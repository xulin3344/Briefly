"""
统一日志配置模块
提供集中式的日志配置和管理
"""
import logging
import sys
from typing import Optional
from datetime import datetime


class LogFormatter(logging.Formatter):
    """
    自定义日志格式化器
    根据日志级别使用不同的颜色和格式
    """
    
    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"
    
    def __init__(self, use_color: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color
    
    def format(self, record: logging.LogRecord) -> str:
        # 添加颜色
        if self.use_color and record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )
        
        return super().format(record)


class LoggingConfig:
    """
    日志配置类
    支持不同环境的日志配置
    """
    
    _initialized: bool = False
    
    @classmethod
    def setup(
        cls,
        level: str = "INFO",
        log_format: Optional[str] = None,
        date_format: Optional[str] = None,
        use_color: bool = True,
        log_file: Optional[str] = None,
    ) -> None:
        """
        配置日志系统
        
        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: 自定义日志格式
            date_format: 自定义日期格式
            use_color: 是否使用彩色输出
            log_file: 日志文件路径（可选）
        """
        if cls._initialized:
            return
        
        # 默认格式
        if log_format is None:
            log_format = (
                "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
            )
        
        if date_format is None:
            date_format = "%Y-%m-%d %H:%M:%S"
        
        # 获取根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # 清除现有的处理器
        root_logger.handlers.clear()
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_formatter = LogFormatter(
            use_color=use_color,
            fmt=log_format,
            datefmt=date_format
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 如果指定了日志文件，添加文件处理器
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            # 文件不使用颜色
            file_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # 降低第三方库的日志级别
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        
        cls._initialized = True
    
    @classmethod
    def reset(cls) -> None:
        """
        重置日志配置（主要用于测试）
        """
        cls._initialized = False
        root_logger = logging.getLogger()
        root_logger.handlers.clear()


def setup_logging(debug: bool = False, log_file: Optional[str] = None) -> None:
    """
    便捷函数：设置日志配置
    
    Args:
        debug: 是否启用调试模式
        log_file: 日志文件路径（可选）
    """
    level = "DEBUG" if debug else "INFO"
    LoggingConfig.setup(level=level, log_file=log_file)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称（通常使用 __name__）
    
    Returns:
        配置好的日志器实例
    
    Example:
        >>> from app.core.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条日志")
    """
    return logging.getLogger(name)
