import os
import tempfile
import json
import base64
import logging
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage, texttospeech
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.genai import types
import socketio
from Backend.tools.processing_tool import process_document
from typing import Dict, Any
import re
import google.adk as adk
from google.cloud import bigquery

# BigQuery Setup
bq_client = bigquery.Client()
DATASET = "StartupDetails"
TABLE = "StartupDetails"

# ===== Logging =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline_logger")

# ===== GCS Setup =====
BUCKET_NAME = "ai-analyst-uploads-file"
storage_client = storage.Client()

# ===== Request Schema =====
class DocRequest(BaseModel):
    bucket_name: str
    file_paths: list[str]

# ===== JSON Helper =====
def fill_json(data, key_path, value):
    keys = key_path.split(".")
    d = data
    for k in keys[:-1]:
        d = d[k]
    d[keys[-1]] = value

# ===== TTS Helper =====
def synthesize_speech_base64(text: str):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    return base64.b64encode(response.audio_content).decode("utf-8")

# ===== Agents =====
# Root agent
instruction = """
You are a Data Ingestion and Structuring Agent for startup evaluation.

Tasks:
1. You MUST call the `process_document` tool with the input {"bucket_name": "...", "file_paths": ["..."]}.
2. Only after receiving the tool response, you should generate your analysis.
3. Analyze text recieved from the tool and Output must be *only* valid JSON without Markdown or extra text with this schema:

{
  "startup_name": "string or null",
  "sector": "string or null (GICS classification)",
  "stage": "string or null (funding stage)",
  "traction": {
    "current_mrr": number or null,
    "mrr_growth_trend": "string or null",
    "active_customers": number or null,
    "new_customers_this_month": number or null,
    "average_subscription_price": number or null,
    "customer_lifespan_months": number or null
  },
  "financials": {
    "ask_amount": number or null,
    "equity_offered": number or null,
    "revenue": number or null,
    "burn_rate": number or null,
    "monthly_expenses": number or null,
    "cash_balance": number or null,
    "marketing_spend": number or null,
  },
  "team": {
    "ceo": "string or null",
    "cto": "string or null,
    "other_key_members": ["string", "string"]
  },
  "market": {
    "market_size_claim": "string or null",
    "target_market": "string or null"
  },
  "product_description": "string or null",
  "document_type": "pitch_deck | transcript | financial_statement | other"
}

SECTOR CLASSIFICATION (GICS Standards):
- "Technology" (Software, AI, SaaS, Cloud Computing, Cybersecurity, FinTech, HealthTech, EdTech, IoT)
- "Healthcare" (Biotech, Pharmaceuticals, Medical Devices, Digital Health, Telemedicine)
- "Financials" (Banking, Insurance, Payments, Blockchain/Crypto, WealthTech)
- "Consumer Discretionary" (E-commerce, Retail, Travel, Entertainment, Gaming, Automotive)
- "Consumer Staples" (Food & Beverage, Household Products, Personal Care)
- "Industrials" (Manufacturing, Logistics, Robotics, Aerospace, Construction)
- "Energy" (Clean Energy, Oil & Gas, Renewable Technology)
- "Materials" (Chemicals, Metals, Mining, Packaging)
- "Real Estate" (PropTech, Construction Tech, Real Estate Services)
- "Communication Services" (Telecom, Media, Social Media, Advertising Tech)
- "Utilities" (Water, Electric, Gas, Infrastructure Tech)

STAGE CLASSIFICATION:
- "Pre-Seed" (Idea stage, <$500k funding, pre-revenue, building MVP)
- "Seed" ($500k-$2M funding, $0-$50k MRR, product-market fit validation)
- "Series A" ($2M-$15M funding, $50k-$500k MRR, scaling customer acquisition)
- "Series B" ($15M-$50M funding, $500k-$5M MRR, expanding market share)
- "Series C" ($50M-$100M funding, $5M-$20M MRR, market leadership)
- "Series D+" ($100M+ funding, $20M+ MRR, pre-IPO or major expansion)
- "IPO" (Publicly traded or preparing for IPO)
- "Public" (Already public company)

RULES FOR SECTOR DETERMINATION:
- Classify based on the primary business model, not the technology used
- If it's a tech-enabled service, classify by the industry it serves (e.g., FinTech → Financials, HealthTech → Healthcare)
- Use the most specific GICS sector that applies
- If hybrid, choose the dominant revenue source

RULES FOR STAGE DETERMINATION:
- Use funding round mentions: "raising seed round" → "Seed", "Series A" → "Series A"
- Infer from financial metrics:
  * Pre-revenue, pre-product → "Pre-Seed"
  * <$50k MRR, raising <$2M → "Seed" 
  * $50k-$500k MRR, raising $2M-$15M → "Series A"
  * $500k-$5M MRR, raising $15M-$50M → "Series B"
  * $5M+ MRR, raising $50M+ → "Series C" or "Series D+"
- Use team size as indicator: <10 → Pre-Seed/Seed, 10-50 → Seed/Series A, 50-200 → Series A/B, 200+ → Series B+

EXTRACTION RULES:
- Extract these specific financial parameters for CAC/LTV calculations:
  * Monthly expenses (for net burn calculation)
  * Cash balance (for runway calculation) 
  * Marketing spend (for CAC calculation)
  * New customers this month (for CAC calculation)
  * Average subscription price (for LTV calculation)
  * Customer lifespan in months (for LTV calculation)
- If exact numbers aren't available, look for approximations (e.g., "~$50K monthly burn", "about 100 new customers")
- For sector: Look for industry descriptions, target market, product category
- For stage: Look for funding round mentions, revenue ranges, team size indicators
- No hallucinations - only extract what's explicitly stated or clearly implied
- Numbers extracted exactly as presented
- Missing values = null
- Final output must be valid JSON only, no additional text

EXAMPLES:
- A company building AI-powered accounting software: sector = "Financials", stage = "Series A" (if $1.2M ARR)
- A telemedicine platform for rural areas: sector = "Healthcare", stage = "Seed" (if raising $1.5M)
- An e-commerce marketplace for sustainable products: sector = "Consumer Discretionary", stage = "Series B" (if $3M MRR)
"""
root_agent = Agent(name="doc_ingest_agent", model="gemini-2.0-flash", instruction=instruction, tools=[process_document])

