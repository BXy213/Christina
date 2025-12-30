"""
日志管理模块

提供统一的日志输出接口，同时写入控制台和文件
支持跨平台自动适配（Windows/Linux/Mac）
"""
import sys
import logging
import platform
from pathlib import Path
from datetime import datetime


class LoggerMaster:
    """ 日志管理器（单例模式）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, log_file: str = "app.log"):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_file: str = "app.log"):
        """
        初始化日志管理器
        
        Args:
            log_file: 日志文件路径
        """
        # 只初始化一次
        if LoggerMaster._initialized:
            return
            
        self.log_file = Path(__file__).parent / log_file
        self._setup_logger()
        LoggerMaster._initialized = True
    
    def _setup_logger(self):
        """配置 logger"""
        # 创建 logger
        self.logger = logging.getLogger("LoggerMaster")
        self.logger.setLevel(logging.DEBUG)  # 设置为 DEBUG 以支持所有级别
        
        # 禁用传播到根 logger，避免重复输出
        self.logger.propagate = False
        
        # 清除所有现有的 handler（避免重复添加）
        self.logger.handlers.clear()
        
        # 创建格式化器
        formatter = logging.Formatter('%(message)s')
        
        # 文件 handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台 handler（根据操作系统自动适配）
        console_handler = self._create_console_handler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _create_console_handler(self) -> logging.StreamHandler:
        """
        创建控制台 handler，根据操作系统自动选择最佳方式
        
        Returns:
            配置好的 StreamHandler
        """
        system = platform.system()
        
        if system == 'Windows':
            # Windows: 使用 UTF-8 包装器处理编码问题
            # Windows 控制台默认使用 GBK/CP936，需要强制 UTF-8
            import io
            console_stream = io.TextIOWrapper(
                sys.stdout.buffer, 
                encoding='utf-8', 
                errors='replace',  # 无法编码的字符用替代字符显示
                line_buffering=True
            )
            return logging.StreamHandler(console_stream)
        else:
            # Linux/Mac: 直接使用标准输出（原生 UTF-8 支持）
            return logging.StreamHandler(sys.stdout)
    
    def debug(self, message: str):
        """
        输出调试日志（DEBUG 级别）
        
        Args:
            message: 调试消息
        """
        self.logger.debug(message)
    
    def log(self, message: str):
        """
        输出普通日志（INFO 级别）
        
        Args:
            message: 日志消息
        """
        self.logger.info(message)
    
    def warning(self, message: str):
        """
        输出警告日志（WARNING 级别）
        
        Args:
            message: 警告消息
        """
        self.logger.warning(message)
    
    def error(self, message: str):
        """
        输出错误日志（ERROR 级别）
        
        Args:
            message: 错误消息
        """
        self.logger.error(message)
    
    def critical(self, message: str):
        """
        输出严重错误日志（CRITICAL 级别）
        
        Args:
            message: 严重错误消息
        """
        self.logger.critical(message)
    
    def separator(self, char: str = "=", length: int = 50):
        """
        输出分隔线
        
        Args:
            char: 分隔符字符
            length: 分隔线长度
        """
        self.log(char * length)


# 全局日志实例（单例）
logger = LoggerMaster()