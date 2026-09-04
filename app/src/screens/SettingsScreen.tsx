import React, { useState } from 'react';
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

type Props = {
  initialAddress: string;
  onConnect: (address: string) => void;
};

export default function SettingsScreen({ initialAddress, onConnect }: Props) {
  const [address, setAddress] = useState(initialAddress);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Segurança em Transporte Privado</Text>
      <Text style={styles.subtitle}>
        Digite o IP e a porta do servidor local (o computador rodando o
        script de detecção, na mesma rede Wi-Fi do veículo).
      </Text>

      <TextInput
        style={styles.input}
        placeholder="192.168.0.15:8000"
        placeholderTextColor="#8b929c"
        value={address}
        onChangeText={setAddress}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="numbers-and-punctuation"
      />

      <TouchableOpacity
        style={[styles.button, !address && styles.buttonDisabled]}
        disabled={!address}
        onPress={() => onConnect(address)}
      >
        <Text style={styles.buttonText}>Conectar e iniciar monitoramento</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0b0d10', padding: 24, justifyContent: 'center' },
  title: { color: '#e8eaed', fontSize: 20, fontWeight: '700', marginBottom: 8, textAlign: 'center' },
  subtitle: { color: '#8b929c', fontSize: 13, textAlign: 'center', marginBottom: 24 },
  input: {
    backgroundColor: '#14171c',
    borderWidth: 1,
    borderColor: '#23272e',
    borderRadius: 10,
    color: '#e8eaed',
    padding: 14,
    fontSize: 16,
    marginBottom: 16,
  },
  button: { backgroundColor: '#3aa0ff', borderRadius: 10, padding: 14, alignItems: 'center' },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#0b0d10', fontWeight: '700' },
});
