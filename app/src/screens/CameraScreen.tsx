import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
} from 'react-native-vision-camera';
import RNFS from 'react-native-fs';
import { useDetectionSocket } from '../hooks/useDetectionSocket';
import AlarmOverlay from '../components/AlarmOverlay';

const CAPTURE_INTERVAL_MS = 300; // ~3 frames/segundo — suficiente pra detecção, leve pra rede

type Props = {
  serverAddress: string;
  onBack: () => void;
};

export default function CameraScreen({ serverAddress, onBack }: Props) {
  const camera = useRef<Camera>(null);
  const device = useCameraDevice('back');
  const { hasPermission, requestPermission } = useCameraPermission();

  const { status, lastResult, sendFrame } = useDetectionSocket(serverAddress);
  const [alarmActive, setAlarmActive] = useState(false);
  const [alarmReasons, setAlarmReasons] = useState<string[]>([]);
  const sendingRef = useRef(false);

  useEffect(() => {
    if (!hasPermission) requestPermission();
  }, [hasPermission, requestPermission]);

  // Loop de captura: tira uma foto, converte pra base64 e manda pro servidor.
  useEffect(() => {
    const interval = setInterval(async () => {
      if (sendingRef.current || !camera.current || status !== 'connected') return;
      sendingRef.current = true;
      try {
        const photo = await camera.current.takePhoto({ flash: 'off' });
        const base64 = await RNFS.readFile(photo.path, 'base64');
        sendFrame(base64);
        // remove o arquivo temporário pra não acumular lixo no dispositivo
        RNFS.unlink(photo.path).catch(() => {});
      } catch (e) {
        console.warn('Erro ao capturar/enviar frame', e);
      } finally {
        sendingRef.current = false;
      }
    }, CAPTURE_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [status, sendFrame]);

  // Reage ao resultado do servidor
  useEffect(() => {
    if (lastResult?.alert && !alarmActive) {
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
        ref={camera}
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={true}
        photo={true}
      />

      <View style={styles.statusBar}>
        <View style={[styles.badge, alarmActive && styles.badgeDanger]}>
          <Text style={styles.badgeText}>
            {alarmActive ? '⚠ PERIGO' : status === 'connected' ? '● Monitorando' : `● ${status}`}
          </Text>
        </View>
        <TouchableOpacity onPress={onBack} style={styles.backBtn}>
          <Text style={styles.backBtnText}>Config</Text>
        </TouchableOpacity>
      </View>

      {alarmActive && (
        <AlarmOverlay
          reasons={alarmReasons}
          onCancel={() => setAlarmActive(false)}
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
