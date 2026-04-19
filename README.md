# 🛡️ airport-kiosk

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Azure AI Vision](https://img.shields.io/badge/Azure%20AI%20Vision-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/products/ai-services/ai-vision)
[![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--5.4-412991?logo=openai&logoColor=white)](https://azure.microsoft.com/products/ai-services/openai-service)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Deploy: Azure App Service](https://img.shields.io/badge/Deployed%20on-Azure%20App%20Service-0078D4?logo=microsoftazure)](https://airport-kiosk.azurewebsites.net)

Created by [vinayjain@microsoft.com](mailto:vinayjain@microsoft.com) / [vinex22@gmail.com](mailto:vinex22@gmail.com)

**AI-powered airport security screening** that uses **Azure AI Vision** and **Azure OpenAI GPT-5.4** to detect objects in real time and assess whether items are permitted in cabin baggage — based on ICAO international aviation security rules. Built with **FastAPI**, authenticated with `DefaultAzureCredential` (no API keys 🔑).

> **Keywords:** airport security AI, baggage screening AI, object detection Azure, carry-on item checker, aviation security kiosk, Azure AI Vision, GPT-5.4 multimodal, FastAPI computer vision, real-time threat detection, ICAO prohibited items

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Prerequisites](#-prerequisites)
- [Project Structure](#-project-structure)
- [Configuration](#️-configuration)
- [Features](#-features)
- [API Endpoints](#-api-endpoints)
- [Local Development](#-local-development)
- [Deployment](#️-deployment)
- [How It Works](#-how-it-works)
- [Troubleshooting](#️-troubleshooting)
- [License](#-license)

---

## 🔎 Overview

| | Security Camera (`/`) | Passenger Kiosk (`/kiosk`) |
|---|---|---|
| Purpose | Real-time object detection on camera feed | "Can I carry this?" self-service item check |
| AI model | Azure AI Vision + GPT-5.4-nano | GPT-5.4 (multimodal) |
| Output | Bounding boxes + threat flags | Allowed / Prohibited verdict with ICAO rules |
| Response | JSON per frame | Streaming SSE (token-by-token) |
| Best for | Security operators, monitoring | Passengers, self-service kiosks |

**Live instance:** https://airport-kiosk.azurewebsites.net

## ✅ Prerequisites

1. Python 3.11+
2. Azure AI Services (multi-service) account with GPT-5.4 deployment
3. Azure Blob Storage account
4. `Cognitive Services User` role assigned for your identity (or managed identity)
5. `az login` completed (for local dev)

## 📁 Project Structure

```
airport-kiosk/
├── .env.example          # environment variable template
├── .gitignore
├── README.md
├── DEPLOYMENT.md         # full Azure App Service deployment guide
├── main.py               # FastAPI application with all endpoints
├── requirements.txt      # Python dependencies
└── static/
    ├── index.html        # Security camera view with object detection
    └── kiosk.html        # Passenger self-service kiosk
```

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in:

```
AZURE_AI_SERVICES_ENDPOINT=https://<your-ai-services>.services.ai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-5.4
AZURE_STORAGE_ACCOUNT_URL=https://<your-storage>.blob.core.windows.net
DEBUG=true
```

## 🌐 Features

### 🔍 Security Camera View (`/`)
- Live webcam feed with continuous object detection
- Two detection modes:
  - **Computer Vision** — Azure AI Vision object detection with bounding boxes
  - **LLM (GPT-5.4-nano)** — Multimodal LLM-based threat detection with threat classification
- Real-time bounding box overlay on video feed

### ✈️ Passenger Kiosk (`/kiosk`)
- "Can I Carry This?" self-service kiosk for passengers
- Point your item at the camera, tap **Scan**, and get an instant verdict
- Classifies items as **Allowed** or **Prohibited** based on international aviation security rules (ICAO guidelines, HK CAD packing tips)
- Covers all prohibited categories: weapons, sharp objects, tools, blunt instruments, liquids >100ml, lithium batteries, dangerous goods
- Streaming response for fast time-to-first-token

## 🔌 API Endpoints

| Method | Path           | Description                                      |
|--------|----------------|--------------------------------------------------|
| GET    | `/`            | Security camera view                             |
| POST   | `/detect`      | Object detection via Azure AI Vision             |
| POST   | `/detect-llm`  | Object detection via GPT-5.4-nano (threat-aware) |
| GET    | `/kiosk`       | Passenger kiosk page                             |
| POST   | `/kiosk/check` | Item check via GPT-5.4 (streaming SSE response)  |

## 🚀 Local Development

```bash
# Clone the repo
git clone https://github.com/vinex22/airport-kiosk.git
cd airport-kiosk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your Azure resource values

# Run the app
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 in your browser (camera access requires HTTPS in production).

## ☁️ Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full Azure App Service deployment instructions.

```bash
# Quick deploy
Compress-Archive -Path main.py, requirements.txt, static -DestinationPath deploy.zip -Force
az webapp deploy --name airport-kiosk --resource-group airport --src-path deploy.zip --type zip
```

## 🧠 How It Works

```
┌─────────────┐     POST /detect      ┌─────────────────┐     analyze()     ┌──────────────────┐
│   Browser    │ ──── image frame ───> │  FastAPI Server  │ ───────────────> │ Azure AI Vision  │
│  (webcam)    │ <─── bounding boxes ─ │   (main.py)      │ <── objects ──── │ (Image Analysis) │
└─────────────┘                        └─────────────────┘                  └──────────────────┘

┌─────────────┐     POST /detect-llm   ┌─────────────────┐   chat.completions  ┌──────────────┐
│   Browser    │ ──── image frame ───> │  FastAPI Server  │ ─── base64 img ──> │ Azure OpenAI │
│  (webcam)    │ <─── threat flags ─── │   (main.py)      │ <── JSON items ─── │ GPT-5.4-nano │
└─────────────┘                        └─────────────────┘                     └──────────────┘

┌─────────────┐     POST /kiosk/check  ┌─────────────────┐   chat (stream)     ┌──────────────┐
│   Browser    │ ──── photo ─────────> │  FastAPI Server  │ ─── base64 img ──> │ Azure OpenAI │
│  (kiosk)     │ <─── SSE tokens ──── │   (main.py)      │ <── token stream ─ │  GPT-5.4     │
└─────────────┘                        └─────────────────┘                     └──────────────┘
```

All images are also uploaded to **Azure Blob Storage** for audit/archival, organized by endpoint and date.

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| 401/403 from Azure AI | Ensure `Cognitive Services User` role is assigned on the AI Services account |
| Blob upload failures | Verify managed identity has `Storage Blob Data Contributor` on the storage account |
| 503 after deploy | Check startup logs: `az webapp log tail --name airport-kiosk --resource-group airport` |
| Camera not working | Camera access requires HTTPS; `.azurewebsites.net` provides this automatically |
| LLM returns non-JSON | Retry — model occasionally wraps response in markdown fences (handled in code) |
| ModuleNotFoundError on App Service | Set `SCM_DO_BUILD_DURING_DEPLOYMENT=true` in app settings |

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

---

<p align="center">
  <sub>Built with ❤️ using Azure AI Services · <a href="https://airport-kiosk.azurewebsites.net">Live Demo</a></sub>
</p>
