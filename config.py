"""
配置管理模块 - 统一的配置管理系统
从 config.json 加载配置
优先级：config.json > 默认值
"""
import json
from pathlib import Path
from typing import Any
from logger import logger


class Config:
    """应用配置类 - 统一配置管理"""
    
    def __init__(self):
        """初始化配置，按优先级加载"""
        self._config_data = {}
        self._config_source = 'unknown'
        self._load_config()
    
    def _load_config(self):
        """
        加载配置：
        1. config.json (优先)
        2. 默认值
        """
        project_root = Path(__file__).parent
        
        # 尝试加载 config.json
        config_json_path = project_root / 'config.json'
        if config_json_path.exists():
            try:
                with open(config_json_path, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
                self._config_source = 'config.json'
                return
            except Exception as e:
                # 加载失败，使用默认值
                pass
        
        # 使用默认值
        self._set_defaults()
        self._config_source = 'default'
    
    def _set_defaults(self):
        """设置默认配置"""
        self._config_data = {
            'openai': {
                'api_key': '',
                'model': 'gpt-4o-mini',
                'temperature': 0.7,
                'max_tokens': 2000
            },
            'search': {
                'engine': 'duckduckgo',
                'tavily_api_key': '',
                'serpapi_key': '',
                'max_results': 3
            },
            'steam': {
                'num_reviews': 10,
                'max_reviews': 100,
                'language': 'schinese',
                'filter': 'recent',
                'request_delay': 1.0  # 请求间隔（秒）
            },
            'agent': {
                'verbose': True,
                'max_iterations': 5,
                'handle_parsing_errors': True
            },
            'ppt': {
                'output_dir': './output',
                'default_slides': 5,
                'font_name': '微软雅黑',
                'title_font_size': 44,
                'content_font_size': 24,
                'primary_color': [0, 112, 192],  # RGB 主色调（蓝色）
                'accent_color': [255, 192, 0]    # RGB 强调色（金色）
            }
        }
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        使用点号路径获取配置值
        
        Args:
            path: 配置路径，如 'openai.api_key'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = path.split('.')
        value = self._config_data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    # OpenAI 配置
    @property
    def OPENAI_API_KEY(self) -> str:
        """OpenAI API Key"""
        return self.get('openai.api_key', '')
    
    @property
    def MODEL_NAME(self) -> str:
        """OpenAI 模型名称"""
        return self.get('openai.model', 'gpt-4o-mini')
    
    @property
    def TEMPERATURE(self) -> float:
        """模型温度参数"""
        return float(self.get('openai.temperature', 0.7))
    
    @property
    def MAX_TOKENS(self) -> int:
        """最大 token 数"""
        return int(self.get('openai.max_tokens', 2000))
    
    # 搜索配置
    @property
    def TAVILY_API_KEY(self) -> str:
        """Tavily API Key"""
        return self.get('search.tavily_api_key', '')
    
    @property
    def SERPAPI_KEY(self) -> str:
        """SerpAPI Key"""
        return self.get('search.serpapi_key', '')
    
    @property
    def MAX_SEARCH_RESULTS(self) -> int:
        """搜索结果最大数量"""
        return int(self.get('search.max_results', 3))
    
    @property
    def search_engine(self) -> str:
        """
        返回可用的搜索引擎
        auto: 自动选择（tavily > serpapi > duckduckgo）
        """
        engine = self.get('search.engine', 'auto')
        
        if engine == 'auto':
            # 自动选择
            if self.TAVILY_API_KEY:
                return 'tavily'
            elif self.SERPAPI_KEY:
                return 'serpapi'
            else:
                return 'duckduckgo'
        
        return engine
    
    # Steam 配置
    @property
    def STEAM_NUM_REVIEWS(self) -> int:
        """Steam 评论数量（用户未指定时使用）"""
        return int(self.get('steam.num_reviews', 10))
    
    @property
    def STEAM_MAX_REVIEWS(self) -> int:
        """Steam 最大评论数量限制"""
        return int(self.get('steam.max_reviews', 100))
    
    @property
    def STEAM_LANGUAGE(self) -> str:
        """Steam 评论语言"""
        return self.get('steam.language', 'schinese')
    
    @property
    def STEAM_FILTER(self) -> str:
        """Steam 评论筛选"""
        return self.get('steam.filter', 'recent')
    
    @property
    def STEAM_REQUEST_DELAY(self) -> float:
        """Steam API 请求间隔（秒）"""
        return float(self.get('steam.request_delay', 1.0))
    
    # Agent 配置
    @property
    def AGENT_VERBOSE(self) -> bool:
        """是否显示 Agent 执行过程"""
        return bool(self.get('agent.verbose', True))
    
    @property
    def AGENT_MAX_ITERATIONS(self) -> int:
        """Agent 最大迭代次数"""
        return int(self.get('agent.max_iterations', 5))
    
    @property
    def AGENT_HANDLE_PARSING_ERRORS(self) -> bool:
        """是否处理解析错误"""
        return bool(self.get('agent.handle_parsing_errors', True))
    
    # PPT 配置
    @property
    def PPT_OUTPUT_DIR(self) -> str:
        """PPT 输出目录"""
        return self.get('ppt.output_dir', './output')
    
    @property
    def PPT_DEFAULT_SLIDES(self) -> int:
        """PPT 默认页数"""
        return int(self.get('ppt.default_slides', 5))
    
    @property
    def PPT_FONT_NAME(self) -> str:
        """PPT 字体名称"""
        return self.get('ppt.font_name', '微软雅黑')
    
    @property
    def PPT_TITLE_FONT_SIZE(self) -> int:
        """PPT 标题字号"""
        return int(self.get('ppt.title_font_size', 44))
    
    @property
    def PPT_CONTENT_FONT_SIZE(self) -> int:
        """PPT 内容字号"""
        return int(self.get('ppt.content_font_size', 24))
    
    @property
    def PPT_PRIMARY_COLOR(self) -> list:
        """PPT 主色调 RGB"""
        return self.get('ppt.primary_color', [0, 112, 192])
    
    @property
    def PPT_ACCENT_COLOR(self) -> list:
        """PPT 强调色 RGB"""
        return self.get('ppt.accent_color', [255, 192, 0])
    
    def get_config_source(self) -> str:
        """返回配置来源"""
        return self._config_source
    
    def print_config_info(self):
        """打印配置信息（安全的方式，处理编码问题）"""
        try:
            source_map = {
                'config.json': 'config.json',
                'default': 'default'
            }
            source_text = source_map.get(self._config_source, self._config_source)
            logger.log(f"[OK] Config loaded from: {source_text}")
        except:
            # 如果有编码问题，使用纯 ASCII
            logger.log(f"[OK] Config loaded from: {self._config_source}")
    
    def validate(self) -> tuple[bool, str]:
        """
        验证配置是否完整
        
        Returns:
            (是否有效, 错误信息)
        """
        if not self.OPENAI_API_KEY:
            return False, "[ERROR] 未找到 OPENAI_API_KEY，请在配置文件中设置"
        
        if not any([self.TAVILY_API_KEY, self.SERPAPI_KEY]):
            # 注意：这里返回字符串，由调用者决定如何输出
            return True, "[WARN] 未配置搜索API，将使用免费的 DuckDuckGo"
        
        return True, "[OK] 配置验证通过"
    
    def to_dict(self) -> dict:
        """导出配置为字典"""
        return self._config_data.copy()
    
    def save_to_file(self, filepath: str = 'config.json'):
        """
        保存配置到 JSON 文件
        
        Args:
            filepath: 文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._config_data, f, indent=2, ensure_ascii=False)
        logger.log(f"[OK] 配置已保存到: {filepath}")


# 全局配置实例
config = Config()