# Question Agent
question_agent = Agent(
    name="question_agent",
    model="gemini-2.0-flash",
    instruction="""
You are a Question Generation Agent.

Input: JSON object called `structured_json`.
Task:
1. Identify all null fields.
2. Generate human-friendly questions to fill them.
3. Return strictly JSON:

{
  "structured_json": { ... },
  "questions": { "missing_field_key": "natural question", ... },
  "status": "INTERMEDIATE"
}

Rules:
- Only include null fields.
- Do not produce extra commentary or markdown.
"""
)

# Filler Agent
class FillerAgent(Agent):
    structured_json: Dict[str, Any] = {}
    questions: Dict[str, str] = {}

    async def run(self, input_content, **kwargs):
        raw_text = input_content.parts[0].text.strip()
        cleaned_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.MULTILINE)
        try:
            content_dict = json.loads(cleaned_text)
        except json.JSONDecodeError:
            return types.Content(role="system", parts=[types.Part(text=json.dumps({"error": "Invalid JSON input"}))])

        self.structured_json = content_dict.get("structured_json", {})
        self.questions = content_dict.get("questions", {})
        return types.Content(role="system", parts=[types.Part(text=json.dumps({"status": "READY"}))])

filler_agent = FillerAgent(name="filler_agent", model="gemini-2.0-flash", instruction="Ask questions to fill missing fields in JSON.")

# ===== Session =====
session_service = InMemorySessionService()
app_name = "doc_app"
user_id = "user123"
session_id = "session1"

# ===== FastAPI + Socket.IO =====
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI(title="Doc Voice Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Combine Socket.IO with FastAPI
sio_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="ws")

# ===== Queue for clients waiting for first question =====
pending_first_questions: Dict[str, bool] = {}


