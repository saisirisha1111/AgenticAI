from crewai import Task
from textwrap import dedent
from first_proj.agents import research_agent


# 1) Understand requirements and constraints, then research options
requirements_and_research = Task(
description=dedent(
"""
**Input**: {event_type}, {city}, {start_date} → {end_date}, {guest_count} guests, budget {budget_currency} {budget_amount}, preferences: {preferences}


1) Restate the requirements and identify any ambiguities.
2) Research 5–8 strong candidate venues and 8–12 activity/vendor ideas.
3) For each candidate, include: name, short description, estimated price range, capacity, location area, and a source link.
4) Provide pros/cons and quickly score each (1–5) for fit.
5) If dates are weather-sensitive, call the weather tool for likely conditions.
6) Output a concise shortlist table followed by key insights.
"""
),
agent=research_agent,
expected_output=dedent(
"""
- Short restatement of requirements
- Shortlist tables (venues, vendors/activities) with source links
- Bulleted insights and watch-outs
"""
),
)


# # 2) Build a feasible itinerary and day-of schedule
# planning_and_itinerary = Task(
# description=dedent(
# """
# Using the selected top options from research and the constraints:
# - Plan a travel-aware schedule with setup, event blocks, buffers, and teardown.
# - Use the maps tool to estimate travel times between locations.
# - Consider likely weather windows from the weather tool.
# - Produce a human-friendly run-of-show and a guest-facing itinerary.
# """
# ),
# agent=planner_agent,
# expected_output=dedent(
# """
# - Run-of-show with timestamps
# - Guest itinerary (clear, friendly)
# - Vendor call sheet with contacts (placeholders if unknown)
# """
# ),
# )


# # 3) Build the budget
# budgeting = Task(
# description=dedent(
# """
# Create an itemized budget covering venue, food & beverage, decor, entertainment, AV, staffing, transport,
# printing, gifts, contingency (10%), and taxes/fees. Use budget tool to benchmark costs. Return both total and per-guest.
# """
# ),
# agent=budget_agent,
# expected_output=dedent(
# """
# Markdown table with columns: Item | Qty/Unit | Unit Cost | Subtotal. Include a totals section with taxes/fees, contingency, and per-guest.
# """
# ),
# )


# # 4) Final stakeholder brief
# final_brief = Task(
# description=dedent(
# """
# Consolidate research, itinerary, and budget into a single executive brief with:
# - Overview: what/where/when/for whom
# - Final shortlist + recommendations
# - Final run-of-show
# - Budget summary
# - Key risks & mitigations
# - Next actions (RACI-style ownership)
# """
# ),
# agent=coordinator_agent,
# expected_output=dedent(
# """
# A clean, well-structured markdown brief ready to share.
# """
# ),
# )