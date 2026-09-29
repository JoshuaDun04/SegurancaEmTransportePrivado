# App: Câmera (React Native / Android)

App Android que fica no suporte do painel do carro: liga a câmera traseira,
captura frames periodicamente e envia para o servidor local via WebSocket.
Não roda nenhum modelo de IA no celular; isso fica todo no
[`backend/`](../backend/README.md).

## Pré-requisitos

- **Node.js 22.11 ou mais novo**: [nodejs.org](https://nodejs.org)
- **Android Studio** instalado, com o **Android SDK** e um dispositivo
  virtual (emulador) ou celular físico configurado
- **CMake 3.31.x** no Android SDK (Android Studio → Settings → Languages &
  Frameworks → Android SDK → aba **SDK Tools** → marque **Show Package
  Details** → CMake **3.31.6**). O CMake 3.22.1 que vem por padrão quebra o
  build no Windows (veja o troubleshooting no final).
- Windows: **virtualização habilitada na BIOS** (Intel VT-x/AMD SVM) para o
  emulador funcionar. Veja o troubleshooting no final se der o erro
  "Windows Hypervisor Platform is not enabled"

## Instalação

A pasta `app/` já é o projeto React Native completo (código + `android/`),
então basta instalar as dependências:

```bash
cd app
npm ci
```

Depois crie o arquivo `app/android/local.properties` (ele não vai para o git,
porque o caminho muda de máquina para máquina) apontando para o CMake 3.31:

```properties
cmake.dir=C\:/Users/<seu-usuario>/AppData/Local/Android/Sdk/cmake/3.31.6
```

### Configurações nativas já aplicadas no projeto

Não precisa fazer nada aqui. A lista é para referência (e para o relatório):

1. `android/build.gradle`: `minSdkVersion = 26` (exigido pelo VisionCamera v5).
2. `AndroidManifest.xml`: permissões de `CAMERA` e `INTERNET`.
3. `AndroidManifest.xml`: `android:usesCleartextTraffic="true"`. O plugin do
   React Native define esse valor como `false` no build release, e o Android
   bloqueia a conexão `ws://` sem mostrar erro: o app fica parado em
   "connecting". No build debug o problema não aparece.
4. `MainActivity.kt`: `FLAG_KEEP_SCREEN_ON`, para a tela não apagar com o
   celular no suporte do carro.

As três dependências do VisionCamera (`react-native-vision-camera`,
`react-native-nitro-modules`, `react-native-nitro-image`) precisam estar na
mesma versão major (v5); o `package-lock.json` já garante isso.

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

## Gerando o APK para instalar no celular

O APK release já leva o JavaScript embutido, então **não precisa do Metro
nem do PC ligado ao celular** para abrir o app. Ele é assinado com a
`debug.keystore` do projeto, o que basta para instalar direto no aparelho
(não serve para publicar na Play Store).

```bash
cd android
./gradlew assembleRelease
```

O APK fica em `android/app/build/outputs/apk/release/app-release.apk`.

Para instalar, escolha uma das opções:

- **Via USB** (com depuração USB ativada): `adb install -r app-release.apk`
- **Sem cabo**: copie o arquivo para o celular (Drive, WhatsApp, cabo como
  armazenamento) e abra pelo gerenciador de arquivos. O Android vai pedir
  para permitir "instalar apps de fontes desconhecidas".

## Troubleshooting (problemas reais encontrados no desenvolvimento)

| Erro | Causa | Solução |
|---|---|---|
| `npx react-native init` não cria nada, sem erro | Comando `init` foi movido de pacote | Use `npx @react-native-community/cli@latest init` |
| `JAVA_HOME is not set` | Variável de ambiente ausente | Configure `JAVA_HOME` apontando para `...\Android Studio\jbr` (Windows: variáveis de ambiente do sistema) |
| `'adb' não é reconhecido` | Platform-tools fora do PATH | Configure `ANDROID_HOME` e adicione `%ANDROID_HOME%\platform-tools` ao PATH |
| `Windows Hypervisor Platform is not enabled` | Virtualização desligada na BIOS, ou o recurso do Windows não está ativado | Habilite SVM Mode/VT-x na BIOS **e** "Windows Hypervisor Platform" em "Ativar recursos do Windows" |
| `Project with path ':react-native-nitro-image' could not be found` | VisionCamera v5 precisa de `react-native-nitro-modules` **e** `react-native-nitro-image` juntos | `npm install react-native-vision-camera react-native-nitro-modules react-native-nitro-image` |
| Erros de `Unresolved reference 'currentActivity'` / `Return type mismatch` no VisionCamera | Versão do VisionCamera incompatível com a versão do React Native (ex: v4 com RN muito recente) | Use a versão do VisionCamera compatível com sua versão de RN, geralmente a mais recente (v5) é a mais bem mantida |
| `ninja: error: manifest 'build.ninja' still dirty after 100 tries` (em `react-native-nitro-image`) | O ninja 1.10 do CMake 3.22.1 do SDK não lida com caminhos > ~250 caracteres no Windows | Instale o CMake 3.31.x e configure o `local.properties` (ver [Instalação](#instalação)). Apague as pastas `node_modules/*/android/.cxx` antes de buildar de novo |
| App fecha sozinho quando o alarme dispara (`SecurityException: vibrate`) | Falta a permissão `VIBRATE` no manifest | Já corrigido em `AndroidManifest.xml` |
| App fica em "connecting"/"disconnected" e a página `http://<ip>:8000` não abre no navegador do celular | Celular e PC em redes diferentes (ex: PC no cabo do modem da operadora, celular no Wi-Fi de um segundo roteador) ou rede de visitantes | Coloque os dois na mesma rede, ou use o cabo USB: `adb reverse tcp:8000 tcp:8000` e endereço `localhost:8000` |
| App fica em "connecting" só no APK release | `usesCleartextTraffic` é `false` no release e o Android bloqueia `ws://` | Veja o passo 3 das configurações nativas |
| `camera.takePhoto is not a function` / prop `photo` inexistente | API do VisionCamera v4; na v5 a captura é feita por um `usePhotoOutput()` passado em `outputs` | Use `photoOutput.capturePhotoToFile(...)` (já implementado em `CameraScreen.tsx`) |
| App não deveria ser testado em celular corporativo/gerenciado por MDM | Riscos de política de TI (bloqueio de depuração USB, instalação fora do catálogo, wipe remoto) | Use um celular pessoal ou o emulador do Android Studio |

## Próximos passos de profissionalização

- **Foreground Service**: hoje o app precisa ficar em primeiro plano com a
  tela ligada. Migrar a captura para um Foreground Service nativo tornaria o
  monitoramento mais robusto (sobrevive a bloqueios de tela).
- **Conexão segura**: `wss://` com certificado autoassinado + token simples
  de autenticação entre app e servidor.
- **Reconexão mais inteligente** em caso de queda momentânea do Wi-Fi (já
  existe uma reconexão básica em `useDetectionSocket.ts`, mas pode evoluir).
