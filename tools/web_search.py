"""Mock web-search interface for industry research."""

from pydantic import BaseModel


class WebSearchResult(BaseModel):
    """Represents one structured result returned by a web search."""

    title: str
    snippet: str
    source: str


class WebSearchTool:
    """Provides deterministic mock web-search results for PM Copilot V1."""

    def search(self, query: str) -> list[WebSearchResult]:
        """Return mock CNC tool-management results for supported keywords."""
        normalized_query = query.lower()
        if "刀具" not in query and "tool" not in normalized_query:
            return []

        return [
            WebSearchResult(
                title="CNC Tool Life Management",
                snippet=(
                    "刀具寿命管理通常会记录累计加工时间、加工次数或加工距离，"
                    "并在达到阈值前进行预警。"
                ),
                source="https://example.com/tool-life",
            ),
            WebSearchResult(
                title="Tool Management in CNC",
                snippet=(
                    "CNC 刀具管理通常需要维护刀具身份、规格、设备位置、"
                    "使用状态和适用工艺。"
                ),
                source="https://example.com/tool-management",
            ),
            WebSearchResult(
                title="Automatic Tool Changer Basics",
                snippet=(
                    "自动换刀依赖刀具编号、刀位、刀具状态和机床控制系统之间的"
                    "一致数据。"
                ),
                source="https://example.com/atc",
            ),
        ]
