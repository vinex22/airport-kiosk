# 🛡️ airport-kiosk

Created by [vinayjain@microsoft.com](mailto:vinayjain@microsoft.com) / [vinex22@gmail.com](mailto:vinex22@gmail.com)

AI-powered airport security screening using Azure AI Vision and GPT-5.4, authenticated with `DefaultAzureCredential` (no API keys 🔑).

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

MIT
