import io
import json
import base64
import time
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Prevent ANY root-level handlers from writing to our detection log
logging.basicConfig(level=logging.WARNING, handlers=[logging.StreamHandler()])
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("airport-vision")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.handlers.clear()
_fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_fh = logging.FileHandler("detections.log", mode="a")
_fh.setFormatter(_fmt)
logger.addHandler(_fh)
# Also log detections to stdout (captured by App Service / App Insights)
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
logger.addHandler(_sh)

# Console logger — verbose timing only in DEBUG mode
console = logging.getLogger("console")
console.setLevel(logging.DEBUG if DEBUG else logging.WARNING)
console.propagate = False
console.handlers.clear()
_ch = logging.StreamHandler()
_ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
console.addHandler(_ch)

if DEBUG:
    console.info("DEBUG mode enabled — verbose timing logs active")

app = FastAPI(title="Airport Object Detection")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

endpoint = os.getenv("AZURE_AI_SERVICES_ENDPOINT")
credential = DefaultAzureCredential()
client = ImageAnalysisClient(endpoint=endpoint, credential=credential)

llm_client = AzureOpenAI(
    azure_endpoint=endpoint,
    azure_ad_token_provider=lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token,
    api_version="2024-12-01-preview",
)
llm_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-nano")

# Azure Blob Storage for captured images
storage_account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=credential) if storage_account_url else None
IMAGES_CONTAINER = "images"


def upload_image_to_blob(image_data: bytes, endpoint_name: str):
    """Upload captured image to Azure Blob Storage in background."""
    if not blob_service_client:
        return
    try:
        container_client = blob_service_client.get_container_client(IMAGES_CONTAINER)
        now = datetime.now(timezone.utc)
        blob_name = f"{endpoint_name}/{now.strftime('%Y/%m/%d')}/{now.strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        container_client.upload_blob(name=blob_name, data=image_data, overwrite=True)
        console.debug(f"[Blob] Uploaded {blob_name} ({len(image_data)} bytes)")
    except Exception as e:
        console.warning(f"[Blob] Upload failed: {e}")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/detect")
async def detect_objects(request: Request, image: UploadFile = File(...)):
    client_ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    t0 = time.perf_counter()
    image_data = await image.read()
    t_read = time.perf_counter()
    console.debug(f"[CV] Image read: {len(image_data)} bytes in {(t_read-t0)*1000:.0f}ms")

    upload_image_to_blob(image_data, "detect")

    result = client.analyze(
        image_data=image_data,
        visual_features=[VisualFeatures.OBJECTS],
    )
    t_api = time.perf_counter()
    console.debug(f"[CV] Azure Vision API call: {(t_api-t_read)*1000:.0f}ms")

    detections = []
    if result.objects is not None:
        for obj in result.objects.list:
            label = obj.tags[0].name if obj.tags else "unknown"
            confidence = obj.tags[0].confidence if obj.tags else 0
            detections.append({
                "label": label,
                "confidence": confidence,
                "boundingBox": {
                    "x": obj.bounding_box.x,
                    "y": obj.bounding_box.y,
                    "w": obj.bounding_box.width,
                    "h": obj.bounding_box.height,
                },
            })

    labels = [d['label'] for d in detections]
    logger.info(f"[ComputerVision] ip={client_ip} | {', '.join(labels) if labels else 'no objects'}")
    console.info(f"[CV] ip={client_ip} | Total: {(time.perf_counter()-t0)*1000:.0f}ms | {len(detections)} objects: {', '.join(labels)}")

    return {"objects": detections}


