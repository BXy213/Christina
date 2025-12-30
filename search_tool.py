"""
网络搜索工具
支持多种搜索引擎：Tavily / SerpAPI / DuckDuckGo
"""
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import Tool
from config import config
from logger import logger


def create_search_tool() -> Tool:
    """
    创建网络搜索工具
    根据配置自动选择搜索引擎，失败时自动回退
    
    Returns:
        搜索工具实例
    """
    engine = config.search_engine
    
    # 按优先级尝试创建搜索工具
    if engine == 'tavily':
        try:
            tool = _create_tavily_tool()
            logger.log("[OK] Search engine: Tavily (recommended)")
            return tool
        except Exception as e:
            logger.warning(f"[WARN] Tavily init failed: {e}, fallback to DuckDuckGo")
    
    elif engine == 'serpapi':
        try:
            tool = _create_serpapi_tool()
            logger.log("[OK] Search engine: SerpAPI")
            return tool
        except Exception as e:
            logger.warning(f"[WARN] SerpAPI init failed: {e}, fallback to DuckDuckGo")
    
    # 默认或回退使用 DuckDuckGo
    tool = _create_duckduckgo_tool()
    logger.log("[OK] Search engine: DuckDuckGo (free, limited features)")
    return tool


def _create_tavily_tool() -> Tool:
    """
    创建 Tavily 搜索工具
    
    Returns:
        Tavily 搜索工具
    """
    from langchain_community.tools.tavily_search import TavilySearchResults
    
    search_tool = TavilySearchResults(
        tavily_api_key=config.TAVILY_API_KEY,
        max_results=config.MAX_SEARCH_RESULTS
    )
    search_tool.name = "web_search"
    search_tool.description = (
        "专业的网络搜索工具，用于查找最新信息。"
        "当用户询问实时信息、新闻、最新数据时使用。"
        "输入应该是搜索查询关键词。"
    )
    return search_tool


def _create_serpapi_tool() -> Tool:
    """
    创建 SerpAPI 搜索工具
    
    Returns:
        SerpAPI 搜索工具
    """
    from langchain_community.utilities import SerpAPIWrapper
    
    search = SerpAPIWrapper(serpapi_api_key=config.SERPAPI_KEY)
    search_tool = Tool(
        name="web_search",
        func=search.run,
        description=(
            "网络搜索工具，用于查找最新信息。"
            "当用户询问实时信息、新闻、最新数据时使用。"
        )
    )
    return search_tool


def _create_duckduckgo_tool() -> Tool:
    """
    创建 DuckDuckGo 搜索工具（免费）
    
    Returns:
        DuckDuckGo 搜索工具
    """
    search = DuckDuckGoSearchRun()
    search.name = "web_search"
    search.description = (
        "网络搜索工具，用于查找最新信息。"
        "当用户询问实时信息、新闻、最新数据时使用。"
        "输入应该是搜索查询关键词。"
    )
    return search

