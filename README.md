# PEX8: Sistema de Segurança para Transporte Privado

> Projeto acadêmico: sistema de detecção de situações de perigo (objeto
> cortante e possível estrangulamento) para uso dentro de veículos de
> transporte por aplicativo (Uber, 99, etc.), com processamento de IA local,
> sem depender de servidores em nuvem.

## A ideia

Um celular fica preso no suporte da multimídia do carro, com a câmera
voltada para o interior do veículo. Ele transmite os frames continuamente
para um servidor, que roda os modelos de IA e decide se algo perigoso está
acontecendo. Se detectar, dispara um alarme sonoro/visual e simula o
acionamento de autoridades (polícia/ambulância).

- **Hoje (protótipo):** o servidor roda em um computador na mesma rede local
  do celular (Wi-Fi ou cabo USB).
- **Plano futuro:** servidor remoto (nuvem ou central), com o celular
  conectado pela internet móvel (4G/5G), atendendo vários veículos.

```
┌─────────────────────┐        Wi-Fi local        ┌──────────────────────────┐
│   App (celular)      │ ── frames JPEG (WebSocket) ──▶ │  Servidor local (PC)      │
│  React Native        │                             │  Python + YOLOv8 +        │
│  só câmera + rede     │ ◀── alerta / status ──────  │  YOLOv8-Pose              │
└─────────────────────┘                             └──────────────────────────┘
```

Por que processar no servidor e não no celular? O celular pode ser simples
(não roda IA, gasta menos bateria e esquenta menos), o servidor usa GPU e os
modelos são atualizados em um lugar só. Para o servidor remoto, o artigo
estima o consumo de dados (~0,26–0,86 GB/h) e a capacidade de uma GPU
(~10 veículos a 5 quadros/s). Ver `experimentos/estimar_dados.py`.

## Estrutura do repositório

```
PEX8/
├── app/        → aplicativo React Native (Android): captura e envia a câmera
└── backend/    → servidor Python: roda os modelos de IA e dispara o alarme
```

## Instalação completa em um PC novo (Windows)

Passo a passo para sair de um PC "zerado" até o app rodando no celular. A
parte demorada (downloads e primeiro build) só acontece uma vez.

### 1. Instalar os programas

