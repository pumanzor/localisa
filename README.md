<div align="center">

# Localisa

### AI that lives in the real world, not in a chat window.

Give any LLM **eyes** (cameras), **ears** (microphone), **voice** (TTS), **hands** (IoT), and **memory** (RAG).

Everything runs locally. Your data stays encrypted on your hardware.

[Install](#quick-start) · [Features](#features) · [Plugins](#plugins) · [Docs](docs/) · [Contributing](#contributing)

</div>

---

## What is Localisa?

Localisa is an open-source platform that bridges AI with the physical world. It connects any LLM — local or cloud — to your cameras, microphones, smart home devices, documents, and more.

Unlike Alexa or Google Home, **your data never leaves your machine**. Unlike ChatGPT, **your AI can see, hear, and act**.

```
Your LLM (any)          Localisa              Physical World
                            │
Ollama, DeepSeek,    ────  Brain  ────────  IP Cameras (eyes)
Claude, OpenAI             Memory            Microphone (ears)
Local or Cloud             Context            Speakers (voice)
                            │                 Sensors (touch)
                            │                 IoT/MQTT (hands)
                            │                 Your documents (memory)
```

## Quick Start

```bash
git clone https://github.com/pumanzor/localisa.git
cd localisa
make install
```

The installer will:
1. Detect your hardware (GPU, cameras, IoT devices on your network)
2. Let you choose your LLM backend (Ollama, cloud API, or built-in)
3. Set up everything with Docker
4. Open your browser to `http://localhost:8080`

**Requirements:** Docker, 8GB RAM. GPU optional (Ollama handles CPU/GPU automatically).

## Features

### Core
- **Chat** with any LLM (Ollama, DeepSeek, Groq, Claude, OpenAI, vLLM, or any OpenAI-compatible API)
- **RAG** — Upload PDFs, DOCX, TXT and ask questions about them. Hybrid search (semantic + keyword).
- **Voice** — Talk to your AI. Whisper for transcription, Piper for natural TTS.
- **Vision** — Connect IP cameras. Your AI sees and describes what's happening.
- **Telegram Bot** — Control everything from your phone, receive alerts with photos.
- **Trust Dashboard** — See exactly what's encrypted, what left your network, full audit log.

### Privacy & Security
- All data encrypted at rest (AES-256-GCM)
- Cloud API calls automatically anonymized (names, addresses, IDs stripped)
- Camera frames processed in memory, never saved to disk by default
- Credential vault with master password
- Open source — verify it yourself

## Plugins

| Plugin | Description |
|--------|-------------|
| `home` | Smart home control — Tuya, Sonoff, Shelly, Tasmota, Zigbee2MQTT, Home Assistant |
| `network` | Router intelligence — Pi-hole, AdGuard, OpenWrt, Mikrotik. AI firewall, parental control |
| `energy` | Solar + grid monitoring — Fronius, Huawei, Growatt, Enphase, Shelly EM |
| `audio` | Music — Spotify, YouTube, internet radio. Cast to Chromecast, DLNA, AirPlay |
| `medical` | Medical RAG with real clinical guidelines (MINSAL, IMSS, WHO). Triage assistance |
| `vehicle` | Car diagnostics via OBD-II/CAN bus. Predictive maintenance |
| `elder` | Elderly care — fall detection, routine monitoring, medication reminders, companionship |
| `finance` | Personal finance — bank API integration, expense analysis, bill alerts |
| `calendar` | Google Calendar, CalDAV. Smart reminders |
| `weather` | Weather forecasts and alerts (Open-Meteo, free) |
| `search` | Web search (DuckDuckGo, SearXNG) |
| `notify` | Push notifications (Ntfy, Gotify) |

## LLM Backend Support

| Backend | GPU Required | Cost | Setup |
|---------|-------------|------|-------|
| **Ollama** | No (CPU ok) | Free | `ollama pull qwen2.5:3b` |
| **DeepSeek** | No | $0.14/M tokens | API key |
| **Groq** | No | Free tier | API key |
| **Claude** | No | $3/M tokens | API key |
| **OpenAI** | No | $2.50/M tokens | API key |
| **vLLM** | Yes (6GB+) | Free | Docker profile |

## Architecture

```
Browser :8080 → nginx → API :5002 → LLM (Ollama/Cloud/vLLM)
                                   → RAG :5001 (ChromaDB)
                                   →   Embeddings :8101 (BGE-M3)
                                   → Whisper :5012
                                   → TTS :5050
                                   → Vision
                                   → Redis :6379
                                   → MQTT :1883
                                   → Telegram Bot
```

All services communicate over an internal Docker network. Only port 8080 is exposed.

## Contributing

PRs welcome! See [docs/PLUGINS.md](docs/PLUGINS.md) for how to create plugins.

```bash
# Development mode
cp .env.example .env
# Edit .env
make dev-api    # Run API with hot-reload
make dev-rag    # Run RAG with hot-reload
```

## License

Apache 2.0 — See [LICENSE](LICENSE)

---

<div align="center">

**Localisa** — Your intelligence. Your hardware. Your rules.

[localisa.cl](https://localisa.cl)

</div>
