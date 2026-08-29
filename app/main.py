from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.services.runtime_logging import (
    build_access_message,
    flush_backend_success_if_needed,
    get_runtime_log_file,
    log_backend_success,
    should_throttle_backend_success,
    tail_runtime_log,
)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "FastAPI backend skeleton for the WHU campus electrical bike WebGIS project. "
        "Current phase focuses on backend framework, local file storage, and mock responses for algorithm endpoints.\n\n"
        "武汉大学校园电单车 WebGIS 系统后端基础框架。当前阶段重点为后端基础环境、本地文件存储，以及算法接口的占位返回。"
    ),
    openapi_tags=[
        {"name": "system", "description": "System and health endpoints / 系统与健康检查接口"},
        {"name": "campus", "description": "Campus spatial base data endpoints / 校园空间基础数据接口"},
        {"name": "demand", "description": "Demand heatmap endpoints / 停车需求与热力图接口"},
        {"name": "siting", "description": "Siting and evaluation endpoints / 智能选址与交互评估接口"},
        {"name": "dispatch", "description": "Dispatch and route planning endpoints / 动态调度与路径规划接口"},
        {"name": "analysis", "description": "Analysis and metrics endpoints / 分析与图表接口"},
        {"name": "process", "description": "Algorithm process visualization endpoints / 算法过程可视化接口"},
        {"name": "scheme", "description": "Scheme persistence endpoints / 方案存储管理接口"},
        {"name": "export", "description": "Scheme export endpoints / 方案导出接口"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)

logger = logging.getLogger("app")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)

    client_host, client_port = request.client if request.client else ("unknown", 0)
    full_path = request.url.path
    if request.url.query:
        full_path = f"{full_path}?{request.url.query}"

    access_message = build_access_message(
        method=request.method,
        full_path=full_path,
        http_version=request.scope.get("http_version", "1.1"),
        status_code=response.status_code,
        client_host=client_host,
        client_port=client_port,
    )

    if should_throttle_backend_success(request.url.path, response.status_code):
        log_backend_success(logger, access_message)
    else:
        if request.url.path in {"/backend", "/backend/", "/backend/logs"} and response.status_code != 200:
            flush_backend_success_if_needed(logger, reason=f"{request.url.path} returned {response.status_code}")
        logger.info(access_message)

    return response


@app.get("/", summary="Root / 根路径", tags=["system"])
def read_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
        "storage_backend": settings.storage_backend,
    }


@app.get("/health", summary="Health Check / 健康检查", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "storage_backend": settings.storage_backend,
    }


@app.get("/backend", response_class=HTMLResponse, include_in_schema=False)
@app.get("/backend/", response_class=HTMLResponse, include_in_schema=False)
def backend_console_page() -> HTMLResponse:
    html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Backend Console</title>
  <style>
    body { margin: 0; font-family: Consolas, 'Courier New', monospace; background: #10151c; color: #d7e0ea; }
    header { padding: 16px 20px; background: #182230; border-bottom: 1px solid #2a3749; }
    h1 { margin: 0 0 6px 0; font-size: 20px; }
    p { margin: 0; color: #9cb0c8; }
    .meta { padding: 10px 20px; border-bottom: 1px solid #2a3749; color: #8da2bb; }
    pre { margin: 0; padding: 20px; white-space: pre-wrap; word-break: break-word; min-height: calc(100vh - 110px); }
  </style>
</head>
<body>
  <header>
    <h1>Backend Console / 后端控制台</h1>
    <p>页面内容直接来自运行日志文件，因此应与本地控制台输出保持一致。</p>
  </header>
  <div class="meta" id="meta">Loading...</div>
  <pre id="log">Loading log output...</pre>
  <script>
    async function refreshLogs() {
      try {
        const response = await fetch('/backend/logs?lines=300', { cache: 'no-store' });
        const data = await response.json();
        document.getElementById('meta').textContent = `Log File: ${data.log_file || 'N/A'} | Updated: ${data.updated_at}`;
        document.getElementById('log').textContent = data.content;
        window.scrollTo(0, document.body.scrollHeight);
      } catch (error) {
        document.getElementById('log').textContent = String(error);
      }
    }
    refreshLogs();
    setInterval(refreshLogs, 1000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/backend/logs", include_in_schema=False)
def backend_logs(lines: int = 200) -> JSONResponse:
    log_file = get_runtime_log_file()
    return JSONResponse(
        {
            "log_file": str(log_file) if log_file else None,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "content": tail_runtime_log(lines=lines),
        }
    )
