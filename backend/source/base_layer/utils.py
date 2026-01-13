# 工具类模块 - 提供通用工具函数和日志配置
import logging
from datetime import datetime
from pathlib import Path


# 配置日志
def setup_logging():
    """
    配置全局日志记录器
    """
    # 确保日志目录存在
    log_dir = Path.cwd() / "logs"
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 创建应用日志文件处理器（主日志）- 指定UTF-8编码
    app_log_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    app_log_handler.setLevel(logging.INFO)
    app_formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    app_log_handler.setFormatter(app_formatter)
    root_logger.addHandler(app_log_handler)

    # 创建历史调用日志文件处理器 - 指定UTF-8编码
    # 使用日期时间戳命名以避免覆盖
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_log_file = log_dir / f"history_{timestamp}.log"
    history_handler = logging.FileHandler(history_log_file, encoding="utf-8")
    history_handler.setLevel(logging.INFO)
    history_formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(module)s - %(funcName)s - %(levelname)s - %(message)s"
    )
    history_handler.setFormatter(history_formatter)
    root_logger.addHandler(history_handler)

    # 设置特定库的日志级别，抑制不必要的详细日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("_client").setLevel(logging.WARNING)  # Suppress HTTP client logs

    # 记录日志初始化信息
    root_logger.info("日志系统初始化完成，历史调用日志已创建: " + str(history_log_file))


# 初始化日志设置
setup_logging()

# 创建默认日志记录器
logger = logging.getLogger(__name__)
logger.info("utils模块初始化完成")
