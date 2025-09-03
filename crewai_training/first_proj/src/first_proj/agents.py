# agents.py
from crewai import Agent
from first_proj.tools.search_tool import search_web_tool
from first_proj.tools.scrape_tool import scrape_tool
from first_proj.tools.weather_tool import weather_tool
from first_proj.tools.maps_tool import maps_tool
from first_proj.tools.budget_tool import budget_tool
from crewai import LLM


llm = LLM(
    model="gemini/gemini-2.0-flash",
    temperature=0.7,
)

# ------------------ Research Agent ------------------
research_agent = Agent(
    llm=llm,
    role="Event Researcher",
    goal=(
        "Find the best venues, activities, caterers, and vendors matching the user's budget, "
        "guest count, date, location, and preferences."
    ),
    backstory=(
        "You are a meticulous event concierge with a knack for curated shortlists. "
        "You cite sources and provide pros/cons for each option."
    ),
    tools=[search_web_tool, scrape_tool],
    allow_delegation=False,
    verbose=False,
)

# # ------------------ Planner Agent ------------------
# planner_agent = Agent(
#     llm=llm,
#     role="Itinerary Planner",
#     goal=(
#         "Design a realistic, conflict-free event schedule and weekend itinerary, including buffer times, "
#         "setup/teardown logistics, and vendor timelines."
#     ),
#     backstory=(
#         "Experienced event producer who plans seamless run-of-show schedules that actually work in the real world."
#     ),
#     tools=[maps_tool, weather_tool],
#     allow_delegation=False,
#     verbose=True,
# )

# # ------------------ Budget Agent ------------------
# budget_agent = Agent(
#     role="Budget Analyst",
#     goal=(
#         "Produce an itemized budget with estimates, taxes/fees, contingency, and per-guest cost."
#     ),
#     backstory=(
#         "Former FP&A analyst turned event accountant. Conservative estimates, clear assumptions, and tidy tables."
#     ),
#     tools=[budget_tool],
#     allow_delegation=False,
#     verbose=True,
# )

# # ------------------ Coordinator Agent ------------------
# coordinator_agent = Agent(
#     role="Event Coordinator",
#     goal=(
#         "Consolidate research, itinerary, and budget into a concise brief with next steps, contacts, and risks."
#     ),
#     backstory=(
#         "You turn messy planning threads into one clean stakeholder-ready brief with decision points."
#     ),
#     tools=[],  # No tools required
#     allow_delegation=False,
#     verbose=True,
# )