@app.post("/detect-llm")
async def detect_objects_llm(request: Request, image: UploadFile = File(...)):
    client_ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    t0 = time.perf_counter()
    image_data = await image.read()
    b64_image = base64.b64encode(image_data).decode("utf-8")
    t_encode = time.perf_counter()
    console.debug(f"[LLM-Detect] Image read+encode: {len(image_data)} bytes in {(t_encode-t0)*1000:.0f}ms")

    upload_image_to_blob(image_data, "detect-llm")

    response = llm_client.chat.completions.create(
        model=llm_deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an airport X-ray baggage screening system. Analyze the image as if it were "
                    "from an airport security X-ray scanner or a live security camera feed. "
                    "Identify ALL objects, paying special attention to prohibited/dangerous items: "
                    "pistols, revolvers, firearms, knives, blades, scissors, darts, explosives, "
                    "lighters, aerosol cans, liquids, batteries, electronics, wires, tools, "
                    "and any other security-relevant items. Also identify normal items like bags, "
                    "clothing, shoes, laptops, phones, bottles, zippers, boards, keys, coins. "
                    "For each object, provide: label, confidence (0.0-1.0), and if threat detected "
                    "set 'threat' to true. Respond ONLY with a JSON array, no markdown, no explanation. "
                    'Example: [{"label": "pistol", "confidence": 0.93, "threat": true}, '
                    '{"label": "laptop", "confidence": 0.95, "threat": false}]'
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this image for airport security screening. List all objects detected."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}", "detail": "low"},
                    },
                ],
            },
        ],
        max_completion_tokens=300,
    )
    t_llm = time.perf_counter()
    console.debug(f"[LLM-Detect] LLM API call: {(t_llm-t_encode)*1000:.0f}ms")

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if the model wraps them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"LLM returned non-JSON: {raw}")
        items = []

    detections = [
        {
            "label": item.get("label", "unknown"),
            "confidence": item.get("confidence", 0),
            "threat": item.get("threat", False),
        }
        for item in items
    ]

    threats = [d['label'] for d in detections if d.get('threat')]
    safe = [d['label'] for d in detections if not d.get('threat')]
    parts = []
    if threats:
        parts.append(f"THREAT: {', '.join(threats)}")
    if safe:
        parts.append(f"safe: {', '.join(safe)}")
    logger.info(f"[LLM] ip={client_ip} | {' | '.join(parts) if parts else 'no objects'}")
    console.info(f"[LLM-Detect] ip={client_ip} | Total: {(time.perf_counter()-t0)*1000:.0f}ms | {len(detections)} objects")

    return {"objects": detections}


@app.get("/kiosk")
async def kiosk():
    return FileResponse("static/kiosk.html")


