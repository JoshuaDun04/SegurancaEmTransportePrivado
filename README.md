# PEX8 — Sistema de Segurança para Transporte Privado

> Projeto acadêmico: sistema de detecção de situações de perigo (objeto
> cortante e possível estrangulamento) para uso dentro de veículos de
> transporte por aplicativo (Uber, 99, etc.), com processamento de IA local
> — sem depender de servidores em nuvem.

## A ideia

Um celular fica preso no suporte da multimídia do carro, com a câmera
voltada para o interior do veículo. Ele transmite os frames continuamente
para um computador local (dentro do próprio carro, ex: um mini-PC/Raspberry
Pi, ou o notebook do motorista), que roda os modelos de IA e decide se algo
perigoso está acontecendo. Se detectar, dispara um alarme sonoro/visual e
simula o acionamento de autoridades (polícia/ambulância).

```
┌─────────────────────┐        Wi-Fi local        ┌──────────────────────────┐
│   App (celular)      │ ── frames JPEG (WebSocket) ──▶ │  Servidor local (PC)      │
│  React Native        │                             │  Python + YOLOv8 +        │
│  só câmera + rede     │ ◀── alerta / status ──────  │  MediaPipe Pose           │
└─────────────────────┘                             └──────────────────────────┘
```

Por que processamento local e não em nuvem? Custo (não pagar por servidores
online rodando 24/7) e latência (decisão precisa ser rápida, sem depender de
conexão de internet estável dentro do carro).

## Estrutura do repositório

```
PEX8/
├── app/        → aplicativo React Native (Android) — captura e envia a câmera
└── backend/    → servidor Python — roda os modelos de IA e dispara o alarme
```

Cada pasta tem seu próprio README detalhado com passo a passo de instalação:

- 📱 [`app/README.md`](./app/README.md) — como rodar o app no Android Studio
- 🖥️ [`backend/README.md`](./backend/README.md) — como rodar o servidor de detecção

## Detecções implementadas

| Situação | Técnica | Status |
|---|---|---|
| Objeto cortante (faca/tesoura) | YOLOv8 (pré-treinado, classes COCO) | ✅ Funcional |
| Possível estrangulamento | MediaPipe Pose (heurística de distância mão↔pescoço) | ⚠️ Protótipo / simplificado |

## Limitações conhecidas (importante para o relatório acadêmico)

1. **Modelo genérico, não especializado**: o YOLO usado é pré-treinado no
   dataset COCO — reconhece a classe "knife" nativamente, mas nunca viu
   exemplos específicos de faca empunhada como ameaça dentro de um carro. Uma
   versão de produção precisaria de fine-tuning com um dataset próprio.
2. **Pose de uma pessoa só**: a heurística de estrangulamento foi desenhada
   para demonstrar o conceito, não é robusta para dois corpos no mesmo frame
   (motorista + passageiro). O passo seguinte é um pose estimator
   multi-pessoa (ex: YOLO-Pose) + um classificador temporal treinado com
   vídeos reais de ação.
3. **"Chamar autoridades" é simulado**: por segurança durante o
   desenvolvimento/testes, o app só simula a chamada (tela + contador), sem
   discar de verdade.
4. Limiares de confiança e de frames consecutivos foram escolhidos
   empiricamente — precisam de validação com dados reais antes de qualquer
   uso além de demonstração acadêmica.

## Roadmap / próximos passos

- [ ] Fine-tuning do YOLO com dataset próprio (fotos dentro de carro)
- [ ] Pose estimation multi-pessoa para o estrangulamento
- [ ] Foreground Service no Android (rodar de forma mais robusta)
- [ ] Conexão `wss://` com autenticação simples entre app e servidor
- [ ] Testes de campo com dados reais

## Autor

Projeto desenvolvido como parte de uma disciplina de extensão universitária
(PEX8).

## Licença

Uso educacional/acadêmico. Adapte conforme a licença exigida pela sua
instituição, se aplicável.
