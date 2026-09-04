"""
Módulo de detecção de situações de perigo para o app de segurança em transporte privado.

Duas frentes de detecção:
1. WeaponDetector  -> objeto (faca/tesoura) via YOLOv8 (classes COCO: knife, scissors)
2. ChokeDetector   -> heurística de pose via MediaPipe: mede a proximidade das mãos
                       em relação à região do pescoço ao longo de múltiplos frames.

IMPORTANTE (limitações honestas, documentar no relatório da faculdade):
- O modelo YOLO usado aqui é o pré-treinado em COCO (uso genérico). Ele já reconhece
  "knife" nativamente, mas não foi fine-tunado para o contexto específico de uma faca
  sendo empunhada como ameaça dentro de um carro -> em um projeto real, o ideal é
  treinar/fine-tunar com um dataset próprio (imagens dentro de veículos, ângulos de
  câmera de suporte de painel, iluminação noturna etc.) para reduzir falsos positivos.
- MediaPipe Pose foi desenhado para UMA pessoa por frame. Para o cenário real
  (motorista + passageiro), a versão de produção precisaria de um pose estimator
  multi-pessoa (ex: YOLO-Pose, OpenPose, ou MediaPipe Holistic com detecção de
  múltiplas boxes de pessoa antes de rodar o pose em cada uma). Aqui a heurística
  aplica o Pose no frame inteiro, o que funciona bem para demonstrar o conceito mas
  é uma simplificação.
- "Detecção de perigo" por poucos frames isolados gera muito falso positivo. Por isso
  os dois detectores usam um buffer temporal (N frames consecutivos) antes de
  confirmar o alarme.
"""

import time
from collections import deque

import cv2
import numpy as np
from ultralytics import YOLO
import mediapipe as mp


# ----------------------------- Detector de objetos (faca/tesoura) -----------------------------

class WeaponDetector:
    DANGER_CLASSES = {"knife", "scissors"}

    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.45,
                 confirm_frames: int = 3, buffer_size: int = 8):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.confirm_frames = confirm_frames
        self.history = deque(maxlen=buffer_size)

    def process(self, frame: np.ndarray):
        results = self.model.predict(frame, verbose=False, conf=self.conf_threshold)[0]

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
    # Índices de landmarks relevantes do MediaPipe Pose
    NOSE = 0
    LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
    LEFT_WRIST, RIGHT_WRIST = 15, 16

    def __init__(self, proximity_threshold: float = 0.18, confirm_frames: int = 6,
                 buffer_size: int = 12):
        self.proximity_threshold = proximity_threshold
        self.confirm_frames = confirm_frames
        self.history = deque(maxlen=buffer_size)
        self.enabled = True
        try:
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=0,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except Exception as exc:
            # Ex: sem acesso à internet para baixar o modelo de pose na primeira execução.
            print(f"[ChokeDetector] AVISO: pose estimation desabilitada ({exc})")
            self.pose = None
            self.enabled = False

    @staticmethod
    def _dist(a, b):
        return float(np.hypot(a.x - b.x, a.y - b.y))

    def process(self, frame: np.ndarray):
        if not self.enabled:
            return {"confirmed": False, "danger_this_frame": False, "landmarks": None}

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.pose.process(rgb)

        danger_this_frame = False
        landmarks_out = None

        if result.pose_landmarks:
            lm = result.pose_landmarks.landmark
            neck_x = (lm[self.LEFT_SHOULDER].x + lm[self.RIGHT_SHOULDER].x) / 2
            neck_y = (lm[self.LEFT_SHOULDER].y + lm[self.RIGHT_SHOULDER].y) / 2

            class _P:  # ponto auxiliar pra reusar _dist
                x, y = neck_x, neck_y
            neck_point = _P()

            dist_left = self._dist(lm[self.LEFT_WRIST], neck_point)
            dist_right = self._dist(lm[self.RIGHT_WRIST], neck_point)

            if min(dist_left, dist_right) < self.proximity_threshold:
                danger_this_frame = True

            landmarks_out = [{"x": p.x, "y": p.y, "z": p.z, "visibility": p.visibility}
                              for p in lm]

        self.history.append(danger_this_frame)
        confirmed = sum(self.history) >= self.confirm_frames

        return {
            "confirmed": confirmed,
            "danger_this_frame": danger_this_frame,
            "landmarks": landmarks_out,
        }


# ----------------------------- Orquestrador -----------------------------

class DangerPipeline:
    """Junta os dois detectores e decide o alarme final."""

    def __init__(self):
        self.weapon_detector = WeaponDetector()
        self.choke_detector = ChokeDetector()

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
            "choke": {
                "confirmed": choke_result["confirmed"],
                "danger_this_frame": choke_result["danger_this_frame"],
            },
            "inference_ms": elapsed_ms,
        }
