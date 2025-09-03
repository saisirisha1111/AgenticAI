# from crewai_tools import WebsiteSearchTool

# import os

# # Instantiate Web Search Tool
# web_search_tool = WebsiteSearchTool()

from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults 
import json


@tool
def search_web_tool(query: str):
    """
    Searches the web and returns results.
    """
    search_tool = DuckDuckGoSearchResults(num_results=10, verbose=True)
    return search_tool.run(query)

