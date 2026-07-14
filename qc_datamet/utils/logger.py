#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Configuración centralizada de logging para QC_DataMet."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any


def get_logger(
    name: str,
    settings: dict[str, Any],
    project_root: Path,
) -> logging.Logger:
    """Crea o recupera un logger configurado desde settings.yaml."""

    logging_config = settings.get("logging", {})
    logger = logging.getLogger(name)

    if getattr(logger, "_qc_datamet_configured", False):
        return logger

    if not logging_config.get("enabled", True):
        logger.disabled = True
        logger._qc_datamet_configured = True  # type: ignore[attr-defined]
        return logger

    level_name = str(logging_config.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logger.disabled = False
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if logging_config.get("console", True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if logging_config.get("file", True):
        configured_directory = Path(
            logging_config.get("directory", "./logs")
        )
        log_directory = (
            configured_directory
            if configured_directory.is_absolute()
            else project_root / configured_directory
        ).resolve()
        log_directory.mkdir(parents=True, exist_ok=True)

        log_filename = str(
            logging_config.get("filename", "qc_datamet.log")
        )
        rotation = str(logging_config.get("rotation", "daily")).lower()
        retention_days = int(logging_config.get("retention_days", 30))

        if rotation == "daily":
            file_handler: logging.Handler = TimedRotatingFileHandler(
                log_directory / log_filename,
                when="midnight",
                interval=1,
                backupCount=max(retention_days, 0),
                encoding="utf-8",
                utc=True,
            )
        else:
            file_handler = logging.FileHandler(
                log_directory / log_filename,
                encoding="utf-8",
            )

        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger._qc_datamet_configured = True  # type: ignore[attr-defined]
    return logger
