"""Provider-neutral web-search interface for industry research."""

from pydantic import BaseModel


class WebSearchResult(BaseModel):
    """Represents one structured result returned by a web search."""

    title: str
    snippet: str
    source: str


class WebSearchTool:
    """Web Search Adapter awaiting integration with a real search provider."""

    def search(self, query: str) -> list[WebSearchResult]:
        """Return no results in V1 because no real Web Search Provider is connected.

        Returning an empty list prevents the adapter from generating fake Evidence.
        """
        return []
