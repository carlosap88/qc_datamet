#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Clase base para las etapas del pipeline de QC_DataMet."""

from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
from typing import Any

from qc_datamet.pipeline.pipeline_state import PipelineState


class BaseStage(ABC):
    """Contrato común para todas las etapas del pipeline."""

    name: str = "base_stage"

    def __init__(
        self,
        state: PipelineState,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.state = state
        self.config = config or {}

    def run(self, data: Any = None) -> Any:
        """Ejecuta la etapa aplicando validaciones y trazabilidad."""

        started = perf_counter()
        self.state.start_stage(self.name)

        try:
            self.validate_inputs(data)
            result = self.execute(data)
            self.validate_outputs(result)

        except Exception as error:
            self.state.fail_stage(
                self.name,
                f"{self.name}: {type(error).__name__}: {error}",
            )
            raise

        self.state.complete_stage(self.name)
        self.state.set_statistic(
            f"{self.name}_duration_seconds",
            round(perf_counter() - started, 3),
        )

        return result

    def validate_inputs(self, data: Any) -> None:
        """Valida las entradas antes de ejecutar la etapa."""

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """Implementa la responsabilidad principal de la etapa."""

    def validate_outputs(self, result: Any) -> None:
        """Valida el resultado generado por la etapa."""

    def save_checkpoint(self, path: str) -> None:
        """Guarda el estado actual del pipeline."""

        checkpoint = self.state.save(path)
        self.state.set_checkpoint(self.name, checkpoint)