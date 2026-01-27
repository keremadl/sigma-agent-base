import logging

import uvicorn

from app.core.config import settings


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Starting Sigma Agent Backend")
    logger.info(f"Server: http://{settings.host}:{settings.port}")
    logger.info(f"Memory: {settings.memory_dir}")

    uvicorn.run(
        "app.api:app",
        host=settings.host,
        port=settings.port,
        reload=False,  # Set to False in production
        log_level="info",
    )
