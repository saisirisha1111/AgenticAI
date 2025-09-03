#!/usr/bin/env python
import sys


from datetime import datetime
from first_proj.crew import crew

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    inputs = {
        "event_type": "Corporate Offsite",
        "city": "Bengaluru, India",
        "start_date": "2025-10-10",
        "end_date": "2025-10-12",
        "guest_count": 60,
        "budget_currency": "INR",
        "budget_amount": 1500000,
        "preferences": "team-building, outdoor-friendly, vegetarian catering, evening networking",
    }
    result = crew.kickoff(inputs=inputs)
    return result



if __name__ == "__main__":
# Example run. Replace with CLI/HTTP as needed.
    output = run()
    print("\n===== FINAL BRIEF =====\n")
    print(output)


# def train():
#     """
#     Train the crew for a given number of iterations.
#     """
#     inputs = {
#         "topic": "AI LLMs",
#         'current_year': str(datetime.now().year)
#     }
#     try:
#         FirstProj().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while training the crew: {e}")

# def replay():
#     """
#     Replay the crew execution from a specific task.
#     """
#     try:
#         FirstProj().crew().replay(task_id=sys.argv[1])

#     except Exception as e:
#         raise Exception(f"An error occurred while replaying the crew: {e}")

# def test():
#     """
#     Test the crew execution and returns the results.
#     """
#     inputs = {
#         "topic": "AI LLMs",
#         "current_year": str(datetime.now().year)
#     }
    
#     try:
#         FirstProj().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while testing the crew: {e}")