def sanitize_for_bq(data):
    """
    Recursively convert strings with numbers to int/float and ensure proper types for BigQuery.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str):
                # Remove commas and convert to int/float if numeric
                v_clean = v.replace(',', '')
                if v_clean.isdigit():
                    data[k] = int(v_clean)
                else:
                    try:
                        data[k] = float(v_clean)
                    except ValueError:
                        data[k] = v  # leave as string
            elif isinstance(v, dict) or isinstance(v, list):
                sanitize_for_bq(v)
            elif v is None:
                data[k] = None
    elif isinstance(data, list):
        for i in range(len(data)):
            sanitize_for_bq(data[i])

    print("***************final json*****************",data)
    return data



@app.on_event("startup")
async def startup_event():
    await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

# ===== Upload Endpoint =====
@app.post("/upload-and-analyze")
async def upload_and_analyze(files: list[UploadFile], user_email: str = Form(...)):
    file_paths = []
    bucket = storage_client.bucket(BUCKET_NAME)
    for file in files:
        blob_name = f"{user_email}/{file.filename}"
        blob = bucket.blob(blob_name)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        blob.upload_from_filename(tmp_path)
        os.remove(tmp_path)
        file_paths.append(blob_name)

    req = DocRequest(bucket_name=BUCKET_NAME, file_paths=file_paths)
    content = types.Content(role="user", parts=[types.Part(text=req.json())])

    # Run root agent
    runner_root = adk.Runner(agent=root_agent, app_name=app_name, session_service=session_service)
    root_output = None
    async for event in runner_root.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response():
            root_output = event.content

    # Run question agent
    runner_q = adk.Runner(agent=question_agent, app_name=app_name, session_service=session_service)
    question_output = None
    async for event in runner_q.run_async(user_id=user_id, session_id=session_id, new_message=root_output):
        if event.is_final_response():
            question_output = event.content

    await filler_agent.run(question_output)

    # If client already connected, emit immediately, else mark pending
    if sio.manager.rooms.get(user_email):
        await emit_next_question(user_email)
    else:
        pending_first_questions[user_email] = True

    return JSONResponse({"status": "ok", "message": "Files uploaded and analysis started."})

# ===== Emit Next Question =====
async def emit_next_question(user_email):
    if filler_agent.questions:
        key, question = next(iter(filler_agent.questions.items()))
        audio_b64 = synthesize_speech_base64(question)
        await sio.emit("new_question", {"key": key, "text": question, "audio_b64": audio_b64}, room=user_email)
    else:
        final_data = sanitize_for_bq(filler_agent.structured_json)

        # Insert into BigQuery
        table_id = f"{bq_client.project}.{DATASET}.{TABLE}"
        try:
            errors = bq_client.insert_rows_json(table_id, [final_data])
            if errors:
                print("❌ BigQuery Insert Errors:", errors)
            else:
                print("✅ Data inserted into BigQuery")
        except Exception as e:
            print("❌ Exception inserting into BigQuery:", e)

        # Send success message to frontend
        await sio.emit("final_json", {"status": "success", "message": "Startup details updated successfully"}, room=user_email)


# ===== Socket.IO Events =====

@sio.event
async def connect(sid, environ, auth):
    user_email = auth.get("user_email") if auth else None
    print(f"Client connected: {sid}, auth: {auth}")
    if user_email:
        await sio.enter_room(sid, user_email)
        # If a first question is pending, emit now
        if pending_first_questions.get(user_email):
            await emit_next_question(user_email)
            pending_first_questions.pop(user_email)

@sio.event
async def disconnect(sid):
    print("Client disconnected:", sid)

@sio.on("answer")
async def receive_answer(sid, data):
    answer = data.get("answer")
    user_email = data.get("user_email")
    key = data.get("key")
    if not answer or not user_email or not key:
        return
     # Sanitize answer before filling JSON
    if isinstance(answer, str):
        answer_clean = answer.replace(',', '')
        if answer_clean.isdigit():
            answer = int(answer_clean)
        else:
            try:
                answer = float(answer_clean)
            except ValueError:
                pass
    fill_json(filler_agent.structured_json, key, answer)
    filler_agent.questions.pop(key, None)
    await emit_next_question(user_email)