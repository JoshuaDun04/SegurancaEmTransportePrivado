# YOLOv8n x YOLOv8s ajustados (validação cruzada por sequência)

## Por quadro (limiar 0,45; IC 95% por bootstrap de sequências)

| Modelo | Classe | Revocação | Alarme falso | AUC |
|---|---|---|---|---|
| YOLOv8n | FACA | 77,9% [45,2%; 98,3%] | 0,0% [0,0%; 0,0%] | 0,915 |
| YOLOv8n | ENFORCAR | 94,0% [86,9%; 98,8%] | 0,2% [0,0%; 0,7%] | 0,998 |

## Por sequência (janelas do sistema: faca 3 de 8, estrangulamento 6 de 12)

| Modelo | Classe | Sequências detectadas | Normais com alarme | Tempo mediano |
|---|---|---|---|---|
| YOLOv8n | FACA | 5/6 | 0/5 | 0,2 s |
| YOLOv8n | ENFORCAR | 8/8 | 0/5 | 0,6 s |

## Por rodada da validação cruzada (revocação por quadro, limiar 0,45)

| Modelo | Parte | Faca | Estrangulamento | Alarme falso |
|---|---|---|---|---|
| YOLOv8n | A | 47,2% | 87,5% | 0,5% |
| YOLOv8n | B | 97,5% | 98,0% | 0,0% |
| YOLOv8n | C | 89,3% | 97,9% | 0,0% |