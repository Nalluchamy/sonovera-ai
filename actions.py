import datetime
import calendar
from typing import Dict, Any

def get_current_time() -> str:
    """Returns the current date and time."""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def get_calendar_info() -> str:
    """Returns the current month's calendar."""
    now = datetime.datetime.now()
    return calendar.month(now.year, now.month)

def search_web(query: str) -> str:
    """Searches the web for a query and returns the top results."""
    from duckduckgo_search import DDGS
    try:
        results = ""
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results += f"Title: {r['title']}\nLink: {r['href']}\nBody: {r['body']}\n\n"
        return results if results else "No results found."
    except Exception as e:
        return f"Error searching the web: {e}"

# Tool definitions for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_calendar_info",
            "description": "Get the calendar for the current month.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for real-time information, news, or facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    }
]

def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Dispatches tool execution based on name."""
    if name == "get_current_time":
        return get_current_time()
    elif name == "get_calendar_info":
        return get_calendar_info()
    elif name == "search_web":
        return search_web(args.get("query", ""))
    else:
        return f"Error: Tool '{name}' not found."

