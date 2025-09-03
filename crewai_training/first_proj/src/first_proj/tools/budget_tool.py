DEFAULT_BENCHMARKS = {
    "venue": (500, 1500),
    "food_beverage": (20, 50),
    "decor": (200, 600),
    "entertainment": (300, 1000),
    "gifts": (5, 20),
}

def budget_tool(item: str, guest_count: int = 50) -> str:
    """
    Return benchmarked costs for event line items.
    """
    item = item.lower().strip()
    if item not in DEFAULT_BENCHMARKS:
        return "Unknown item; valid keys: " + ", ".join(DEFAULT_BENCHMARKS.keys())
    low, high = DEFAULT_BENCHMARKS[item]
    if item in ("food_beverage", "gifts"):
        return f"{item}: {low*guest_count} – {high*guest_count} (scaled for {guest_count} guests)"
    return f"{item}: {low} – {high}"

budget_tool = {
    "name": "budget_tool",
    "description": "Returns benchmarked costs for event line items (venue, food_beverage, decor, entertainment, gifts).",
    "func": budget_tool,
}
