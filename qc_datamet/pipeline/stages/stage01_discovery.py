#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Etapa 01: descubrimiento de archivos de entrada."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qc_datamet.pipeline.base_stage import BaseStage


class Stage01Discovery(BaseStage):
    """Busca archivos de entrada configurados para el pipeline."""

    name = "stage01_discovery"

    def validate_inputs(self, data: Any) -> None:
        """Stage01 no requiere datos previos."""
        if data is not None:
            raise ValueError("Stage01Discovery no requiere datos de entrada.")

    def execute(self, data: Any = None) -> list[str]:
        """Busca archivos Excel dentro del directorio configurado."""

        settings = self.config.get("settings.yaml", {})
        raw_config = settings.get("data", {}).get("raw", {})
        excel_dir = Path(raw_config.get("excel", "./data/raw/excel"))

        if not excel_dir.exists():
            self.state.add_warning(
                f"El directorio de entrada no existe: {excel_dir}"
            )
            return []

        files = sorted(
            path
            for path in excel_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".xlsx", ".xls", ".xlsm"}
        )

        for path in files:
            self.state.add_discovered_file(path)

        self.state.set_statistic("files_found", len(files))

        return [str(path) for path in files]

    def validate_outputs(self, result: Any) -> None:
        """Valida que el resultado sea una lista de rutas."""
        if not isinstance(result, list):
            raise TypeError("Stage01Discovery debe devolver una lista.")

        if not all(isinstance(path, str) for path in result):
            raise TypeError("Todas las rutas encontradas deben ser texto.")