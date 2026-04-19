# Deployment Guide — Azure App Service

This application is deployed to **Azure App Service (Linux)** using zip deploy.

## Current Deployment

| Setting            | Value                                                        |
|--------------------|--------------------------------------------------------------|
| App Service        | `airport-kiosk`                                              |
| URL                | https://airport-kiosk.azurewebsites.net                      |
| Resource Group     | `airport`                                                    |
| Location           | Central India                                                |
| App Service Plan   | `airport-plan` (F1 Free tier)                                |
| OS                 | Linux                                                        |
| Subscription       | ME-MngEnvMCAP497026-vinayjain-1 (`555a1e03-73fb-4f88-9296-59bd703d16f3`) |

## Azure Resources Required

1. **Azure AI Services** (multi-service account) — provides both Azure AI Vision and Azure OpenAI
2. **Azure OpenAI deployment** — GPT-5.4 (for kiosk) and/or GPT-5.4-nano (for detect-llm)
3. **Azure Blob Storage account** — stores captured images
4. **Azure App Service** (Linux, Python 3.11+) — hosts the FastAPI app

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed and logged in
- Contributor access to the target subscription

## Step-by-Step Deployment

### 1. Create the Resource Group (if not exists)

```bash
az group create --name airport --location centralindia
```

### 2. Create the App Service Plan

```bash
az appservice plan create \
  --name airport-plan \
  --resource-group airport \
  --sku F1 \
  --is-linux
```

### 3. Create the Web App

```bash
az webapp create \
  --name airport-kiosk \
  --resource-group airport \
  --plan airport-plan \
  --runtime "PYTHON:3.11"
```

### 4. Configure App Settings

Set the required environment variables on the App Service. **Do not use API keys** — use managed identity instead.

```bash
az webapp config appsettings set \
  --name airport-kiosk \
  --resource-group airport \
  --settings \
    AZURE_AI_SERVICES_ENDPOINT="https://<your-ai-services>.services.ai.azure.com" \
    AZURE_OPENAI_DEPLOYMENT="gpt-5.4" \
    AZURE_STORAGE_ACCOUNT_URL="https://<your-storage>.blob.core.windows.net" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

### 5. Enable Managed Identity

The app uses `DefaultAzureCredential` — no API keys are stored. Assign a system-assigned managed identity and grant it access to your Azure resources.

```bash
# Enable system-assigned managed identity
az webapp identity assign \
  --name airport-kiosk \
  --resource-group airport

# Note the principalId from the output, then assign roles:

# Cognitive Services User — for AI Vision + OpenAI
az role assignment create \
  --assignee <principalId> \
  --role "Cognitive Services User" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<ai-account>

# Storage Blob Data Contributor — for image uploads
az role assignment create \
  --assignee <principalId> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage-account>
```

### 6. Configure Startup Command

```bash
az webapp config set \
  --name airport-kiosk \
  --resource-group airport \
  --startup-file "uvicorn main:app --host 0.0.0.0 --port 8000"
```

### 7. Deploy via Zip Deploy

```bash
# Create the deployment package
zip -r deploy.zip main.py requirements.txt static/

# Deploy
az webapp deploy \
  --name airport-kiosk \
  --resource-group airport \
  --src-path deploy.zip \
  --type zip
```

### 8. Verify

```bash
# Check deployment logs
az webapp log tail --name airport-kiosk --resource-group airport

# Open in browser
az webapp browse --name airport-kiosk --resource-group airport
```

## Redeployment

After making code changes, redeploy with:

```bash
zip -r deploy.zip main.py requirements.txt static/
az webapp deploy --name airport-kiosk --resource-group airport --src-path deploy.zip --type zip
```

## Troubleshooting

- **503 errors after deploy** — Check startup logs: `az webapp log tail --name airport-kiosk --resource-group airport`
- **401/403 from Azure AI** — Verify managed identity has `Cognitive Services User` role on the AI Services account
- **Blob upload failures** — Verify managed identity has `Storage Blob Data Contributor` on the storage account
- **Camera not working** — Camera access requires HTTPS; the `.azurewebsites.net` domain provides this automatically
