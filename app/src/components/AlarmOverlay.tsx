import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, Vibration, View } from 'react-native';

const REASON_LABELS: Record<string, string> = {
  objeto_cortante: 'Objeto cortante detectado',
  possivel_estrangulamento: 'Padrão de possível estrangulamento',
};

// Padrão de vibração tipo "sirene": vibra 500ms, pausa 250ms, repete.
const SIREN_PATTERN = [0, 500, 250];

type Props = {
  reasons: string[];
  onCancel: () => void;
};

export default function AlarmOverlay({ reasons, onCancel }: Props) {
  const [seconds, setSeconds] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    Vibration.vibrate(SIREN_PATTERN, true); // true = repete até cancelar
    intervalRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => {
      Vibration.cancel();
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');
  const label = seconds < 4 ? 'Ligando para a Polícia...' : 'Chamada simulada conectada (protótipo).';

  return (
    <View style={styles.overlay}>
      <Text style={styles.title}>⚠️ SITUAÇÃO DE PERIGO DETECTADA</Text>
      <Text style={styles.reasons}>
        {reasons.map((r) => REASON_LABELS[r] || r).join(' • ')}
      </Text>

      <View style={styles.callingBox}>
        <Text style={styles.callingText}>{label}</Text>
        <Text style={styles.timer}>{mm}:{ss}</Text>
      </View>

      <TouchableOpacity style={styles.cancelBtn} onPress={onCancel}>
        <Text style={styles.cancelBtnText}>Estou seguro(a) — cancelar</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(160,0,0,0.75)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    zIndex: 10,
  },
  title: { color: '#fff', fontSize: 20, fontWeight: '700', textAlign: 'center', marginBottom: 8 },
  reasons: { color: '#ffd0d0', fontSize: 13, textAlign: 'center', marginBottom: 20 },
  callingBox: {
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 22,
    alignItems: 'center',
  },
  callingText: { color: '#fff', fontSize: 14, marginBottom: 4 },
  timer: { color: '#fff', fontSize: 22, fontWeight: '600' },
  cancelBtn: {
    marginTop: 24,
    backgroundColor: '#fff',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 24,
  },
  cancelBtnText: { color: '#7a0000', fontWeight: '700' },
});
