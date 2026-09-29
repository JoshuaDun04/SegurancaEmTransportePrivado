# Resultados dos experimentos

Quadros: 1855 ({'ENFORCAR': 786, 'FACA': 594, 'normal': 475})

## Faca — por quadro (positivos: FACA; negativos: normal)

| Detector | Limiar | Revocação | Alarme falso | AUC |
|---|---|---|---|---|
| YOLOv8n COCO | 0.45 | 0.0% | 0.0% | 0.582 |
| YOLOv8n COCO | 0.25 | 0.0% | 0.0% | 0.582 |
| YOLOv8s COCO | 0.45 | 1.5% | 0.0% | 0.674 |
| YOLOv8s COCO | 0.25 | 5.6% | 0.0% | 0.674 |
| YOLOv8m COCO | 0.45 | 6.4% | 1.1% | 0.692 |
| YOLOv8m COCO | 0.25 | 20.5% | 3.6% | 0.692 |
| YOLOv8n ajustado | 0.45 | 77.9% | 0.6% | 0.913 |
| YOLOv8n ajustado | 0.25 | 80.0% | 0.6% | 0.913 |

## Estrangulamento — por quadro (positivos: ENFORCAR; negativos: normal)

| Método | Limiar | Revocação | Alarme falso | Alarme em cenas de faca | AUC |
|---|---|---|---|---|---|
| Heurística (pose n) | τ=0.4 | 5.9% | 0.4% | 1.0% | 0.654 |
| Heurística (pose n) | τ=0.6 | 33.1% | 7.6% | 6.9% | 0.654 |
| Heurística (pose n) | τ=0.8 | 46.9% | 16.0% | 19.4% | 0.654 |
| Heurística (pose s) | τ=0.4 | 19.2% | 0.2% | 1.2% | 0.806 |
| Heurística (pose s) | τ=0.6 | 54.6% | 1.3% | 18.5% | 0.806 |
| Heurística (pose s) | τ=0.8 | 65.9% | 10.1% | 30.3% | 0.806 |
| YOLOv8n ajustado | 0.45 | 94.0% | 1.7% | 4.2% | 0.993 |
| YOLOv8n ajustado | 0.25 | 97.7% | 2.3% | 4.5% | 0.993 |

## Por vídeo, com confirmação temporal

| Situação | Método | Vídeos detectados | Quadros até o alarme (mediana; faixa) | Vídeos normais com alarme | Alarmes falsos |
|---|---|---|---|---|---|
| Faca | YOLOv8n COCO (0,45) | 0/6 | — | 0/5 | 0 |
| Faca | YOLOv8m COCO (0,25) | 5/6 | 12 (3–27) ≈ 1.0 s (0.2–2.2 s) | 2/5 | 2 |
| Estrangulamento | Heurística pose n (τ=0,6) | 7/8 | 24 (14–42) ≈ 2.0 s (1.1–3.4 s) | 2/5 | 2 |
| Estrangulamento | Heurística pose s (τ=0,6) | 8/8 | 14 (7–67) ≈ 1.1 s (0.6–5.4 s) | 0/5 | 0 |
| Faca | YOLOv8n ajustado (0,45) | 5/6 | 3 (3–9) ≈ 0.2 s (0.2–0.7 s) | 0/5 | 0 |
| Estrangulamento | YOLOv8n ajustado (0,45) | 8/8 | 8 (6–21) ≈ 0.6 s (0.5–1.7 s) | 0/5 | 0 |

## Sistema completo por vídeo (alarme = faca OU estrangulamento)

| Configuração | Vídeos perigosos detectados | Quadros até o alarme | Vídeos normais com alarme | Alarmes falsos |
|---|---|---|---|---|
| Atual: YOLOv8n (0,45) + heurística pose n | 9/14 | 30 (14–83) ≈ 2.4 s (1.1–6.7 s) | 2/5 | 2 |
| Sem treino, melhorado: YOLOv8m (0,25) + heurística pose s | 14/14 | 12 (3–67) ≈ 1.0 s (0.2–5.4 s) | 2/5 | 2 |
| Ajustado: YOLOv8n treinado (FACA e ENFORCAR, 0,45) | 14/14 | 6 (3–38) ≈ 0.5 s (0.2–3.1 s) | 0/5 | 0 |
| Híbrido: YOLOv8n treinado (FACA) + heurística pose s | 14/14 | 10 (3–67) ≈ 0.8 s (0.2–5.4 s) | 0/5 | 0 |

## Modelo ajustado por parte da validação cruzada (limiar 0,45, por quadro)

| Parte | Quadros | Revocação FACA | Revocação ENFORCAR | Alarme falso | AUC FACA | AUC ENFORCAR | mAP@0,5 (última época) |
|---|---|---|---|---|---|---|---|
| A | 685 | 47.2% | 87.5% | 2.1% | 0.761 | 0.994 | 0.732 |
| B | 683 | 97.5% | 98.0% | 1.6% | 0.986 | 0.996 | 0.966 |
| C | 487 | 89.3% | 97.9% | 4.1% | 0.998 | 0.985 | 0.979 |