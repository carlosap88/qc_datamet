#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Orquestador principal del pipeline de QC_DataMet."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from qc_datamet.pipeline.base_stage import BaseStage
from qc_datamet.pipeline.pipeline_state import PipelineState


class PipelineManager:
    """Carga, valida y ejecuta las etapas definidas en pipeline.yaml."""

    def __init__(
        self,
        config: dict[str, Any],
        state: PipelineState | None = None,
    ) -> None:
        self.config = config
        self.state = state or PipelineState()
        self.stages_config = self._get_stages_config()

    def run(self, data: Any = None) -> Any:
        """Ejecuta secuencialmente todas las etapas habilitadas."""

        self.state.start()
        result = data

        try:
            for stage_name, stage_config in self._enabled_stages():
                self._validate_dependencies(stage_name, stage_config)

                stage = self._create_stage(stage_name, stage_config)
                result = stage.run(result)

                if stage_config.get("checkpoint", False):
                    self._save_checkpoint(stage_name)

        except Exception:
            self.state.finish(success=False)
            raise

        self.state.finish(success=True)
        return result

    def _get_stages_config(self) -> dict[str, dict[str, Any]]:
        """Obtiene las etapas desde la configuración cargada."""

        pipeline_file = self.config.get("pipeline.yaml", self.config)
        stages = pipeline_file.get("stages")

        if not isinstance(stages, dict) or not stages:
            raise ValueError(
                "pipeline.yaml debe contener una sección 'stages' válida."
            )

        return stages

    def _enabled_stages(
        self,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Devuelve las etapas habilitadas ordenadas por ejecución."""

        enabled = [
            (name, stage)
            for name, stage in self.stages_config.items()
            if stage.get("enabled", False)
        ]

        return sorted(
            enabled,
            key=lambda item: item[1].get("order", 0),
        )

    def _validate_dependencies(
        self,
        stage_name: str,
        stage_config: dict[str, Any],
    ) -> None:
        """Comprueba que las dependencias ya fueron completadas."""

        dependencies = stage_config.get("requires", [])

        for dependency in dependencies:
            if dependency not in self.state.completed_stages:
                raise RuntimeError(
                    f"La etapa '{stage_name}' requiere que "
                    f"'{dependency}' esté completada."
                )

    def _create_stage(
        self,
        stage_name: str,
        stage_config: dict[str, Any],
    ) -> BaseStage:
        """Importa dinámicamente y construye una etapa."""

        module_name = stage_config.get("module")
        class_name = stage_config.get("class_name")

        if not module_name or not class_name:
            raise ValueError(
                f"La etapa '{stage_name}' debe definir "
                "'module' y 'class_name'."
            )

        try:
            module = import_module(module_name)
            stage_class = getattr(module, class_name)

        except (ImportError, AttributeError) as error:
            raise ImportError(
                f"No se pudo cargar la etapa '{stage_name}' "
                f"desde {module_name}.{class_name}"
            ) from error

        if not issubclass(stage_class, BaseStage):
            raise TypeError(
                f"La clase '{class_name}' debe heredar de BaseStage."
            )

        return stage_class(
            state=self.state,
            config=self.config,
        )

    def _save_checkpoint(self, stage_name: str) -> None:
        """Guarda un checkpoint JSON del estado actual."""

        checkpoint_dir = self._get_checkpoint_directory()
        checkpoint_path = (
            f"{checkpoint_dir}/"
            f"{self.state.run_id}_{stage_name}.json"
        )

        saved_path = self.state.save(checkpoint_path)
        self.state.set_checkpoint(stage_name, saved_path)

    def _get_checkpoint_directory(self) -> str:
        """Obtiene el directorio de checkpoints del pipeline."""

        pipeline_file = self.config.get("pipeline.yaml", self.config)
        pipeline_config = pipeline_file.get("pipeline", {})

        return pipeline_config.get(
            "checkpoint_directory",
            "./data/staging/checkpoints",
        )