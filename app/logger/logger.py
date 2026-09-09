import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from app.context.request_id_var import request_id_var

# 移除loguru的默认配置
logger.remove()


# 日志中注入请求id
def _inject_request_id(record) -> None:
    # 每条日志渲染前，都用当前上下文中的 request_id 覆盖兜底值，
    # 实现跨模块的全局自动关联，无需手动 logger.bind()
    record["extra"]["request_id"] = request_id_var.get()


# patch 返回带注入逻辑的新 logger，且与原 logger 共享同一套 handlers
logger = logger.patch(_inject_request_id)

# 先加载 .env，保证日志开关配置（LOG_DIAGNOSE）可用
load_dotenv(Path(__file__).parents[2] / ".env")

# 是否启用日志诊断信息；诊断会打印异常时的局部变量值，仅建议本地调试开启
LOG_DIAGNOSE = os.getenv("LOG_DIAGNOSE", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)

# 日志目录固定为项目根目录下 logs/，避免依赖进程工作目录
LOG_DIR = Path(__file__).parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 定义日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<yellow>{extra[request_id]}</yellow> | "  # 用于追踪请求ID
    "<level>{message}</level>"
)

#  配置默认的 extra 字段，防止 KeyError
logger.configure(extra={"request_id": "N/A"})

# 日志文件配置
logger.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",  # 按天生成日志文件
    level="INFO",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    compression="zip",  # 压缩旧日志
    enqueue=True,  # 【重要】异步写入，避免阻塞主线程
    backtrace=True,
    format=LOG_FORMAT,
)

# 控制台日志配置
logger.add(
    sys.stdout,
    level="DEBUG",
    format=LOG_FORMAT,
    colorize=True,
    backtrace=True,  # 记录完整的堆栈信息，便于调试
    diagnose=LOG_DIAGNOSE,  # 仅在 LOG_DIAGNOSE=true 时显示异常时的变量值，避免泄露敏感信息
)


# 捕获标准库 logging 的日志
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取对应的 Loguru 级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 寻找调用者，跳过这个拦截器本身
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# 将 InterceptHandler 添加到 root logger
logging.root.handlers = [InterceptHandler()]
logging.root.setLevel(logging.INFO)

# 禁止第三方库的日志向 root logger 传播，避免重复
for name in logging.root.manager.loggerDict.keys():
    logging.getLogger(name).handlers = []
    logging.getLogger(name).propagate = False
