import { useCallback, useEffect, useRef, useState } from 'react';

export type DetectionResult = {
  alert: boolean;
  reasons: string[];
  inference_ms: number;
  frame_id: number;
};

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

// Se a resposta de um frame não chegar nesse tempo (ex: mensagem perdida), libera o envio do próximo.
const RESPONSE_TIMEOUT_MS = 3000;

// Aceita o endereço como o usuário digitar: "http://192.168.0.15:8000/ " -> "192.168.0.15:8000".
function normalizeAddress(address: string) {
  return address.trim().replace(/^(https?|wss?):\/\//i, '').replace(/\/+$/, '');
}

/**
 * Gerencia a conexão WebSocket com o servidor local (o computador no carro
 * rodando server.py). Reconecta automaticamente se a conexão cair (ex: perda
 * momentânea de Wi-Fi).
 */
export function useDetectionSocket(serverAddress: string) {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastResult, setLastResult] = useState<DetectionResult | null>(null);
  // Tempo de ida e volta do último frame (captura enviada -> resultado recebido).
  const [roundTripMs, setRoundTripMs] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  // Momento em que o frame ainda sem resposta foi enviado (null = nenhum em trânsito).
  const inFlightSinceRef = useRef<number | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);

  const connect = useCallback(() => {
    if (!serverAddress) return;
    setStatus('connecting');

    const ws = new WebSocket(`ws://${normalizeAddress(serverAddress)}/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      inFlightSinceRef.current = null;
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data: DetectionResult = JSON.parse(event.data);
        if (inFlightSinceRef.current !== null) {
          setRoundTripMs(Date.now() - inFlightSinceRef.current);
          inFlightSinceRef.current = null;
        }
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

  // Só um frame em trânsito por vez: se o app mandasse frames mais rápido do que o
  // servidor processa, eles se acumulariam numa fila e o alarme chegaria cada vez
  // mais atrasado. Assim o atraso fica limitado a um único frame.
  const canSendFrame = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    const since = inFlightSinceRef.current;
    return since === null || Date.now() - since > RESPONSE_TIMEOUT_MS;
  }, []);

  const sendFrame = useCallback((base64Jpeg: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    inFlightSinceRef.current = Date.now();
    ws.send(JSON.stringify({ frame: base64Jpeg }));
    return true;
  }, []);

  // Pede ao servidor para zerar o histórico de frames (usado ao cancelar o alarme).
  const sendReset = useCallback(() => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'reset' }));
    }
  }, []);

  return { status, lastResult, roundTripMs, canSendFrame, sendFrame, sendReset };
}
