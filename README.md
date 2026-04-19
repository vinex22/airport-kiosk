# ✈️ airport-kiosk

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--5.4-412991?logo=openai&logoColor=white)](https://azure.microsoft.com/products/ai-services/openai-service)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Deploy: Azure App Service](https://img.shields.io/badge/Deployed%20on-Azure%20App%20Service-0078D4?logo=microsoftazure)](https://airport-kiosk.azurewebsites.net)

Created by [vinayjain@microsoft.com](mailto:vinayjain@microsoft.com) / [vinex22@gmail.com](mailto:vinex22@gmail.com)

**"Can I Carry This On Board?"** — an AI-powered airport self-service kiosk that uses **Azure OpenAI GPT-5.4** to determine whether an item is allowed in cabin baggage, based on ICAO international aviation security rules. Built with **FastAPI**, authenticated with `DefaultAzureCredential` (no API keys 🔑).

> **Keywords:** airport kiosk AI, carry-on item checker, cabin baggage rules, aviation security kiosk, Azure OpenAI GPT-5.4 multimodal, ICAO prohibited items, FastAPI camera app, self-service airport screening

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Prerequisites](#-prerequisites)
- [Project Structure](#-project-structure)
- [Configuration](#️-configuration)
- [Features](#️-features)
- [API Endpoints](#-api-endpoints)
- [Local Development](#-local-development)
- [Deployment](#️-deployment)
- [How It Works](#-how-it-works)
- [Troubleshooting](#️-troubleshooting)
- [License](#-license)

---

## 🔎 Overview

Point your item at the camera, tap **Scan**, and get an instant verdict:

- **✅ Allowed** — item is safe to carry on board
- **🚫 Prohibited** — item is banned from cabin baggage, with the specific rule cited

The kiosk covers all ICAO prohibited categories: weapons, sharp objects, tools, blunt instruments, liquids >100ml, lithium batteries, and dangerous goods.

**Live instance:** https://airport-kiosk.azurewebsites.net

## ✅ Prerequisites

1. Python 3.11+
2. Azure AI Services (multi-service) account with GPT-5.4 deployment
3. Azure Blob Storage account (for image archival)
4. `Cognitive Services User` role assigned for your identity (or managed identity)
5. `az login` completed (for local dev)

## 📁 Project Structure

```
airport-kiosk/
├── .env.example          # environment variable template
├── .gitignore
├── LICENSE
├── README.md
├── DEPLOYMENT.md         # full Azure App Service deployment guide
├── architecture.drawio   # draw.io architecture diagram
├── main.py               # FastAPI application
├── requirements.txt      # Python dependencies
└── static/
    └── kiosk.html        # Kiosk UI (camera + scan)
```

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in:

```
AZURE_AI_SERVICES_ENDPOINT=https://<your-ai-services>.services.ai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-5.4
AZURE_STORAGE_ACCOUNT_URL=https://<your-storage>.blob.core.windows.net
DEBUG=true
```

## ✈️ Features

- **Camera capture** — uses device camera (rear-facing on mobile) to photograph the item
- **GPT-5.4 multimodal analysis** — sends image to Azure OpenAI for item identification
- **ICAO rule matching** — checks against 6 prohibited categories + liquid/gel/aerosol rules + lithium battery rules
- **Streaming response** — SSE token-by-token streaming for fast time-to-first-token
- **Partial JSON rendering** — shows item name and verdict before the full response arrives
- **Image archival** — all scanned images stored in Azure Blob Storage by date

## 🔌 API Endpoints

| Method | Path     | Description                                     |
|--------|----------|-------------------------------------------------|
| GET    | `/`      | Kiosk UI page                                   |
| POST   | `/check` | Item check via GPT-5.4 (streaming SSE response) |

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

> Open [`architecture.drawio`](architecture.drawio) in [draw.io](https://app.diagrams.net/) or VS Code (with the Draw.io Integration extension) for the full architecture diagram.

```
┌─────────────┐     POST /check       ┌─────────────────┐   chat (stream)     ┌──────────────┐
│   Browser    │ ──── photo ─────────> │  FastAPI Server  │ ─── base64 img ──> │ Azure OpenAI │
│  (kiosk)     │ <─── SSE tokens ──── │   (main.py)      │ <── token stream ─ │  GPT-5.4     │
└─────────────┘                        └─────────────────┘                     └──────────────┘
```

All scanned images are also uploaded to **Azure Blob Storage** for audit/archival, organized by date.

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
