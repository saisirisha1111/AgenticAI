from crewai import Crew, Process,LLM
# from first_proj.agents import research_agent, planner_agent, budget_agent, coordinator_agent
from first_proj.agents import research_agent
# from first_proj.tasks import (
# requirements_and_research,
# planning_and_itinerary,
# budgeting,
# final_brief,
# )
from first_proj.tasks import (
requirements_and_research,
)
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators


 
# crew = Crew(
#     agents=[research_agent, planner_agent, budget_agent, coordinator_agent],
#     tasks=[requirements_and_research, planning_and_itinerary, budgeting, final_brief],
#     process=Process.sequential,
#     verbose=True,
# )

crew = Crew(
    agents=[research_agent],
    tasks=[requirements_and_research],
    process=Process.sequential,
    verbose=True,
)