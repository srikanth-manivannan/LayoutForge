import logging
import logging.handlers
from pathlib import Path


def configure_logging(logs_dir: Path) -> None:
    """Wires up the three log streams required by the spec:
    - application.log: API/app-level events (root + uvicorn loggers)
    - conversion.log: pipeline stage transitions (layoutforge.pipeline)
    - performance.log: per-stage durations (layoutforge.performance)
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    app_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "application.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    conversion_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "conversion.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    conversion_handler.setFormatter(formatter)
    pipeline_logger = logging.getLogger("layoutforge.pipeline")
    pipeline_logger.addHandler(conversion_handler)
    pipeline_logger.propagate = True  # also captured by application.log

    performance_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "performance.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    performance_handler.setFormatter(formatter)
    performance_logger = logging.getLogger("layoutforge.performance")
    performance_logger.addHandler(performance_handler)
    performance_logger.propagate = True
