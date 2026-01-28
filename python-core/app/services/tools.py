import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ToolsService:
    def __init__(self):
        self.tavily_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Tavily client if key is available"""
        if settings.tavily_api_key:
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
                logger.info("Tavily client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {e}")
                self.tavily_client = None
        else:
            logger.warning("Tavily API key not found in settings")

    def search_web(self, query: str, max_results: int = 3) -> str:
        """
        Search the web using Tavily API.
        
        Args:
            query: Search query string
            max_results: Number of results to return
            
        Returns:
            Formatted string with search results or error message
        """
        if not self.tavily_client:
            # Try re-initializing in case key was added later (e.g. via .env reload)
            self._initialize_client()
            if not self.tavily_client:
                return "[Search unavailable: TAVILY_API_KEY missing]"

        try:
            logger.info(f"Searching web for: {query}")
            response = self.tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results
            )
            
            results = []
            for result in response.get("results", []):
                title = result.get("title", "No title")
                url = result.get("url", "#")
                content = result.get("content", "No content")
                results.append(f"Source: {title} ({url})\nContent: {content}\n")
            
            formatted_results = "\n---\n".join(results)
            return formatted_results if formatted_results else "[No relevant search results found]"

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"[Search failed: {str(e)}]"

# Global instance
tools = ToolsService()
