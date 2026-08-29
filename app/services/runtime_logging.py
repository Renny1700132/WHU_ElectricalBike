from __future__ import annotations

import logging
import os
import time
from collections import deque
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from uvicorn.config import LOGGING_CONFIG

from app.core.config import settings

_CURRENT_LOG_FILE: Path | None = None
_BACKEND_SUCCESS_WINDOW_SECONDS = 60.0
_BACKEND_LAST_EMIT_TS: float | None = None
_BACKEND_PENDING_SUCCESS_COUNT = 0


def create_runtime_log_file() -> Path:
    """创建本次运行对应的日志文件。

    返回值：
    - Path：当前运行日志文件的绝对路径。

    说明：
    - 每次启动服务时都创建一个新的 `.log` 文件。
    - 文件位于项目根目录 `log/` 下。
    """
    global _CURRENT_LOG_FILE
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = settings.log_dir / f'backend_{timestamp}.log'
    log_file.touch(exist_ok=True)
    _CURRENT_LOG_FILE = log_file
    os.environ['APP_RUNTIME_LOG_FILE'] = str(log_file)
    return log_file


def get_runtime_log_file() -> Path | None:
    """获取当前运行日志文件路径。"""
    global _CURRENT_LOG_FILE
    if _CURRENT_LOG_FILE and _CURRENT_LOG_FILE.exists():
        return _CURRENT_LOG_FILE
    env_path = os.environ.get('APP_RUNTIME_LOG_FILE')
    if env_path:
        path = Path(env_path)
        if path.exists():
            _CURRENT_LOG_FILE = path
            return path
    if settings.log_dir.exists():
        files = sorted(settings.log_dir.glob('backend_*.log'))
        if files:
            _CURRENT_LOG_FILE = files[-1]
            return _CURRENT_LOG_FILE
    return None


def build_uvicorn_log_config(log_file: Path) -> dict[str, Any]:
    """构建 Uvicorn 日志配置。

    设计目标：
    - 控制台输出与文件输出使用同一套格式。
    - 关闭 Uvicorn 默认 access log，统一改由应用层中间件记录访问日志。
    - 这样 `/backend` 页面读取的日志文件内容可以与控制台看到的内容保持一致。
    """
    config = deepcopy(LOGGING_CONFIG)
    config['formatters']['default']['fmt'] = '%(asctime)s | %(levelprefix)s | %(message)s'
    config['handlers']['file_default'] = {
        'class': 'logging.FileHandler',
        'formatter': 'default',
        'filename': str(log_file),
        'encoding': 'utf-8',
    }
    config['loggers']['uvicorn']['handlers'] = ['default', 'file_default']
    config['loggers']['uvicorn.error']['handlers'] = ['default', 'file_default']
    config['loggers']['uvicorn.access']['handlers'] = []
    config['loggers']['uvicorn.access']['propagate'] = False
    config['loggers']['app'] = {
        'handlers': ['default', 'file_default'],
        'level': 'INFO',
        'propagate': False,
    }
    return config


def tail_runtime_log(lines: int = 200) -> str:
    """读取当前运行日志文件的最后若干行。

    参数：
    - lines: 需要返回的日志行数。

    返回值：
    - str：拼接后的日志文本。
    """
    path = get_runtime_log_file()
    if path is None or not path.exists():
        return 'No runtime log file found yet. / 尚未发现运行日志文件。'
    with path.open('r', encoding='utf-8', errors='replace') as file:
        return ''.join(deque(file, maxlen=lines))


def build_access_message(method: str, full_path: str, http_version: str, status_code: int, client_host: str, client_port: int) -> str:
    """按统一格式拼接访问日志文本。

    返回示例：
    `127.0.0.1:12708 - "GET /backend/logs?lines=300 HTTP/1.1" 200 OK`
    """
    return f'{client_host}:{client_port} - "{method} {full_path} HTTP/{http_version}" {status_code} {http_status_phrase(status_code)}'


def http_status_phrase(status_code: int) -> str:
    """将状态码映射为常见短语。"""
    phrases = {
        200: 'OK',
        201: 'Created',
        204: 'No Content',
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
        422: 'Unprocessable Entity',
        500: 'Internal Server Error',
    }
    return phrases.get(status_code, '')


def should_throttle_backend_success(path: str, status_code: int) -> bool:
    """判断是否应对 `/backend` 相关 200 成功请求进行聚合输出。"""
    return path in {'/backend', '/backend/', '/backend/logs'} and status_code == 200


def log_backend_success(logger: logging.Logger, access_message: str) -> None:
    """对 `/backend` 与 `/backend/logs` 的 200 成功日志做一分钟聚合。

    规则：
    - 第一条成功请求立即输出。
    - 后续 60 秒内的成功请求不逐条输出，只累计数量。
    - 满 60 秒后下一条成功请求到来时，再输出一条摘要日志。
    - 摘要日志中标明本周期省略了多少条 200 成功日志。
    """
    global _BACKEND_LAST_EMIT_TS, _BACKEND_PENDING_SUCCESS_COUNT

    now = time.time()
    _BACKEND_PENDING_SUCCESS_COUNT += 1

    if _BACKEND_LAST_EMIT_TS is None:
        omitted_count = _BACKEND_PENDING_SUCCESS_COUNT - 1
        suffix = f' | 已省略 {omitted_count} 条 /backend 200 日志' if omitted_count > 0 else ''
        logger.info('%s%s', access_message, suffix)
        _BACKEND_LAST_EMIT_TS = now
        _BACKEND_PENDING_SUCCESS_COUNT = 0
        return

    if now - _BACKEND_LAST_EMIT_TS >= _BACKEND_SUCCESS_WINDOW_SECONDS:
        omitted_count = _BACKEND_PENDING_SUCCESS_COUNT - 1
        suffix = f' | 已省略 {omitted_count} 条 /backend 200 日志' if omitted_count > 0 else ''
        logger.info('%s%s', access_message, suffix)
        _BACKEND_LAST_EMIT_TS = now
        _BACKEND_PENDING_SUCCESS_COUNT = 0


def flush_backend_success_if_needed(logger: logging.Logger, reason: str | None = None) -> None:
    """在必要时补打一条聚合摘要。

    使用场景：
    - 当 `/backend` 或 `/backend/logs` 发生非 200 状态码时，先把之前累计的成功请求摘要补出来。
    - 避免成功日志统计被异常日志打断而丢失。
    """
    global _BACKEND_PENDING_SUCCESS_COUNT, _BACKEND_LAST_EMIT_TS

    if _BACKEND_PENDING_SUCCESS_COUNT <= 0:
        return

    omitted_count = _BACKEND_PENDING_SUCCESS_COUNT
    message = f'backend 聚合日志补发 | 已省略 {omitted_count} 条 /backend 200 日志'
    if reason:
        message += f' | 原因: {reason}'
    logger.info(message)
    _BACKEND_PENDING_SUCCESS_COUNT = 0
    _BACKEND_LAST_EMIT_TS = time.time()
