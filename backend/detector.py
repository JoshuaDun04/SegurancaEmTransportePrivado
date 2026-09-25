"""
Módulo de detecção de situações de perigo para o app de segurança em transporte privado.

Duas frentes de detecção:
1. WeaponDetector  -> objeto (faca/tesoura) via YOLOv8 (classes COCO: knife, scissors)
2. ChokeDetector   -> heurística de pose via YOLOv8-Pose (multi-pessoa): mede a
                       proximidade dos punhos em relação ao pescoço de cada pessoa
                       ao longo de múltiplos frames.

IMPORTANTE (limitações honestas, documentar no relatório da faculdade):
- O modelo YOLO usado aqui é o pré-treinado em COCO (uso genérico). Ele já reconhece
  "knife" nativamente, mas não foi fine-tunado para o contexto específico de uma faca
  sendo empunhada como ameaça dentro de um carro -> em um projeto real, o ideal é
  treinar/fine-tunar com um dataset próprio (imagens dentro de veículos, ângulos de
  câmera de suporte de painel, iluminação noturna etc.) para reduzir falsos positivos.
- A detecção de estrangulamento é uma heurística geométrica (punho perto do
  pescoço), não um modelo treinado para reconhecer a ação. Ela não diferencia um
  aperto de um abraço ou de um toque no ombro, e depende de o agressor aparecer no
  frame: mãos de alguém fora do enquadramento não têm keypoints. A evolução
  natural é um classificador temporal (sequência de keypoints -> ação) treinado
  com vídeos reais.
- "Detecção de perigo" por poucos frames isolados gera muito falso positivo. Por isso
  os dois detectores usam um buffer temporal (N frames consecutivos) antes de
  confirmar o alarme.
"""

import threading
import time
from collections import deque

import numpy as np
import torch
from ultralytics import YOLO


# ----------------------------- Modelo compartilhado -----------------------------

class SharedModel:
    """Modelo YOLO carregado uma única vez e compartilhado entre conexões.

    Carregar o YOLO é caro, então todas as conexões usam a mesma instância. Como a
    inferência roda em threads (ver server.py), o lock evita duas predições
    simultâneas no mesmo modelo.
    """

    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model = YOLO(model_path)
        self.names = self.model.names
        self._lock = threading.Lock()
        # Usa a GPU NVIDIA se o PyTorch tiver suporte a CUDA (bem mais rápido); senão, CPU.
        # Na GPU, meia precisão (FP16) é mais rápida e praticamente não muda o resultado.
        self.device = 0 if torch.cuda.is_available() else "cpu"
        self.precision = "fp32" if self.device == "cpu" else "fp16"
        # A primeira inferência é lenta (inicialização do PyTorch/CUDA). Fazendo ela aqui,
        # na subida do servidor, o primeiro frame do app já é processado na velocidade normal.
        self.predict(np.zeros((480, 640, 3), dtype=np.uint8), conf=0.5)
        where = "CPU" if self.device == "cpu" else torch.cuda.get_device_name(0)
        print(f"[SharedModel] {model_path} carregado em {where}")

    def predict(self, frame: np.ndarray, conf: float):
        with self._lock:
            return self.model.predict(frame, verbose=False, conf=conf,
                                      device=self.device, quantize=self.precision)[0]


# ----------------------------- Detector de objetos (faca/tesoura) -----------------------------

class WeaponDetector:
    DANGER_CLASSES = {"knife", "scissors"}

    def __init__(self, model: SharedModel, conf_threshold: float = 0.45,
                 confirm_frames: int = 3, buffer_size: int = 8):
        self.model = model
        self.conf_threshold = conf_threshold
        self.confirm_frames = confirm_frames
        self.history = deque(maxlen=buffer_size)

    def reset(self):
        self.history.clear()

    def process(self, frame: np.ndarray):
        results = self.model.predict(frame, self.conf_threshold)

        detections = []
        danger_this_frame = False
        for box in results.boxes:
            cls_id = int(box.cls[0])
            name = self.model.names[cls_id]
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]

            detections.append({
                "class": name,
                "confidence": round(conf, 3),
                "bbox": [x1, y1, x2, y2],
            })

            if name in self.DANGER_CLASSES:
                danger_this_frame = True

        self.history.append(danger_this_frame)
        confirmed = sum(self.history) >= self.confirm_frames

        return {
            "confirmed": confirmed,
            "danger_this_frame": danger_this_frame,
            "detections": detections,
        }


# ----------------------------- Heurística de estrangulamento (pose) -----------------------------

