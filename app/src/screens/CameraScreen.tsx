import React, { useCallback, useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import {
  Camera,
  type CameraRef,
  CommonResolutions,
  useCameraDevice,
  useCameraPermission,
  usePhotoOutput,
} from 'react-native-vision-camera';
import RNFS from 'react-native-fs';
import { useDetectionSocket } from '../hooks/useDetectionSocket';
import AlarmOverlay from '../components/AlarmOverlay';

// Intervalo mínimo entre capturas. O ritmo real é ditado pelo servidor: um frame
// novo só é capturado depois que a resposta do anterior chega (ver useDetectionSocket).
const CAPTURE_INTERVAL_MS = 150;
// Largura do frame enviado. O YOLO trabalha em 640px, então mandar mais que isso
// só aumenta o tempo de codificação e de rede.
const FRAME_WIDTH = 480;
const JPEG_QUALITY = 60;
// Depois de cancelar o alarme, ignora novos alertas por um tempo: frames que já
// estavam a caminho do servidor ainda podem voltar com alert=true.
const ALARM_COOLDOWN_MS = 5000;

type Props = {
  serverAddress: string;
  onBack: () => void;
};

export default function CameraScreen({ serverAddress, onBack }: Props) {
  const device = useCameraDevice('back');
  const { hasPermission, requestPermission } = useCameraPermission();
  // Resolução baixa (480p) e compressão maior: o YOLO redimensiona para 640px de
  // qualquer forma, e fotos menores reduzem muito a latência na rede.
  const photoOutput = usePhotoOutput({
    targetResolution: CommonResolutions.VGA_4_3,
    quality: 0.6,
    qualityPrioritization: device?.supportsSpeedQualityPrioritization ? 'speed' : 'balanced',
  });

  const { status, lastResult, roundTripMs, canSendFrame, sendFrame, sendReset } =
    useDetectionSocket(serverAddress);
  const [alarmActive, setAlarmActive] = useState(false);
  const [alarmReasons, setAlarmReasons] = useState<string[]>([]);
  const cameraRef = useRef<CameraRef>(null);
  const capturingRef = useRef(false);
  // O snapshot do preview é bem mais rápido que tirar foto, mas nem todo aparelho
  // suporta; se falhar uma vez, passa a usar a captura de foto.
  const snapshotSupportedRef = useRef(true);
  const cooldownUntilRef = useRef(0);

  useEffect(() => {
    if (!hasPermission) requestPermission();
  }, [hasPermission, requestPermission]);

  // Captura um frame e devolve o caminho de um JPEG temporário.
  const captureFrame = useCallback(async (): Promise<string> => {
    if (snapshotSupportedRef.current && cameraRef.current) {
      try {
        const snapshot = await cameraRef.current.takeSnapshot();
        const height = Math.round((snapshot.height * FRAME_WIDTH) / snapshot.width);
        const small = await snapshot.resizeAsync(FRAME_WIDTH, height);
        return await small.saveToTemporaryFileAsync('jpg', JPEG_QUALITY);
      } catch (e) {
        console.warn('Snapshot indisponível, usando captura de foto', e);
        snapshotSupportedRef.current = false;
      }
    }
    const { filePath } = await photoOutput.capturePhotoToFile(
      { flashMode: 'off', enableShutterSound: false },
      {},
    );
    return filePath;
  }, [photoOutput]);

  // Loop de captura: pega um frame, converte pra base64 e manda pro servidor.
  useEffect(() => {
    const interval = setInterval(async () => {
      if (capturingRef.current || status !== 'connected' || !canSendFrame()) return;
      capturingRef.current = true;
      try {
        const filePath = await captureFrame();
        const base64 = await RNFS.readFile(filePath, 'base64');
        sendFrame(base64);
        // remove o arquivo temporário pra não acumular lixo no dispositivo
        RNFS.unlink(filePath).catch(() => {});
      } catch (e) {
        console.warn('Erro ao capturar/enviar frame', e);
      } finally {
        capturingRef.current = false;
      }
    }, CAPTURE_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [status, canSendFrame, sendFrame, captureFrame]);

  // Reage ao resultado do servidor
  useEffect(() => {
    if (lastResult?.alert && !alarmActive && Date.now() > cooldownUntilRef.current) {
      setAlarmActive(true);
      setAlarmReasons(lastResult.reasons);
    }
  }, [lastResult, alarmActive]);

  if (!device) {
    return (
      <View style={styles.center}>
        <Text style={styles.info}>Nenhuma câmera traseira encontrada.</Text>
      </View>
    );
  }

  if (!hasPermission) {
    return (
      <View style={styles.center}>
        <Text style={styles.info}>Aguardando permissão de câmera...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Camera
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={true}
        outputs={[photoOutput]}
      />

      <View style={styles.statusBar}>
        <View style={[styles.badge, alarmActive && styles.badgeDanger]}>
          <Text style={styles.badgeText}>
            {alarmActive
              ? '⚠ PERIGO'
              : status === 'connected'
                ? `● Monitorando${roundTripMs !== null ? ` · ${roundTripMs} ms` : ''}`
                : `● ${status}`}
          </Text>
        </View>
        <TouchableOpacity onPress={onBack} style={styles.backBtn}>
          <Text style={styles.backBtnText}>Config</Text>
        </TouchableOpacity>
      </View>

      {alarmActive && (
        <AlarmOverlay
          reasons={alarmReasons}
          onCancel={() => {
            cooldownUntilRef.current = Date.now() + ALARM_COOLDOWN_MS;
            sendReset();
            setAlarmActive(false);
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, backgroundColor: '#0b0d10', alignItems: 'center', justifyContent: 'center' },
  info: { color: '#8b929c' },
  statusBar: {
    position: 'absolute',
    top: 16,
    left: 16,
    right: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  badge: {
    backgroundColor: 'rgba(0,0,0,0.55)',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  badgeDanger: { backgroundColor: 'rgba(255,0,0,0.6)' },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  backBtn: {
    backgroundColor: 'rgba(0,0,0,0.55)',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  backBtnText: { color: '#fff', fontSize: 12 },
});
