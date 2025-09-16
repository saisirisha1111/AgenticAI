import os
import tempfile
import asyncio
import pickle
import base64
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import storage
from google.adk.agents import Agent
import google.adk as adk
from google.adk.sessions import InMemorySessionService
from google.genai import types
# from tools.processing_tool import process_document
from Backend.tools.processing_tool import process_document
# from ..tools.email_extraction_tool import check_email_inbox
from Backend.tools.email_extraction_tool import check_email_inbox
from fastapi.middleware.cors import CORSMiddleware  
import json







# ===== GCS Config =====
BUCKET_NAME = "ai-analyst-uploads-files"
storage_client = storage.Client()

# ===== Request Schema =====
class DocRequest(BaseModel):
    bucket_name: str
    file_paths: list[str]

# ===== System Instruction =====
# ===== System Instruction =====
instruction = """
You are a Data Ingestion and Structuring Agent for startup evaluation.

Tasks:
1. If the user provides **only documents**, you MUST call the `process_document` tool with:
   {"bucket_name": "...", "file_paths": ["..."]}

2. If the user provides **only a founder email**, you MUST call the `email_extraction` tool with:
   {"founder_email": "..."}

3. If the user provides **both documents and a founder email**, you MUST call both tools:
   - First call `process_document` for the files.
   - Then call `email_extraction` for the founder’s email.
   - Combine the extracted text from both sources.

4. After getting the extracted text, analyze it and produce JSON strictly in this schema:

{
  "startup_name": "string or null",
  "traction": {
    "current_mrr": number or null,
    "mrr_growth_trend": "string or null",
    "active_customers": number or null,
    "other_metrics": ["string", "string"]
  },
  "financials": {
    "ask_amount": number or null,
    "equity_offered": number or null,
    "implied_valuation": number or null,
    "revenue": number or null,
    "burn_rate": number or null
  },
  "team": {
    "ceo": "string or null",
    "cto": "string or null",
    "other_key_members": ["string", "string"]
  },
  "market": {
    "market_size_claim": "string or null",
    "target_market": "string or null"
  },
  "product_description": "string or null",
  "document_type": "pitch_deck | transcript | financial_statement | email_thread | other"
}

Rules:
- Always ground responses on the extracted text only.
- Do not hallucinate values.
- Extract numbers exactly.
- Use null if data is missing.
- Final output must be valid JSON only.
"""


# ===== Define the Agent =====
root_agent = Agent(
    name="doc_ingest_agent",
    model="gemini-2.0-flash",
    instruction=instruction,
    tools=[process_document,check_email_inbox],
)

# ===== Session Service =====
session_service = InMemorySessionService()
app_name = "doc_app"
user_id = "user123"
session_id = "session1"

# ===== FastAPI App =====
app = FastAPI(title="Doc Ingestion Agent API")




# ===== Enable CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 👈 for testing; replace with your frontend URL in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

@app.post("/upload-and-analyze")
async def upload_and_analyze(
    files: list[UploadFile],
    user_email: str = Form(...),
    founder_email: str | None = Form(None)   # 👈 optional founder email
):
    """
    Uploads files to GCS, constructs request for the Agent, 
    and returns structured JSON. If founder_email is provided,
    it will also trigger email_extraction.
    """
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

    # Build agent input
    payload = {
        "bucket_name": BUCKET_NAME,
        "file_paths": file_paths
    }

    # If founder_email is provided, include it
    if founder_email:
        payload["founder_email"] = founder_email

    req_json = json.dumps(payload)

    runner = adk.Runner(agent=root_agent, app_name=app_name, session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=req_json)])

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        if event.is_final_response():
            return JSONResponse(content={"response": event.content.parts[0].text})