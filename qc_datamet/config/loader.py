#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Carga centralizada de archivos YAML de configuración."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from qc_datamet.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigYAMLError,
)


class ConfigLoader:
    """Carga los archivos YAML de configuración de QC_DataMet."""

    REQUIRED_FILES = (
        "settings.yaml",
        "pipeline.yaml",
        "excel_schema.yaml",
        "data_dictionary.yaml",
        "canonical_schema.yaml",
        "stations.yaml",
        "variables.yaml",
        "units.yaml",
        "qc_rules.yaml",
        "reports.yaml",
    )

    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    def __init__(self, config_dir: str | Path | None = None) -> None:
        self.config_dir = (
            Path(config_dir).resolve()
            if config_dir is not None
            else self.PROJECT_ROOT / "config"
        )

    def load(self, filename: str) -> dict[str, Any]:
        """Carga un archivo YAML y devuelve su contenido."""

        path = self.config_dir / filename

        if not path.is_file():
            raise ConfigFileNotFoundError(
                f"No existe el archivo de configuración: {path}"
            )

        try:
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file)

        except (OSError, UnicodeError) as error:
            raise ConfigYAMLError(
                f"No se pudo leer el archivo YAML {path}: {error}"
            ) from error

        except yaml.YAMLError as error:
            raise ConfigYAMLError(
                f"Error de sintaxis YAML en {path}: {error}"
            ) from error

        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ConfigYAMLError(
                f"La raíz del archivo debe ser un diccionario: {path}"
            )

        return data

    def load_all(self) -> dict[str, dict[str, Any]]:
        """Carga todos los archivos YAML obligatorios."""

        return {
            filename: self.load(filename)
            for filename in self.REQUIRED_FILES
        }