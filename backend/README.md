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
                                                      │ ChokeDetector     │ → YOLOv8-Pose (heurística)
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
    com o resultado da detecção. Também aceita `{"type": "reset"}`, enviado
    quando o usuário cancela o alarme, para zerar o histórico de frames.
- **`detector.py`** — o "cérebro":
  - `WeaponDetector`: YOLOv8 pré-treinado (COCO) para `knife` e `scissors`.
  - `ChokeDetector`: YOLOv8-Pose (várias pessoas por frame) — mede a
    distância entre os punhos e o pescoço de cada pessoa, normalizada pela
    largura dos ombros. Conta como perigo: punho de **outra** pessoa perto do
    pescoço, ou os **dois** punhos da própria pessoa (uma mão só é ignorada,
    pra não disparar com alguém coçando o pescoço ou no telefone).
  - `DangerPipeline`: junta os dois e só confirma alarme após N frames
    de perigo dentro de uma janela (reduz falso positivo por ruído de um frame
    só). Cada conexão WebSocket tem o seu, com histórico próprio; os modelos
    YOLO são carregados uma vez e compartilhados.

## Pré-requisitos

- Python 3.10+ instalado ([python.org](https://python.org) — marque "Add
  Python to PATH" na instalação)
- Uma webcam (se for testar pela página web) — não é obrigatório se for
  testar direto pelo app Android

## Rodando o servidor (jeito rápido)

Dê dois cliques em **`backend/iniciar.bat`** (ou rode `backend\iniciar.bat`
no terminal). Na primeira vez ele:

1. cria um ambiente Python isolado em `backend/.venv` (não vai para o git);
2. instala as dependências do `requirements.txt` (alguns minutos — baixa o
   PyTorch);
3. se o PC tiver placa **NVIDIA**, troca o PyTorch pela versão com GPU
   (CUDA, ~3 GB de download);
4. baixa os pesos `yolov8n.pt` (objetos) e `yolov8n-pose.pt` (pose), ~6 MB
   cada.

Nas próximas vezes ele só inicia o servidor. A janela mostra os endereços
IPv4 do PC para digitar no app (ex: `192.168.0.15:8000`) e, quando estiver
pronto, a linha:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### GPU x CPU

O servidor usa a GPU NVIDIA automaticamente quando o PyTorch tem suporte a
CUDA (a janela mostra `carregado em NVIDIA ...` ou `carregado em CPU`).
Medido neste projeto, com os dois modelos por frame:

| Hardware | Tempo por frame |
|---|---|
| CPU (Ryzen 7 5700X) | ~100–140 ms |
| GPU (GTX 1650, FP16) | ~35 ms |

Se o `.venv` foi criado antes de instalar o driver NVIDIA, instale a versão
com GPU manualmente:
```bash
.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

## Rodando manualmente (qualquer sistema)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
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
de mexer no app Android. Ela desenha as caixas dos objetos e o esqueleto de
cada pessoa detectada (verde normal, vermelho quando a heurística de
estrangulamento vê perigo no frame).

## Estrutura de arquivos

```
backend/
├── detector.py        # pipeline de detecção (YOLO + pose)
├── server.py           # servidor FastAPI (WebSocket)
├── iniciar.bat         # atalho Windows: cria o .venv na 1ª vez e sobe o servidor
├── static/index.html   # cliente web de teste (opcional, sem o app)
└── requirements.txt
```

## Limitações e próximos passos

Ver a seção **Limitações conhecidas** no [README geral](../README.md) do
repositório — os pontos sobre modelo genérico e heurística de
estrangulamento se aplicam diretamente a este backend.
