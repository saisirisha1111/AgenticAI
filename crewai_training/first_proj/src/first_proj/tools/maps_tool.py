
def maps_tool(distance_km: float, mode: str = "car") -> str:
    """Estimate travel time given straight-line distance in km and mode = car|walk|bike.
    Returns a string like "~18 minutes" suitable for itinerary planning.
    """
    speeds = {
    "car": 35.0, # km/h conservative urban avg
    "walk": 4.5,
    "bike": 15.0,
    }
    v = speeds.get(mode, 35.0)
    hours = distance_km / v
    minutes = int(round(hours * 60))
    return f"~{minutes} minutes by {mode}"

maps_tool = {
    "name": "maps_tool",
    "description": "Estimates travel time given distance in km and transport mode (car, walk, bike).",
    "func": maps_tool,
}


