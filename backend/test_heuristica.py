"""
Testes da heurística de estrangulamento (ChokeDetector) com keypoints sintéticos.

Cada caso monta as pessoas "à mão" (posição de nariz, ombros e punhos) e verifica
se a regra marca perigo no frame. Não precisa de câmera nem de GPU: o modelo
YOLO-Pose é substituído por um falso que devolve os keypoints do caso.

Rodar com:
    .venv\\Scripts\\python.exe test_heuristica.py
"""

import types

import numpy as np

from detector import ChokeDetector

CONF = 0.9  # confiança dos keypoints sintéticos (acima do limiar de 0.5)


def pessoa(pescoco, largura_ombros=100, punho_esq=None, punho_dir=None):
    """Keypoints COCO de uma pessoa sentada; por padrão, mãos no colo (longe do pescoço)."""
    x, y = pescoco
    k = np.zeros((17, 3), dtype=np.float32)
    k[0] = [x, y - 60, CONF]                               # nariz
    k[5] = [x + largura_ombros / 2, y, CONF]               # ombro esquerdo
    k[6] = [x - largura_ombros / 2, y, CONF]               # ombro direito
    k[9] = [*(punho_esq or (x + 60, y + 150)), CONF]       # punho esquerdo
    k[10] = [*(punho_dir or (x - 60, y + 150)), CONF]      # punho direito
    return k


class _Tensor:
    def __init__(self, arr):
        self.arr = arr

    def cpu(self):
        return types.SimpleNamespace(numpy=lambda: self.arr)


class _Keypoints:
    def __init__(self, arr):
        self.data = _Tensor(arr)
        self._n = len(arr)

    def __len__(self):
        return self._n


class ModeloFalso:
    """Imita o SharedModel: devolve sempre os mesmos keypoints."""

    def __init__(self, pessoas):
        self.kps = np.stack(pessoas)

    def predict(self, frame, conf):
        return types.SimpleNamespace(
            keypoints=_Keypoints(self.kps),
            boxes=types.SimpleNamespace(xyxy=_Tensor(np.zeros((len(self.kps), 4)))),
        )


# O pescoço estimado fica 30% do caminho entre o meio dos ombros e o nariz:
# para uma pessoa com pescoço de referência em (x, 300), ele fica em (x, 282).
CASOS = [
    ("Pessoa sozinha, mãos no colo",
     [pessoa((300, 300))], False),
    ("Uma mão no próprio pescoço (coçar, telefone)",
     [pessoa((300, 300), punho_esq=(300, 282))], False),
    ("Duas mãos no próprio pescoço",
     [pessoa((300, 300), punho_esq=(310, 282), punho_dir=(290, 282))], True),
    ("Mão de outra pessoa no pescoço",
     [pessoa((300, 300)), pessoa((600, 300), punho_dir=(305, 285))], True),
    ("Duas pessoas lado a lado, mãos longe",
     [pessoa((300, 300)), pessoa((600, 300))], False),
    ("Pessoas longe da câmera (ombros de 40 px), mão alheia no pescoço",
     [pessoa((300, 300), largura_ombros=40),
      pessoa((400, 300), largura_ombros=40, punho_dir=(300, 290))], True),
]


def main():
    falhas = 0
    for descricao, pessoas, esperado in CASOS:
        detector = ChokeDetector(ModeloFalso(pessoas))
        obtido = detector.process(None)["danger_this_frame"]
        ok = obtido == esperado
        falhas += not ok
        print(f"[{'OK' if ok else 'FALHOU'}] {descricao}: perigo={obtido} (esperado {esperado})")
    print(f"\n{len(CASOS) - falhas}/{len(CASOS)} casos corretos")
    raise SystemExit(1 if falhas else 0)


if __name__ == "__main__":
    main()
