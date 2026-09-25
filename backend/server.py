"""
Servidor local (edge) do protótipo de segurança em transporte privado.

Recebe frames de vídeo via WebSocket (enviados pelo "app" no celular, aqui simulado
por uma página web que acessa a webcam), roda o pipeline de detecção de perigo
(detector.py) e devolve o resultado em tempo real para o cliente desenhar os
alertas na tela.

Rodar com (ou dois cliques em iniciar.bat):
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

import base64
import json
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from detector import DangerPipeline, SharedModel

# Caminhos relativos a este arquivo, para o servidor funcionar de qualquer pasta.
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Protótipo - Segurança em Transporte Privado")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Modelos carregados uma vez só; cada conexão cria seu próprio DangerPipeline em cima deles.
# Na primeira execução o Ultralytics baixa os pesos (.pt) automaticamente.
weapon_model = SharedModel(str(BASE_DIR / "yolov8n.pt"))
pose_model = SharedModel(str(BASE_DIR / "yolov8n-pose.pt"))


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


def decode_frame(b64_jpeg: str) -> np.ndarray:
    header_sep = b64_jpeg.find(",")
    if header_sep != -1:
        b64_jpeg = b64_jpeg[header_sep + 1:]
    raw = base64.b64decode(b64_jpeg)
    arr = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    pipeline = DangerPipeline(weapon_model, pose_model)
    frame_count = 0
    last_alert_log = 0.0

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)

            # Mensagem de controle: o usuário cancelou o alarme no app, então o
            # histórico temporal é zerado para o alarme não disparar de novo na hora.
            if data.get("type") == "reset":
                pipeline.reset()
                print("[INFO] Alarme cancelado pelo cliente; histórico zerado.")
                continue

            frame = decode_frame(data["frame"])
            if frame is None:
                continue

            # A inferência é pesada e síncrona; rodar numa thread evita travar o
            # event loop (e com ele as outras conexões) enquanto o modelo processa.
            result = await run_in_threadpool(pipeline.process_frame, frame)
            frame_count += 1
            result["frame_id"] = frame_count
            result["timestamp"] = time.time()

            if result["alert"] and time.time() - last_alert_log > 2:
                print(f"[ALERTA] frame={frame_count} motivos={result['reasons']}")
                last_alert_log = time.time()

            await websocket.send_text(json.dumps(result))

    except WebSocketDisconnect:
        print("Cliente desconectado.")
