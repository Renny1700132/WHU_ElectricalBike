from __future__ import annotations

import uvicorn

from app.services.runtime_logging import build_uvicorn_log_config, create_runtime_log_file


if __name__ == "__main__":
    log_file = create_runtime_log_file()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=7860,
        reload=True,
        access_log=False,
        log_config=build_uvicorn_log_config(log_file),
    )
