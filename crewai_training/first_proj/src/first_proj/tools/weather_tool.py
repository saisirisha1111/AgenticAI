from datetime import datetime



def weather_tool(city: str, date: str) -> str:
    """Lightweight heuristic weather lookahead (no external API). Date format: YYYY-MM-DD.
    Returns likely conditions summary to help planning.
    """
    # NOTE: Replace with a real API if desired.
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        month = dt.month
    except Exception:
        return "Invalid date format; expected YYYY-MM-DD"


    # Super-simplified seasonal heuristic (customize per region if needed)
    if month in (12, 1, 2):
        season = "winter"
        conditions = "cool to cold; chance of rain in coastal cities"
    elif month in (3, 4, 5):
        season = "spring"
        conditions = "mild; scattered showers possible"
    elif month in (6, 7, 8):
        season = "summer"
        conditions = "warm to hot; plan shade and hydration"
    else:
        season = "fall"
        conditions = "pleasant; occasional rain; early sunsets"


    return f"Season: {season}. Likely conditions for {city} around {date}: {conditions}."

weather_tool = {
    "name": "weather_tool",
    "description": "Provides heuristic weather forecast based on city and date (YYYY-MM-DD).",
    "func": weather_tool,
}