| Programa | Onde baixar | Observação |
|---|---|---|
| **Git** | [git-scm.com](https://git-scm.com/download/win) | Opções padrão |
| **Python 3.10 ou mais novo** | [python.org](https://www.python.org/downloads/) | ⚠️ Marque **"Add python.exe to PATH"** na primeira tela do instalador |
| **Node.js 22.11 ou mais novo** (LTS) | [nodejs.org](https://nodejs.org) | Opções padrão |
| **Android Studio** | [developer.android.com/studio](https://developer.android.com/studio) | Na primeira abertura, siga o assistente (modo *Standard*): ele baixa o Android SDK |
| **Driver NVIDIA** (opcional) | [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx) | Só se o PC tiver placa NVIDIA; deixa a detecção ~2,6x mais rápida |

### 2. Configurar o Android SDK

No Android Studio: **More Actions → SDK Manager** (ou *Settings → Languages
& Frameworks → Android SDK*), aba **SDK Tools**, marque **Show Package
Details** e instale:

- **NDK (Side by side) 27.1.12297006**
- **CMake 3.31.6**: ⚠️ não use o 3.22.1 que vem marcado por padrão: ele
  quebra o build no Windows (erro `build.ninja still dirty`)
- **Android SDK Platform-Tools** (normalmente já vem instalado)

Clique em **Apply** e espere os downloads terminarem.

### 3. Variáveis de ambiente e caminhos longos

Abra o **PowerShell como administrador** (botão direito no menu Iniciar →
*Terminal (Admin)*) e rode os três comandos:

```powershell
setx JAVA_HOME "C:\Program Files\Android\Android Studio\jbr" /M
setx ANDROID_HOME "$env:LOCALAPPDATA\Android\Sdk" /M
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

Depois adicione o `adb` ao PATH: *Configurações do Windows → Sistema → Sobre
→ Configurações avançadas do sistema → Variáveis de Ambiente*, edite a
variável **Path** do sistema e adicione:
```
%LOCALAPPDATA%\Android\Sdk\platform-tools
```

**Reinicie o PC** para as variáveis e os caminhos longos valerem.

> O terceiro comando libera caminhos com mais de 260 caracteres no Windows.
> As bibliotecas nativas do app geram caminhos bem longos durante o build, e
> sem isso a compilação falha.

### 4. Baixar o projeto

Use uma pasta de caminho **curto** (também ajuda no build nativo):

```powershell
git clone git@github.com:Melinyel04/Seguran-aEmTransportePrivado.git C:\Projetos\PEX8
cd C:\Projetos\PEX8
```

> Sem chave SSH configurada no GitHub, use o endereço HTTPS:
> `https://github.com/Melinyel04/Seguran-aEmTransportePrivado.git`.

### 5. Backend (servidor de detecção)

Dê dois cliques em **`backend\iniciar.bat`**. Na primeira vez ele:
1. cria o ambiente Python em `backend\.venv`;
2. instala as dependências (FastAPI, Ultralytics, PyTorch...);
3. se houver placa NVIDIA, troca o PyTorch pela versão com GPU (~3 GB);
4. baixa os modelos `yolov8n.pt` e `yolov8n-pose.pt` (~6 MB cada).

Isso leva de 5 a 20 minutos, dependendo da internet. Quando aparecer
`Uvicorn running on http://0.0.0.0:8000`, o servidor está pronto. A janela
também mostra se os modelos carregaram na **GPU** ou na **CPU**.

**Teste rápido:** abra `http://localhost:8000` no navegador do PC e inicie a
webcam. Devem aparecer os esqueletos das pessoas na imagem.

Se o Firewall do Windows perguntar, clique em **Permitir acesso**.

### 6. App (gerar o APK)

Em um terminal (PowerShell) **novo**:

```powershell
cd C:\Projetos\PEX8\app
npm ci
```

Crie o arquivo `app\android\local.properties` (ele não vai para o git) com
o caminho do CMake 3.31 (troque `<seu-usuario>` pelo seu usuário do
Windows):

```properties
cmake.dir=C\:/Users/<seu-usuario>/AppData/Local/Android/Sdk/cmake/3.31.6
```

Gere o APK:

```powershell
cd C:\Projetos\PEX8\app\android
.\gradlew.bat assembleRelease -PreactNativeArchitectures=arm64-v8a
```

O primeiro build leva de 5 a 15 minutos. No final aparece `BUILD
SUCCESSFUL` e o APK fica em:
```
C:\Projetos\PEX8\app\android\app\build\outputs\apk\release\app-release.apk
```

> `arm64-v8a` cobre praticamente todos os celulares dos últimos 8 anos. Para
> gerar um APK que roda também em aparelhos 32 bits, rode sem o
> `-PreactNativeArchitectures=...` (o build fica mais lento e o APK maior).

### 7. Instalar o APK no celular

**Opção A: pelo cabo USB (recomendado)**
1. No celular, ative as *Opções do desenvolvedor*: Configurações → Sobre o
   telefone → toque 7 vezes em **Número da versão**.
2. Em Opções do desenvolvedor, ative a **Depuração USB**.
3. Conecte o cabo e aceite o aviso "Permitir depuração USB" no celular.
4. No PC:
   ```powershell
   adb install -r C:\Projetos\PEX8\app\android\app\build\outputs\apk\release\app-release.apk
   ```

**Opção B: sem cabo.** envie o `app-release.apk` para o celular (Drive,
WhatsApp...), abra o arquivo e permita "instalar apps de fontes
desconhecidas".

### 8. Conectar o app ao servidor e testar

Com o `iniciar.bat` rodando, escolha **uma** forma de conexão:

- **Cabo USB (funciona em qualquer rede):**
  ```powershell
  adb reverse tcp:8000 tcp:8000
  ```
  No app, digite **`localhost:8000`**. Se desconectar o cabo, rode o
  comando de novo.
- **Wi-Fi:** o celular e o PC precisam estar **na mesma rede** (mesmo
  roteador, fora de rede de visitantes). No app, digite o endereço que o
  `iniciar.bat` mostrou (ex: `192.168.0.15:8000`). Para conferir, abra esse
  endereço no navegador do celular; a página de teste tem que abrir.

Toque em **Conectar e iniciar monitoramento** e permita o acesso à câmera. O
selo no topo deve mostrar `● Monitorando · XX ms` (tempo de resposta de
cada frame).

**O que testar:**

| Teste | Como | Esperado |
|---|---|---|
| Estrangulamento | Duas pessoas no quadro; uma põe a mão no pescoço da outra por ~2 s | Alarme "possível estrangulamento" |
| Falso positivo | Uma pessoa sozinha coça o pescoço com uma mão | **Não** dispara |
| Objeto cortante | Faca ou tesoura bem visível e iluminada por 1–2 s | Alarme "objeto cortante" (o modelo genérico ainda erra bastante, ver Limitações) |
| Cancelar | "Estou seguro(a), cancelar" | Alarme some e não volta por 5 s |

Problemas comuns e soluções estão nas tabelas de troubleshooting de
[`app/README.md`](./app/README.md#troubleshooting-problemas-reais-encontrados-no-desenvolvimento)
e [`backend/README.md`](./backend/README.md).

## Uso no dia a dia (depois de instalado)

1. Dois cliques em `backend\iniciar.bat`.
2. Celular no cabo → `adb reverse tcp:8000 tcp:8000` → no app, `localhost:8000`.
   (Ou pelo Wi-Fi, com o endereço mostrado pelo `iniciar.bat`.)
3. Só é preciso gerar o APK de novo quando o código do app mudar.

Cada pasta tem seu próprio README detalhado com passo a passo de instalação:

- 📱 [`app/README.md`](./app/README.md): detalhes do app, configurações nativas e troubleshooting
- 🖥️ [`backend/README.md`](./backend/README.md): como rodar o servidor de detecção

## Detecções implementadas

| Situação | Técnica | Status |
|---|---|---|
| Objeto cortante (faca/tesoura) | YOLOv8 (pré-treinado, classes COCO) | ✅ Funcional |
| Possível estrangulamento | YOLOv8-Pose multi-pessoa (heurística de distância punho↔pescoço) | ⚠️ Protótipo / heurística |

## Limitações conhecidas (importante para o relatório acadêmico)

1. **Modelo genérico, não especializado**: o YOLO usado é pré-treinado no
   dataset COCO. Reconhece a classe "knife" nativamente, mas nunca viu
   exemplos específicos de faca empunhada como ameaça dentro de um carro. Uma
   versão de produção precisaria de fine-tuning com um dataset próprio. Nos
   primeiros testes com o app, o estrangulamento foi detectado, mas a faca
   não: o `yolov8n` (menor modelo da família) tem dificuldade com objetos
   finos e pequenos no quadro. Próximos passos: `yolov8s`, frames maiores,
   limiar próprio para faca e, principalmente, fine-tuning com imagens
   gravadas dentro do carro.
2. **Estrangulamento é heurística, não modelo treinado**: o YOLOv8-Pose
   detecta várias pessoas (motorista + passageiro), e o alarme considera um
   punho de outra pessoa (ou os dois punhos da própria pessoa) perto do
   pescoço. A regra não diferencia um aperto de um abraço e só funciona se as
   mãos do agressor aparecerem no frame. O passo seguinte é um classificador
   temporal (sequência de keypoints → ação) treinado com vídeos reais.
3. **"Chamar autoridades" é simulado**: por segurança durante o
   desenvolvimento/testes, o app só simula a chamada (tela + contador), sem
   discar de verdade.
4. Limiares de confiança e de frames consecutivos foram escolhidos
   empiricamente e precisam de validação com dados reais antes de qualquer
   uso além de demonstração acadêmica.

## Roadmap / próximos passos

- [ ] Fine-tuning do YOLO com dataset próprio (fotos dentro de carro)
- [x] Pose estimation multi-pessoa para o estrangulamento (YOLOv8-Pose)
- [ ] Classificador temporal de ação sobre os keypoints
- [ ] Foreground Service no Android (rodar de forma mais robusta)
- [ ] Conexão `wss://` com autenticação simples entre app e servidor
- [ ] Testes de campo com dados reais

## Autor

Projeto desenvolvido como parte de uma disciplina de extensão universitária
(PEX8).

## Licença

Uso educacional/acadêmico. Adapte conforme a licença exigida pela sua
instituição, se aplicável.