class ChokeDetector:
    """Heurística de estrangulamento sobre o YOLO-Pose (multi-pessoa).

    Para cada pessoa detectada (possível vítima), estima o ponto do pescoço e mede a
    distância até os punhos de todas as pessoas no frame. A distância é normalizada
    pela largura dos ombros da vítima, então o limiar vale igual para quem está perto
    ou longe da câmera. Conta como perigo no frame:
      - punho de OUTRA pessoa perto do pescoço da vítima; ou
      - os DOIS punhos da própria pessoa perto do pescoço dela. Uma mão só no próprio
        pescoço é comum (coçar, ajeitar a gola, falar ao telefone) e é ignorada, mas
        com as duas mãos a chance de ser um aperto é maior. Esse caso também cobre o
        YOLO-Pose atribuir as mãos do agressor ao corpo da vítima quando os dois se
        sobrepõem na imagem.
    """

    # Índices de keypoints no formato COCO (17 pontos) usado pelo YOLO-Pose
    NOSE = 0
    LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
    LEFT_WRIST, RIGHT_WRIST = 9, 10

    def __init__(self, model: SharedModel, conf_threshold: float = 0.4,
                 keypoint_conf: float = 0.5, proximity_ratio: float = 0.6,
                 confirm_frames: int = 6, buffer_size: int = 12):
        self.model = model
        self.conf_threshold = conf_threshold
        self.keypoint_conf = keypoint_conf
        # distância punho<->pescoço máxima, em múltiplos da largura dos ombros
        self.proximity_ratio = proximity_ratio
        self.confirm_frames = confirm_frames
        self.history = deque(maxlen=buffer_size)

    def reset(self):
        self.history.clear()

    def _neck(self, kps: np.ndarray):
        """Retorna (ponto_do_pescoço, largura_dos_ombros) ou None se os ombros não aparecem."""
        ls, rs = kps[self.LEFT_SHOULDER], kps[self.RIGHT_SHOULDER]
        if ls[2] < self.keypoint_conf or rs[2] < self.keypoint_conf:
            return None
        shoulder_width = float(np.hypot(*(ls[:2] - rs[:2])))
        if shoulder_width < 10:  # pessoa pequena demais / de perfil -> não confiável
            return None
        neck = (ls[:2] + rs[:2]) / 2
        # O pescoço fica acima da linha dos ombros: sobe um pouco em direção ao nariz.
        nose = kps[self.NOSE]
        if nose[2] >= self.keypoint_conf:
            neck = neck + 0.3 * (nose[:2] - neck)
        return neck, shoulder_width

    def _wrists_near(self, kps: np.ndarray, neck: np.ndarray, shoulder_width: float) -> int:
        near = 0
        for idx in (self.LEFT_WRIST, self.RIGHT_WRIST):
            wrist = kps[idx]
            if wrist[2] < self.keypoint_conf:
                continue
            if np.hypot(*(wrist[:2] - neck)) / shoulder_width < self.proximity_ratio:
                near += 1
        return near

    def process(self, frame: np.ndarray):
        results = self.model.predict(frame, self.conf_threshold)

        people = []
        if results.keypoints is not None and len(results.keypoints) > 0:
            all_kps = results.keypoints.data.cpu().numpy()  # (pessoas, 17, [x, y, conf])
            boxes = results.boxes.xyxy.cpu().numpy()
            people = [{"kps": kps, "bbox": box} for kps, box in zip(all_kps, boxes)]

        danger_this_frame = False
        for v, victim in enumerate(people):
            neck_info = self._neck(victim["kps"])
            if neck_info is None:
                continue
            neck, shoulder_width = neck_info
            for a, other in enumerate(people):
                near = self._wrists_near(other["kps"], neck, shoulder_width)
                if (a != v and near >= 1) or (a == v and near == 2):
                    danger_this_frame = True
                    break
            if danger_this_frame:
                break

        self.history.append(danger_this_frame)
        confirmed = sum(self.history) >= self.confirm_frames

        return {
            "confirmed": confirmed,
            "danger_this_frame": danger_this_frame,
            "people": [
                {
                    "bbox": [round(float(v), 1) for v in p["bbox"]],
                    "keypoints": [[round(float(x), 1), round(float(y), 1), round(float(c), 3)]
                                  for x, y, c in p["kps"]],
                }
                for p in people
            ],
        }


# ----------------------------- Orquestrador -----------------------------

class DangerPipeline:
    """Junta os dois detectores e decide o alarme final.

    Uma instância por conexão: o histórico de frames de um cliente não pode
    influenciar o alarme de outro. O modelo YOLO (pesado) vem compartilhado.
    """

    def __init__(self, weapon_model: SharedModel, pose_model: SharedModel):
        self.weapon_detector = WeaponDetector(weapon_model)
        self.choke_detector = ChokeDetector(pose_model)

    def reset(self):
        """Zera o histórico temporal (ex: usuário cancelou o alarme no app)."""
        self.weapon_detector.reset()
        self.choke_detector.reset()

    def process_frame(self, frame: np.ndarray):
        t0 = time.time()
        weapon_result = self.weapon_detector.process(frame)
        choke_result = self.choke_detector.process(frame)
        elapsed_ms = round((time.time() - t0) * 1000, 1)

        alert = weapon_result["confirmed"] or choke_result["confirmed"]
        reasons = []
        if weapon_result["confirmed"]:
            reasons.append("objeto_cortante")
        if choke_result["confirmed"]:
            reasons.append("possivel_estrangulamento")

        return {
            "alert": alert,
            "reasons": reasons,
            "weapon": weapon_result,
            "choke": choke_result,
            "inference_ms": elapsed_ms,
        }
