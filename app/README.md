# App — Câmera (React Native / Android)

App Android que fica no suporte do painel do carro: liga a câmera traseira,
captura frames periodicamente e envia para o servidor local via WebSocket.
Não roda nenhum modelo de IA no celular — isso fica todo no
[`backend/`](../backend/README.md).

## Pré-requisitos

- **Node.js LTS** (18 ou 20) — [nodejs.org](https://nodejs.org)
- **Android Studio** instalado, com o **Android SDK** e um dispositivo
  virtual (emulador) ou celular físico configurado
- Windows: **virtualização habilitada na BIOS** (Intel VT-x/AMD SVM) para o
  emulador funcionar — veja o troubleshooting no final se der o erro
  "Windows Hypervisor Platform is not enabled"

## Criando o projeto do zero (caso ainda não tenha)

> Se você já tem a pasta `app/` com os arquivos deste repositório, pule para
> [Instalação](#instalação).

```bash
npx @react-native-community/cli@latest init SegurancaTransporteApp
```

⚠️ **Não use** `npx react-native init` sozinho — em versões recentes, o
comando `init` foi movido para o pacote `@react-native-community/cli` e o
comando antigo falha silenciamente (cria nada, sem erro visível).

## Instalação

```bash
cd app
npm install
npm install react-native-vision-camera react-native-nitro-modules react-native-nitro-image react-native-fs
```

> **Importante**: as três dependências do VisionCamera (`react-native-vision-camera`,
> `react-native-nitro-modules`, `react-native-nitro-image`) precisam ser
> instaladas **juntas**, na mesma versão major (v5). Instalar só uma causa erro
> de build tipo `Project with path ':react-native-nitro-image' could not be
> found`. Se seu projeto usa uma versão do React Native mais antiga (0.7x),
> pode ser necessário usar `react-native-vision-camera@4.x` no lugar — mas
> nesse caso os pacotes Nitro não são necessários.

### Configurações nativas necessárias

**1. `android/build.gradle`** — aumente o `minSdkVersion` para 26:
```gradle
minSdkVersion = 26
```

**2. `android/app/src/main/AndroidManifest.xml`** — adicione antes de `<application>`:
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-feature android:name="android.hardware.camera" android:required="true" />
```

**3. `android/app/src/main/java/.../MainActivity.kt`** — mantenha a tela
sempre ligada (essencial pro uso no suporte do carro):
```kotlin
import android.os.Bundle
import android.view.WindowManager

class MainActivity : ReactActivity() {
  // ... (mantenha o resto igual)

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
  }
}
```

## Rodando

Com um emulador ligado ou celular físico conectado via USB (Depuração USB
ativada):

```bash
npx react-native run-android
```

### Testando no emulador com sua webcam

Como o emulador não tem câmera física, configure-o para usar a webcam do PC:
Android Studio → Device Manager → editar o dispositivo (ícone de lápis) →
seção **Camera** → mude **Back** para `Webcam0`.

### Conectando ao servidor

Na tela inicial do app, digite o endereço do servidor local:

- **Emulador** (servidor rodando no mesmo PC): `10.0.2.2:8000`
- **Celular físico** (mesma rede Wi-Fi do servidor): `<IP-do-PC>:8000`
  (descubra com `ipconfig`/`ifconfig` no computador do servidor)

## Estrutura de arquivos

```
app/
├── App.tsx                       # alterna entre tela de config e câmera
└── src/
    ├── screens/
    │   ├── SettingsScreen.tsx     # tela para digitar IP:porta do servidor
    │   └── CameraScreen.tsx       # câmera + captura periódica de frames
    ├── components/
    │   └── AlarmOverlay.tsx       # tela de alarme (vibração + "ligando p/ polícia")
    └── hooks/
        └── useDetectionSocket.ts  # conexão WebSocket com reconexão automática
```

## Gerando o APK final

```bash
cd android
./gradlew assembleRelease
```

O APK fica em `android/app/build/outputs/apk/release/app-release.apk`.

## Troubleshooting (problemas reais encontrados no desenvolvimento)

| Erro | Causa | Solução |
|---|---|---|
| `npx react-native init` não cria nada, sem erro | Comando `init` foi movido de pacote | Use `npx @react-native-community/cli@latest init` |
| `JAVA_HOME is not set` | Variável de ambiente ausente | Configure `JAVA_HOME` apontando para `...\Android Studio\jbr` (Windows: variáveis de ambiente do sistema) |
| `'adb' não é reconhecido` | Platform-tools fora do PATH | Configure `ANDROID_HOME` e adicione `%ANDROID_HOME%\platform-tools` ao PATH |
| `Windows Hypervisor Platform is not enabled` | Virtualização desligada na BIOS, ou o recurso do Windows não está ativado | Habilite SVM Mode/VT-x na BIOS **e** "Windows Hypervisor Platform" em "Ativar recursos do Windows" |
| `Project with path ':react-native-nitro-image' could not be found` | VisionCamera v5 precisa de `react-native-nitro-modules` **e** `react-native-nitro-image` juntos | `npm install react-native-vision-camera react-native-nitro-modules react-native-nitro-image` |
| Erros de `Unresolved reference 'currentActivity'` / `Return type mismatch` no VisionCamera | Versão do VisionCamera incompatível com a versão do React Native (ex: v4 com RN muito recente) | Use a versão do VisionCamera compatível com sua versão de RN — geralmente a mais recente (v5) é a mais bem mantida |
| App não deveria ser testado em celular corporativo/gerenciado por MDM | Riscos de política de TI (bloqueio de depuração USB, instalação fora do catálogo, wipe remoto) | Use um celular pessoal ou o emulador do Android Studio |

## Próximos passos de profissionalização

- **Foreground Service**: hoje o app precisa ficar em primeiro plano com a
  tela ligada. Migrar a captura para um Foreground Service nativo tornaria o
  monitoramento mais robusto (sobrevive a bloqueios de tela).
- **Conexão segura**: `wss://` com certificado autoassinado + token simples
  de autenticação entre app e servidor.
- **Reconexão mais inteligente** em caso de queda momentânea do Wi-Fi (já
  existe uma reconexão básica em `useDetectionSocket.ts`, mas pode evoluir).
