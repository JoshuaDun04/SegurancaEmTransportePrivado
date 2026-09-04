import { useCallback, useEffect, useRef, useState } from 'react';

export type DetectionResult = {
  alert: boolean;
  reasons: string[];
  inference_ms: number;
  frame_id: number;
};

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

/**
 * Gerencia a conexão WebSocket com o servidor local (o computador no carro
 * rodando server.py). Reconecta automaticamente se a conexão cair (ex: perda
 * momentânea de Wi-Fi).
 */
export function useDetectionSocket(serverAddress: string) {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastResult, setLastResult] = useState<DetectionResult | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);

  const connect = useCallback(() => {
    if (!serverAddress) return;
    setStatus('connecting');

    const ws = new WebSocket(`ws://${serverAddress}/ws`);
    wsRef.current = ws;

    ws.onopen = () => setStatus('connected');

    ws.onmessage = (event) => {
      try {
        const data: DetectionResult = JSON.parse(event.data);
        setLastResult(data);
      } catch (e) {
        console.warn('Falha ao interpretar resposta do servidor', e);
      }
    };

    ws.onerror = () => setStatus('error');

    ws.onclose = () => {
      setStatus('disconnected');
      if (shouldReconnect.current) {
        reconnectTimer.current = setTimeout(connect, 2000);
      }
    };
  }, [serverAddress]);

  useEffect(() => {
    shouldReconnect.current = true;
    connect();
    return () => {
      shouldReconnect.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendFrame = useCallback((base64Jpeg: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({ frame: base64Jpeg }));
    return true;
  }, []);

  return { status, lastResult, sendFrame };
}
