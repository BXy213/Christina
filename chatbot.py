"""
AI 聊天助手核心模块
支持网络搜索、Steam 评论等多种工具
"""
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from config import config
from steam_tool import create_steam_reviews_tool
from search_tool import create_search_tool
from ppt_tool import create_ppt_tool
from logger import logger


class AIAssistant:
    """AI 助手，支持多种工具"""
    
    def __init__(self):
        """初始化 AI 助手"""
        # 打印配置信息
        config.print_config_info()
        
        # 验证配置
        is_valid, message = config.validate()
        if not is_valid:
            raise ValueError(message)
        
        # 根据消息类型选择合适的日志级别
        if "[WARN]" in message:
            logger.warning(message)
        else:
            logger.log(message)
        
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            api_key=config.OPENAI_API_KEY
        )
        
        # 初始化搜索工具
        self.tools = self._setup_tools()
        
        # 初始化对话历史（使用列表存储，不再使用已弃用的 Memory）
        self.chat_history = []
        
        # 初始化 Agent
        self.agent_executor = self._setup_agent()
        
    def _setup_tools(self) -> List:
        """
        设置可用工具
        
        Returns:
            工具列表
        """
        tools = []
        
        # 添加网络搜索工具
        try:
            search_tool = create_search_tool()
            tools.append(search_tool)
        except Exception as e:
            logger.error(f"[ERROR] Search tool init failed: {e}")
        
        # 添加 Steam 评论工具
        try:
            steam_tool = create_steam_reviews_tool()
            tools.append(steam_tool)
            logger.log("[OK] Steam reviews tool enabled")
        except Exception as e:
            logger.error(f"[ERROR] Steam tool init failed: {e}")
        
        # 添加 PPT 生成工具
        try:
            ppt_tool = create_ppt_tool(self.llm)
            tools.append(ppt_tool)
            logger.log("[OK] PPT generator tool enabled")
        except Exception as e:
            logger.error(f"[ERROR] PPT tool init failed: {e}")
        
        return tools
    
    def _setup_agent(self) -> AgentExecutor:
        """
        设置 Agent 执行器
        
        Returns:
            AgentExecutor 实例
        """
        # 定义 Agent 提示词（新版 API）
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，具有以下能力：
1. 回答各种问题
2. 通过网络搜索工具获取最新信息
3. 获取 Steam 游戏的评论和评价
4. 生成 PPT 演示文稿
5. 分析和总结搜索结果

重要指南：
- 当用户询问最新信息、实时数据、新闻时，主动使用网络搜索工具
- 当用户询问游戏评价、Steam评分、玩家反馈时，主动使用 Steam 评论工具
- 当用户需要制作PPT、演示文稿、幻灯片时，使用 PPT 生成工具
  * 如果用户提供了提纲，直接使用提纲生成
  * 如果用户只给了主题，先帮用户规划内容大纲，然后生成
  * 支持图片引用格式：[图片: 本地路径] 或 [图片: URL]
- 搜索后，用清晰、结构化的方式总结信息
- 如果搜索结果不够准确，尝试换个关键词再次搜索
- 对于一般性问题，可以直接回答，无需搜索
- 保持友好、专业的语气

当前日期：{current_date}
"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 创建 Agent（使用新的 create_tool_calling_agent）
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # 创建 Agent 执行器（使用配置）
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=config.AGENT_VERBOSE,  # 从配置读取
            max_iterations=config.AGENT_MAX_ITERATIONS,  # 从配置读取
            handle_parsing_errors=config.AGENT_HANDLE_PARSING_ERRORS  # 从配置读取
        )
        
        return agent_executor
    
    def chat(self, user_input: str) -> str:
        """
        与用户对话
        
        Args:
            user_input: 用户输入
            
        Returns:
            机器人回复
        """
        from datetime import datetime
        
        try:
            # 调用 Agent（传入对话历史）
            response = self.agent_executor.invoke({
                "input": user_input,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "chat_history": self.chat_history
            })
            
            # 更新对话历史
            self.chat_history.append(HumanMessage(content=user_input))
            self.chat_history.append(AIMessage(content=response["output"]))
            
            return response["output"]
        except Exception as e:
            return f"抱歉，处理您的请求时出错了：{str(e)}"
    
    def reset_memory(self):
        """重置对话记忆"""
        self.chat_history = []
        logger.log("✨ 对话历史已清除")
