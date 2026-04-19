# Airport Vision - AI-Powered Airport Security Screening

A real-time airport security screening application that uses Azure AI Vision and GPT-5.4 to detect objects and assess whether items are permitted in cabin baggage.

## Features

### Security Camera View (`/`)
- Live webcam feed with continuous object detection
- Two detection modes:
  - **Computer Vision** — Azure AI Vision object detection with bounding boxes
  - **LLM (GPT-5.4-nano)** — Multimodal LLM-based threat detection with threat classification
- Real-time bounding box overlay on video feed

### Passenger Kiosk (`/kiosk`)
- "Can I Carry This?" self-service kiosk for passengers
- Point your item at the camera, tap **Scan**, and get an instant verdict
- Classifies items as **Allowed** or **Prohibited** based on international aviation security rules (ICAO guidelines, HK CAD packing tips)
- Covers all prohibited categories: weapons, sharp objects, tools, blunt instruments, liquids >100ml, lithium batteries, dangerous goods
- Streaming response for fast time-to-first-token

## Tech Stack

- **Backend:** Python / FastAPI
- **Frontend:** Vanilla HTML/JS (no build step)
- **AI Services:**
  - Azure AI Vision (Image Analysis 4.0) — object detection
  - Azure OpenAI GPT-5.4 / GPT-5.4-nano — multimodal threat analysis & kiosk assistant
- **Storage:** Azure Blob Storage — captured images archived by endpoint/date
- **Auth:** `DefaultAzureCredential` (managed identity, no API keys)
- **Hosting:** Azure App Service (Linux)

## Project Structure

```
main.py              # FastAPI application with all endpoints
requirements.txt     # Python dependencies
static/
  index.html         # Security camera view with object detection
  kiosk.html         # Passenger self-service kiosk
.env                 # Environment variables (not committed)
```

## API Endpoints

| Method | Path           | Description                                      |
|--------|----------------|--------------------------------------------------|
| GET    | `/`            | Security camera view                             |
| POST   | `/detect`      | Object detection via Azure AI Vision             |
| POST   | `/detect-llm`  | Object detection via GPT-5.4-nano (threat-aware) |
| GET    | `/kiosk`       | Passenger kiosk page                             |
| POST   | `/kiosk/check` | Item check via GPT-5.4 (streaming SSE response)  |

## Getting Started

### Prerequisites

- Python 3.11+
- An Azure subscription with:
  - Azure AI Services (multi-service) account
  - Azure OpenAI GPT-5.4 deployment
  - Azure Blob Storage account
- Azure CLI logged in (`az login`)

### Local Development

```bash
# Clone the repo
git clone <repo-url>
cd airport

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

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full Azure App Service deployment instructions.

**Live instance:** https://airport-kiosk.azurewebsites.net

## Environment Variables

See [.env.example](.env.example) for all required configuration.

## License

MIT