@app.post("/kiosk/check")
async def kiosk_check(request: Request, image: UploadFile = File(...)):
    client_ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    t0 = time.perf_counter()
    image_data = await image.read()
    b64_image = base64.b64encode(image_data).decode("utf-8")
    t_encode = time.perf_counter()
    console.debug(f"[Kiosk] Image read+encode: {len(image_data)} bytes in {(t_encode-t0)*1000:.0f}ms")

    upload_image_to_blob(image_data, "kiosk")

    def generate():
        stream = llm_client.chat.completions.create(
            model=llm_deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an airport kiosk assistant helping passengers determine if an item "
                        "is allowed in CABIN (carry-on) baggage based on international aviation security "
                        "rules (ref: HK CAD packing tips, ICAO guidelines).\n\n"
                        "PROHIBITED IN CABIN BAGGAGE:\n"
                        "Cat 1 - Explosives & incendiary: ammunition, blasting caps, detonators, fuses, "
                        "mines, grenades, fireworks, party poppers, toy caps, smoke canisters, dynamite, "
                        "gunpowder, plastic explosives, replica explosive devices.\n"
                        "Cat 2 - Guns & stunning devices: firearms (pistols, revolvers, rifles, shotguns), "
                        "toy/replica/imitation guns, gun lighters, compressed gas guns, pellet guns, "
                        "signal flare pistols, starter pistols, stun guns, stun batons, animal stunners.\n"
                        "Cat 3 - Chemicals: mace, pepper spray, capsicum spray, acid spray, tear gas, "
                        "animal repellent spray, reactive chemical mixtures.\n"
                        "Cat 4 - Sharp/edged objects & projectiles: axes, hatchets, cleavers, ice axes, "
                        "ice picks, ice skates, razor blades, open razors, utility knives, box cutters, "
                        "bows, crossbows, arrows, harpoon guns, spear guns, slingshots, catapults, "
                        "flick knives (any blade length), knives with metal blades (any length, except "
                        "round-ended blunt tip), scissors with blades >6cm from fulcrum, martial arts "
                        "equipment with sharp edges, swords, sabres, darts, ski poles.\n"
                        "Cat 5 - Workers' tools: crowbars, drills (including cordless), screwdrivers "
                        "and chisels with blades/shafts >6cm, saws (including cordless), blowtorches, "
                        "bolt guns, nail guns, hammers, pliers, wrenches/spanners.\n"
                        "Cat 6 - Blunt instruments: baseball/softball bats, billiard/pool cues, "
                        "cricket bats, hockey sticks, lacrosse sticks, golf clubs, billy clubs, "
                        "blackjacks, night sticks, nunchaku, knuckledusters, kubotans.\n\n"
                        "LIQUIDS/GELS/AEROSOLS (LAG) RULES - IMPORTANT:\n"
                        "- Each container max 100ml capacity. If container is >100ml it is PROHIBITED even "
                        "if only part-filled. Estimate volume from the image: standard water bottle is "
                        "~500ml (PROHIBITED), soda can ~330ml (PROHIBITED), juice box ~200ml (PROHIBITED), "
                        "small toiletry/travel bottle ~100ml or less (ALLOWED if in clear bag). "
                        "Any bottle, can, or container that appears larger than a small travel-size "
                        "container should be flagged as >100ml and PROHIBITED.\n"
                        "- All containers <=100ml must be in ONE transparent re-sealable plastic bag (max 1 litre)\n"
                        "- One bag per passenger, presented separately at screening\n"
                        "- Exempt: medications, baby milk/food, special dietary (subject to verification)\n\n"
                        "LITHIUM BATTERIES:\n"
                        "- PEDs with lithium batteries in checked bag: must be completely switched off\n"
                        "- Damaged/defective/recalled lithium batteries: NOT allowed on aircraft\n"
                        "- Power banks: cabin only, not in checked baggage, max 100Wh (101-160Wh needs airline approval)\n\n"
                        "ALLOWED IN CABIN:\n"
                        "- Electronics: laptops, tablets, phones, cameras, chargers, power banks (<100Wh)\n"
                        "- Safety/disposable razors with blades in cartridge\n"
                        "- Scissors with blades <=6cm from fulcrum\n"
                        "- Round-ended blunt-tip knives\n"
                        "- Nail clippers, tweezers\n"
                        "- Food, snacks, empty water bottles\n"
                        "- Clothing, books, travel pillows\n"
                        "- Medications, baby items\n\n"
                        "DANGEROUS GOODS (ICAO 9 classes - prohibited unless small qty with conditions):\n"
                        "Class 1: Explosives, Class 2: Gases, Class 3: Flammable liquids, "
                        "Class 4: Flammable solids, Class 5: Oxidizers, Class 6: Toxic/infectious, "
                        "Class 7: Radioactive, Class 8: Corrosive, Class 9: Misc dangerous.\n\n"
                        "Analyze the image. Identify the item(s) shown. For liquids, estimate the container "
                        "volume and flag as prohibited if >100ml. Respond ONLY with JSON, no markdown:\n"
                        '{"item": "name of item", "allowed": true/false, "category": "which category if prohibited, or allowed", '
                        '"reason": "brief explanation referencing the specific rule", "tip": "helpful travel tip"}'
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Can I carry this item in my carry-on bag on the plane?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}", "detail": "high"},
                        },
                    ],
                },
            ],
            max_completion_tokens=400,
            stream=True,
        )

        t_first = None
        collected = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                if t_first is None:
                    t_first = time.perf_counter()
                    console.debug(f"[Kiosk] Time to first token: {(t_first-t_encode)*1000:.0f}ms")
                collected += token
                yield f"data: {json.dumps({'token': token})}\n\n"

        t_done = time.perf_counter()
        console.debug(f"[Kiosk] Stream complete: {(t_done-t_encode)*1000:.0f}ms total, {len(collected)} chars")

        # Parse final result for logging
        raw = collected.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        console.debug(f"[Kiosk] Raw LLM response: {raw}")
        try:
            result = json.loads(raw)
            status = "ALLOWED" if result.get("allowed") else "PROHIBITED"
            logger.info(f"[Kiosk] ip={client_ip} | {result.get('item', 'unknown')} -> {status}")
            console.info(f"[Kiosk] ip={client_ip} | Total: {(t_done-t0)*1000:.0f}ms | {result.get('item','unknown')} -> {status}")
        except json.JSONDecodeError:
            console.warning(f"[Kiosk] JSON parse failed: {raw}")
            logger.info(f"[Kiosk] ip={client_ip} | parse error")

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


app.mount("/static", StaticFiles(directory="static"), name="static")
