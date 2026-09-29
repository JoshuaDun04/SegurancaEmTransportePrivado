# Análises complementares

## 1. Intervalos de confiança (95%, bootstrap por sequência, 2.000 reamostragens)

| Método | Revocação | Alarme falso | AUC |
|---|---|---|---|
| Faca – YOLOv8n COCO (0,45) | 0.0% [0.0%; 0.0%] | 0.0% [0.0%; 0.0%] | 0.583 [0.488; 0.686] |
| Faca – YOLOv8s COCO (0,45) | 1.5% [0.2%; 3.5%] | 0.0% [0.0%; 0.0%] | 0.677 [0.600; 0.747] |
| Faca – YOLOv8m COCO (0,45) | 6.4% [3.4%; 9.4%] | 1.1% [0.0%; 3.2%] | 0.697 [0.574; 0.813] |
| Faca – YOLOv8m COCO (0,25) | 20.5% [10.8%; 31.4%] | 3.7% [0.0%; 8.7%] | 0.697 [0.564; 0.815] |
| Faca – YOLOv8n ajustado (0,45) | 77.9% [45.2%; 98.3%] | 0.0% [0.0%; 0.0%] | 0.915 [0.759; 0.998] |
| Estrang. – heurística pose n (τ=0,6) | 33.1% [22.9%; 43.8%] | 7.6% [0.0%; 16.7%] | 0.656 [0.527; 0.779] |
| Estrang. – heurística pose s (τ=0,6) | 54.6% [35.9%; 71.1%] | 0.7% [0.2%; 1.1%] | 0.811 [0.685; 0.909] |
| Estrang. – YOLOv8n ajustado (0,45) | 94.0% [87.5%; 98.6%] | 0.2% [0.0%; 0.7%] | 0.998 [0.995; 0.999] |

## 2. Ablação da janela de confirmação (K de W)

| Detector | Janela | Sequências detectadas | Normais com alarme | Tempo até o alarme (mediana) |
|---|---|---|---|---|
| Faca – ajustado | sem janela (1 de 1) | 5/6 | 0/5 | 0.1 s |
| Faca – ajustado | 3 de 8 | 5/6 | 0/5 | 0.2 s |
| Faca – ajustado | 6 de 12 | 5/6 | 0/5 | 0.5 s |
| Faca – ajustado | 10 de 20 | 5/6 | 0/5 | 0.8 s |
| Estrang. – ajustado | sem janela (1 de 1) | 8/8 | 1/5 | 0.1 s |
| Estrang. – ajustado | 3 de 8 | 8/8 | 0/5 | 0.4 s |
| Estrang. – ajustado | 6 de 12 | 8/8 | 0/5 | 0.6 s |
| Estrang. – ajustado | 10 de 20 | 8/8 | 0/5 | 0.9 s |
| Estrang. – heurística pose s | sem janela (1 de 1) | 8/8 | 3/5 | 0.6 s |
| Estrang. – heurística pose s | 3 de 8 | 8/8 | 0/5 | 0.7 s |
| Estrang. – heurística pose s | 6 de 12 | 8/8 | 0/5 | 1.1 s |
| Estrang. – heurística pose s | 10 de 20 | 8/8 | 0/5 | 1.5 s |
| Estrang. – heurística pose n | sem janela (1 de 1) | 8/8 | 2/5 | 0.6 s |
| Estrang. – heurística pose n | 3 de 8 | 8/8 | 2/5 | 1.2 s |
| Estrang. – heurística pose n | 6 de 12 | 7/8 | 2/5 | 2.0 s |
| Estrang. – heurística pose n | 10 de 20 | 6/8 | 2/5 | 2.5 s |

## 3. Ablação das regras da heurística (τ = 0,6, por quadro)

| Pose | Regras | Revocação (estrangulamento) | Alarme falso (normal) | Disparo em cenas de faca |
|---|---|---|---|---|
| n | só (i): mão de outra pessoa | 31.8% | 0.0% | 4.9% |
| n | só (ii): duas mãos próprias | 1.9% | 7.6% | 2.4% |
| n | (i) + (ii) | 33.1% | 7.6% | 6.9% |
| s | só (i): mão de outra pessoa | 53.8% | 0.2% | 18.2% |
| s | só (ii): duas mãos próprias | 1.9% | 0.4% | 0.7% |
| s | (i) + (ii) | 54.6% | 0.7% | 18.5% |

## 4. Ablação do limiar do modelo ajustado

| Classe | Limiar | Revocação (quadro) | Alarme falso (quadro) | Sequências detectadas | Normais com alarme |
|---|---|---|---|---|---|
| Faca | 0.25 | 80.0% | 0.0% | 6/6 | 0/5 |
| Faca | 0.45 | 77.9% | 0.0% | 5/6 | 0/5 |
| Faca | 0.65 | 74.9% | 0.0% | 5/6 | 0/5 |
| Faca | 0.85 | 50.5% | 0.0% | 5/6 | 0/5 |
| Estrangulamento | 0.25 | 97.7% | 0.2% | 8/8 | 0/5 |
| Estrangulamento | 0.45 | 94.0% | 0.2% | 8/8 | 0/5 |
| Estrangulamento | 0.65 | 87.2% | 0.0% | 8/8 | 0/5 |
| Estrangulamento | 0.85 | 28.2% | 0.0% | 3/8 | 0/5 |