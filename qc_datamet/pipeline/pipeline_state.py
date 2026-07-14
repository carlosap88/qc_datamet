#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Estado serializable de una ejecución del pipeline de QC_DataMet."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    """Devuelve la fecha y hora UTC en formato ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineState:
    """Almacena el estado y la trazabilidad de una ejecución."""

    run_id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "pending"
    current_stage: str | None = None

    started_at: str | None = None
    finished_at: str | None = None

    completed_stages: list[str] = field(default_factory=list)
    failed_stages: list[str] = field(default_factory=list)

    discovered_files: list[str] = field(default_factory=list)
    checkpoint_paths: dict[str, str] = field(default_factory=dict)

    statistics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def start(self) -> None:
        """Marca el inicio de la ejecución."""
        self.status = "running"
        self.started_at = utc_now()
        self.finished_at = None

    def start_stage(self, stage_name: str) -> None:
        """Registra la etapa que comienza a ejecutarse."""
        self.current_stage = stage_name
        self.status = "running"

    def complete_stage(self, stage_name: str) -> None:
        """Marca una etapa como completada."""
        if stage_name not in self.completed_stages:
            self.completed_stages.append(stage_name)

        self.current_stage = None

    def fail_stage(self, stage_name: str, message: str) -> None:
        """Marca una etapa como fallida y registra el error."""
        if stage_name not in self.failed_stages:
            self.failed_stages.append(stage_name)

        self.add_error(message)
        self.current_stage = stage_name
        self.status = "failed"

    def add_warning(self, message: str) -> None:
        """Agrega una advertencia a la ejecución."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Agrega un error a la ejecución."""
        self.errors.append(message)

    def add_discovered_file(self, path: str | Path) -> None:
        """Registra un archivo encontrado por el pipeline."""
        file_path = str(Path(path))

        if file_path not in self.discovered_files:
            self.discovered_files.append(file_path)

    def set_statistic(self, name: str, value: Any) -> None:
        """Registra o actualiza una estadística."""
        self.statistics[name] = value

    def set_checkpoint(self, stage_name: str, path: str | Path) -> None:
        """Registra la ruta del checkpoint de una etapa."""
        self.checkpoint_paths[stage_name] = str(Path(path))

    def finish(self, success: bool = True) -> None:
        """Finaliza la ejecución del pipeline."""
        self.finished_at = utc_now()
        self.current_stage = None
        self.status = "completed" if success else "failed"

    def to_dict(self) -> dict[str, Any]:
        """Convierte el estado en un diccionario serializable."""
        return asdict(self)

    def save(self, path: str | Path) -> Path:
        """Guarda el estado en un archivo JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    @classmethod
    def load(cls, path: str | Path) -> "PipelineState":
        """Recupera el estado desde un archivo JSON."""
        input_path = Path(path)

        if not input_path.is_file():
            raise FileNotFoundError(
                f"No existe el archivo de estado: {input_path}"
            )

        data = json.loads(input_path.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            raise ValueError(
                f"El archivo de estado no contiene un objeto válido: {input_path}"
            )

        return cls(**data)