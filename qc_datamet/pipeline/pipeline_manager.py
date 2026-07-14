#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Orquestador principal del pipeline de QC_DataMet."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from qc_datamet.pipeline.base_stage import BaseStage
from qc_datamet.pipeline.pipeline_state import PipelineState


class PipelineManager:
    """Carga, valida y ejecuta las etapas definidas en pipeline.yaml."""

    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    def __init__(
        self,
        config: dict[str, Any],
        state: PipelineState | None = None,
    ) -> None:
        self.config = config
        self.state = state or PipelineState()
        self.pipeline_config = self._get_pipeline_config()
        self.stages_config = self._get_stages_config()

    def run(self, data: Any = None) -> Any:
        """Ejecuta secuencialmente todas las etapas habilitadas."""

        if not self.pipeline_config.get("enabled", True):
            raise RuntimeError("El pipeline está deshabilitado en pipeline.yaml.")

        execution_mode = self.pipeline_config.get("execution_mode", "sequential")
        if execution_mode != "sequential":
            raise NotImplementedError(
                "QC_DataMet v0.1.0 solo admite execution_mode='sequential'."
            )

        self.state.start()
        result = data

        try:
            for stage_name, stage_config in self._enabled_stages():
                if self.pipeline_config.get("validate_stage_dependencies", True):
                    self._validate_dependencies(stage_name, stage_config)

                stage = self._create_stage(stage_name, stage_config)
                result = stage.run(result)

                if (
                    self.pipeline_config.get("save_checkpoints", True)
                    and stage_config.get("checkpoint", False)
                ):
                    self._save_checkpoint(stage_name)

        except Exception:
            self.state.finish(success=False)
            raise

        self.state.finish(success=True)
        return result

    def _get_pipeline_file(self) -> dict[str, Any]:
        """Obtiene el contenido cargado de pipeline.yaml."""

        pipeline_file = self.config.get("pipeline.yaml", self.config)
        if not isinstance(pipeline_file, dict):
            raise ValueError("La configuración de pipeline.yaml no es válida.")
        return pipeline_file

    def _get_pipeline_config(self) -> dict[str, Any]:
        """Obtiene la configuración general del pipeline."""

        pipeline_config = self._get_pipeline_file().get("pipeline", {})
        if not isinstance(pipeline_config, dict):
            raise ValueError("pipeline.yaml debe contener una sección 'pipeline'.")
        return pipeline_config

    def _get_stages_config(self) -> dict[str, dict[str, Any]]:
        """Obtiene las etapas desde la configuración cargada."""

        stages = self._get_pipeline_file().get("stages")
        if not isinstance(stages, dict) or not stages:
            raise ValueError(
                "pipeline.yaml debe contener una sección 'stages' válida."
            )
        return stages

    def _enabled_stages(self) -> list[tuple[str, dict[str, Any]]]:
        """Devuelve las etapas habilitadas ordenadas por ejecución."""

        enabled = [
            (name, stage)
            for name, stage in self.stages_config.items()
            if stage.get("enabled", False)
        ]

        return sorted(enabled, key=lambda item: item[1].get("order", 0))

    def _validate_dependencies(
        self,
        stage_name: str,
        stage_config: dict[str, Any],
    ) -> None:
        """Comprueba que las dependencias ya fueron completadas."""

        dependencies = stage_config.get("requires", [])
        if not isinstance(dependencies, list):
            raise ValueError(
                f"La etapa '{stage_name}' debe definir 'requires' como lista."
            )

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

        if not isinstance(stage_class, type) or not issubclass(
            stage_class,
            BaseStage,
        ):
            raise TypeError(
                f"La clase '{class_name}' debe heredar de BaseStage."
            )

        return stage_class(state=self.state, config=self.config)

    def _save_checkpoint(self, stage_name: str) -> None:
        """Guarda un checkpoint JSON del estado actual."""

        checkpoint_path = (
            self._get_checkpoint_directory()
            / f"{self.state.run_id}_{stage_name}.json"
        )
        saved_path = self.state.save(checkpoint_path)
        self.state.set_checkpoint(stage_name, saved_path)

    def _get_checkpoint_directory(self) -> Path:
        """Obtiene y resuelve el directorio de checkpoints."""

        checkpoint_config = self.pipeline_config.get("checkpoint", {})
        if not isinstance(checkpoint_config, dict):
            raise ValueError(
                "pipeline.checkpoint debe ser un diccionario válido."
            )

        configured_path = Path(
            checkpoint_config.get(
                "directory",
                "./data/staging/checkpoints",
            )
        )

        if not configured_path.is_absolute():
            configured_path = self.PROJECT_ROOT / configured_path

        return configured_path.resolve()
