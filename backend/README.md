# Backend — Servidor de Detecção (Python)

Servidor local que recebe os frames de vídeo do app (via WebSocket), roda os
modelos de IA e decide se deve disparar o alarme.

## Arquitetura

```
[App React Native] --frames JPEG (base64) via WebSocket--> [server.py]
                                                                  │
                                                                  ▼
                                                          [detector.py]
                                                      ┌──────────────────┐
                                                      │ WeaponDetector    │ → YOLOv8 (knife, scissors)
                                                      │ ChokeDetector     │ → MediaPipe Pose (heurística)
                                                      └──────────────────┘
                                                                  │
                                                                  ▼
                                                    resultado (alerta + motivos)
```

- **`server.py`** — servidor FastAPI, expõe:
  - `GET /` → serve uma página web de teste (`static/index.html`) que também
    funciona como cliente de demonstração (acessa a webcam do PC direto pelo
    navegador, sem precisar do app Android — útil pra testar o modelo
    isoladamente).
  - `WS /ws` → recebe frames em JSON (`{"frame": "<base64 jpeg>"}`) e responde
    com o resultado da detecção.
- **`detector.py`** — o "cérebro":
  - `WeaponDetector`: YOLOv8 pré-treinado (COCO) para `knife` e `scissors`.
  - `ChokeDetector`: MediaPipe Pose — mede a distância entre os punhos e a
    região do pescoço ao longo de vários frames.
  - `DangerPipeline`: junta os dois e só confirma alarme após N frames
    consecutivos de perigo (reduz falso positivo por ruído de um frame só).

## Pré-requisitos

- Python 3.10+ instalado ([python.org](https://python.org) — marque "Add
  Python to PATH" na instalação)
- Uma webcam (se for testar pela página web) — não é obrigatório se for
  testar direto pelo app Android

## Instalação

```bash
cd backend
pip install -r requirements.txt
```

> **Nota sobre o MediaPipe**: dependendo da sua versão do Python, o pip pode
> instalar uma versão mais recente do `mediapipe` que não tem mais a API de
> pose estimation "clássica" (`mediapipe.solutions`). Nesse caso, o
> `ChokeDetector` detecta isso automaticamente na inicialização e desativa
> apenas essa parte (com um aviso no console), sem travar o servidor — a
> detecção de faca continua funcionando normalmente. Se quiser a detecção de
> pose ativa, procure uma versão do Python compatível com uma release mais
> antiga do MediaPipe (ex: 0.10.14) que ainda inclui essa API.

## Rodando o servidor

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

Você deve ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Deixe essa janela aberta enquanto o app estiver em uso.

### Descobrindo o IP para conectar o app

- **Emulador Android** (rodando no mesmo PC): use `10.0.2.2:8000` — é o
  endereço especial que o emulador usa para "voltar" ao computador host.
- **Celular físico** (na mesma rede Wi-Fi do PC): rode `ipconfig` (Windows)
  ou `ifconfig`/`ip addr` (Mac/Linux) e procure o "Endereço IPv4" da sua
  placa de rede Wi-Fi (algo como `192.168.0.15`). Use
  `<esse-ip>:8000` no app.

Se o Firewall do Windows perguntar se quer permitir a conexão, clique em
**Permitir acesso**.

## Testando sem o app (opcional)

Abra `http://localhost:8000` no navegador do próprio PC — uma página de
teste abre a webcam e já roda a detecção, útil para validar o modelo antes
de mexer no app Android.

## Estrutura de arquivos

```
backend/
├── detector.py        # pipeline de detecção (YOLO + pose)
├── server.py           # servidor FastAPI (WebSocket)
├── static/index.html   # cliente web de teste (opcional, sem o app)
└── requirements.txt
```

## Limitações e próximos passos

Ver a seção **Limitações conhecidas** no [README geral](../README.md) do
repositório — os pontos sobre modelo genérico e pose de uma pessoa só se
aplicam diretamente a este backend.
