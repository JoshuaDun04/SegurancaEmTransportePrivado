import React, { useState } from 'react';
import { SafeAreaView, StatusBar, StyleSheet } from 'react-native';
import SettingsScreen from './src/screens/SettingsScreen';
import CameraScreen from './src/screens/CameraScreen';

export default function App() {
  const [serverAddress, setServerAddress] = useState('');
  const [screen, setScreen] = useState<'settings' | 'camera'>('settings');

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0b0d10" />
      {screen === 'settings' ? (
        <SettingsScreen
          initialAddress={serverAddress}
          onConnect={(address) => {
            setServerAddress(address);
            setScreen('camera');
          }}
        />
      ) : (
        <CameraScreen
          serverAddress={serverAddress}
          onBack={() => setScreen('settings')}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0b0d10' },
});
