# main.py
from __future__ import annotations

import uvicorn

from app import create_app
from settings import get_settings

app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.app.server.host,
        port=settings.app.server.port,
        workers=1 if settings.debug else settings.app.server.workers,
        reload=settings.app.server.reload,
        proxy_headers=settings.app.server.proxy_headers,
        forwarded_allow_ips=settings.app.server.forwarded_allow_ips,
        root_path=settings.app.server.root_path,
        log_config=None,
    )


if __name__ == "__main__":
    run()