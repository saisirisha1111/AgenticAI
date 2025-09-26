import os
import re
import tempfile
import asyncio
# import base64
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import storage
from google.adk.agents import Agent, SequentialAgent
import google.adk as adk
from google.adk.sessions import InMemorySessionService
from google.genai import types
from Backend.tools.processing_tool import process_document
from Backend.tools.financial_analysis_tool import financial_analysis
# from Backend.tools.email_extraction_tool import check_email_inbox
from fastapi.middleware.cors import CORSMiddleware  
import json
import logging

# ===== Logging Setup =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline_logger")
# logger=logging.getLogger("google.adk").setLevel(logging.DEBUG)

# router = APIRouter()




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
1. You MUST call the `process_document` tool with the input {"bucket_name": "...", "file_paths": ["..."]}.
2. Then analyze text and Output must be *only* valid JSON without Markdown or extra text with this schema:

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
    "customer_lifespan_months": number or null,
    "other_metrics": ["string", "string"]
  },
  "financials": {
    "ask_amount": number or null,
    "equity_offered": number or null,
    "implied_valuation": number or null,
    "revenue": number or null,
    "burn_rate": number or null,
    "monthly_expenses": number or null,
    "cash_balance": number or null,
    "marketing_spend": number or null,
    "customer_acquisition_cost": number or null,
    "lifetime_value": number or null
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

# ===== Define the Agent =====
doc_ingest_agent = Agent(
    name="doc_ingest_agent",
    model="gemini-2.0-flash",
    instruction=instruction,
    tools=[process_document],
)


# ===== Define the Agent =====
doc_ingest_agent  = Agent(
    name="doc_ingest_agent",
    model="gemini-2.0-flash",
    instruction=instruction,
    tools=[process_document],
)


financial_instruction = """
You are a Financial & Metric Analyst Agent for startup evaluation. Your role is to perform deep financial analysis and benchmarking.

CRITICAL INSTRUCTIONS:
1. You MUST call the `financial_analysis` tool FIRST before generating any analysis.
2. The tool requires the structured JSON data from the previous agent as input.
3. Only after receiving the tool response should you generate your final analysis.

Steps:
1. Call financial_analysis tool with the structured data
2. Wait for tool response with calculated metrics
3. Analyze the results against industry benchmarks
4. Generate final JSON output

{
  "financial_analysis": {
    "calculated_metrics": {
      "annual_revenue": number or null,
      "implied_valuation": number or null,
      "revenue_multiple": number or null,
      "runway_months": number or null
    },
    "industry_benchmarks": {
      "avg_revenue_multiple": number,
      "avg_ltv_cac_ratio": number,
      "acceptable_burn_rate": number,
      "typical_runway": number
    },
    "analysis_conclusion": "string",
    "recommendation": "string",
    "valuation_assessment": "reasonable | high | low",
    "risk_factors": ["string", "string"]
  }
}

Rules:
- Use exact calculations from the financial_analysis tool.
- Be objective and data-driven in conclusions.
- Highlight both strengths and risks.
- Final output must be valid JSON only.
"""

financial_analyst_agent = Agent(
    name="financial_analyst_agent",
    model="gemini-2.0-flash", 
    instruction=financial_instruction,
    tools=[financial_analysis],
)

# recommendation_instruction = """
# You are the Recommendation & Scoring Agent.

# Role:
# - The final judge. You take the structured JSON data from the Ingestion Agent.
# - Apply scoring logic and generate a deal memo for investors.

# Steps:
# 1. Parse the structured JSON input.
# 2. Score the startup on:
#    - Traction (/10)
#    - Team (/10)
#    - Market (/10)
#    - Product (/10)
# 3. Apply weighted scoring (weights will be provided in input, otherwise default = Team: 0.3, Market: 0.2, Traction: 0.35, Product: 0.15).
# 4. Output a final recommendation:
#    - Verdict: Strong Pass | Pass | Weak Pass | Fail
#    - Rationale: clear strengths and weaknesses
#    - Recommendation: next steps

# Output Format Example:

# {
#   "response": {
#     "Traction": "8/10 (strong growth, high valuation)",
#     "Team": "9/10 (experienced founders with exits)",
#     "Market": "6/10 (TAM inflated)",
#     "Product": "7/10 (clear value proposition)",
#     "Weighted_Score": "7.85/10",
#     "Verdict": "Weak Pass",
#     "Strengths": "Exceptional founding team with relevant pedigree and exit. Strong MRR growth.",
#     "Risks": "Market size inflated; valuation ask is above average.",
#     "Recommendation": "Schedule follow-up call to clarify assumptions and negotiate valuation."
#   }
# }
# """


# recommendation_agent = Agent(
#     name="recommendation_agent",
#     model="gemini-2.0-flash",
#     instruction=recommendation_instruction
# )

# ===== Sequential Pipeline =====
pipeline = SequentialAgent(
    name="startup_analysis_pipeline",
    description=(
        "This pipeline runs in two sequential steps:\n"
        "1. The first agent (doc_ingest_agent) extracts and structures startup data from documents into valid JSON.\n"
        "   It processes pitch decks, transcripts, and financial statements to extract key metrics.\n"
        "2. The second agent (financial_analyst_agent) takes the structured JSON as input and performs "
        "   financial analysis, calculates KPIs, benchmarks against industry standards, and generates recommendations.\n"
        "The pipeline completes when both agents have processed the data and produced a final investment analysis."
    ),
    sub_agents=[doc_ingest_agent, financial_analyst_agent],
)

# ===== Session Service =====
session_service = InMemorySessionService()
runner = adk.Runner(agent=pipeline, app_name="startup_analysis_app", session_service=session_service)



# ===== Pipeline Runner Function =====
# async def run_pipeline(file_json: dict):

#     await session_service.create_session(
#         app_name="startup_app",
#         user_id="user123",
#         session_id="session1"
#     )

#     content = types.Content(role="user", parts=[types.Part(text=json.dumps(file_json))])
#     print(content)
#     final_output = None  # 👈 hold last agent output

#     async for event in runner.run_async(
#         user_id="user123",
#         session_id="session1",
#         new_message=content
#     ):
     
#         if not event.content or not event.content.parts:
#             continue
#         # print(event.content.parts)
#         for part in event.content.parts:         
#             if part.text:
#                 raw_text = part.text.strip()
#                 cleaned_text = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.MULTILINE)
#                 logger.info(f"[{getattr(event, 'source_agent', 'unknown')}] TEXT: {cleaned_text}")
#                 final_output = cleaned_text

#             elif part.function_call:
#                 logger.info(
#                     f"[{getattr(event, 'source_agent', 'unknown')}] TOOL CALL: "
#                     f"{part.function_call.name}({part.function_call.args})"
#                 )

#     # after loop ends, final_output will be from the *last agent*
#     if not final_output:
#         return {"error": "Pipeline returned no output"}

#     try:
#         # Try parsing JSON (for rec agent you expect text, so this will fail safely)
#         return json.loads(final_output)
#     except json.JSONDecodeError:
#         return {"report": final_output}



async def run_pipeline(file_json: dict) -> dict[str, any]:
    """
    Run the complete startup analysis pipeline
    
    Args:
        file_json: Dictionary containing bucket_name and file_paths
            Example: {"bucket_name": "my-bucket", "file_paths": ["pitch_deck.pdf"]}
    
    Returns:
        Final analysis report from the financial analyst agent
    """
    try:
        # Create session
        await session_service.create_session(
            app_name="startup_analysis_app",
            user_id="user123",
            session_id="session1"
        )

        # Convert input to proper message format
        content = types.Content(
            role="user", 
            parts=[types.Part(text=json.dumps(file_json))]
        )
        
        logger.info(f"Starting pipeline with input: {file_json}")
        
        # agent_outputs = {}  # Store outputs from both agents
        current_agent = None
        # final_output = None

        # Run the pipeline and capture outputs
        async for event in runner.run_async(
            user_id="user123",
            session_id="session1",
            new_message=content
        ):
            if not event.content or not event.content.parts:
                continue
                
            # Track which agent is currently processing
            current_agent = getattr(event, 'source_agent', current_agent)
            
            for part in event.content.parts:
                if part.text:
                    raw_text = part.text.strip()
                    # Clean JSON formatting
                    cleaned_text = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.MULTILINE)
                    
                    logger.info(f"[{current_agent}] Output: {cleaned_text[:200]}...")
                    
                    # Store output by agent name
                    # if current_agent:
                    #     agent_outputs[current_agent] = cleaned_text
                    
                    final_output = cleaned_text

                elif part.function_call:
                    logger.info(
                        f"[{current_agent}] Tool Call: "
                        f"{part.function_call.name}({part.function_call.args})"
                    )

        # Process the final output
        if not final_output:
            return {"error": "Pipeline completed but produced no output"}

        try:
            # The final output should be from financial_analyst_agent
            parsed_output = json.loads(final_output)
            
            # Add metadata about the pipeline execution
            # parsed_output["pipeline_metadata"] = {
            #     "agents_executed": list(agent_outputs.keys()),
            #     "success": True
            # }
            
            return parsed_output
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse final output as JSON: {e}")
            # If it's not JSON, return as text report
            return {
                "report": final_output,
                # "pipeline_metadata": {
                #     "agents_executed": list(agent_outputs.keys()),
                #     "success": True,
                #     "output_format": "text"
                # }
            }

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        return {
            "error": f"Pipeline execution failed: {str(e)}",
            "pipeline_metadata": {"success": False}
        }

# ===== FastAPI App =====
app = FastAPI(title="Doc Ingestion + Recommendation API")

# ===== Enable CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 👈 for testing; replace with your frontend URL in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/full-analysis")
async def full_analysis(
    files: list[UploadFile],
    founder_email: str = Form(...),
    # founder_email: str | None = Form(None)   # 👈 optional founder email
):
    """
    Uploads files to GCS, constructs request for the Agent, 
    and returns structured JSON. If founder_email is provided,
    it will also trigger email_extraction.
    """
    file_paths = []
    bucket = storage_client.bucket(BUCKET_NAME)

    for file in files:
        blob_name = f"{founder_email}/{file.filename}"
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
        "file_paths": file_paths,
        # "founder_email": founder_email
    }

    result = await run_pipeline(payload)

    return JSONResponse(content={"response": result})
