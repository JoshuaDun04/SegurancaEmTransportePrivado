"""
Servidor local (edge) do protótipo de segurança em transporte privado.

Recebe frames de vídeo via WebSocket (enviados pelo "app" no celular, aqui simulado
por uma página web que acessa a webcam), roda o pipeline de detecção de perigo
(detector.py) e devolve o resultado em tempo real para o cliente desenhar os
alertas na tela.

Rodar com:
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

import base64
import json
import time

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from detector import DangerPipeline

app = FastAPI(title="Protótipo - Segurança em Transporte Privado")
app.mount("/static", StaticFiles(directory="static"), name="static")

pipeline = DangerPipeline()


@app.get("/")
def index():
    return FileResponse("static/index.html")


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
    frame_count = 0
    last_alert_log = 0.0

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)

            frame = decode_frame(data["frame"])
            if frame is None:
                continue

            result = pipeline.process_frame(frame)
            frame_count += 1
            result["frame_id"] = frame_count
            result["timestamp"] = time.time()

            if result["alert"] and time.time() - last_alert_log > 2:
                print(f"[ALERTA] frame={frame_count} motivos={result['reasons']}")
                last_alert_log = time.time()

            await websocket.send_text(json.dumps(result))

    except WebSocketDisconnect:
        print("Cliente desconectado.")
