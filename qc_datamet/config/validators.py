#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Validadores básicos para la configuración de QC_DataMet."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from qc_datamet.config.exceptions import ConfigValidationError
from qc_datamet.config.loader import ConfigLoader


class ConfigValidator:
    """Valida la estructura básica y coherencia de los archivos YAML."""

    REQUIRED_ROOT_KEYS = {
        "settings.yaml": ("project", "system", "paths", "data"),
        "pipeline.yaml": ("pipeline", "stages"),
        "excel_schema.yaml": ("schema", "columns"),
        "data_dictionary.yaml": ("dictionary", "fields"),
        "canonical_schema.yaml": ("canonical_schema", "columns"),
        "stations.yaml": ("stations",),
        "variables.yaml": ("variables",),
        "units.yaml": ("units",),
        "qc_rules.yaml": ("qc_rules",),
        "reports.yaml": ("reports",),
    }

    def __init__(self, config: Mapping[str, Mapping[str, Any]]) -> None:
        self.config = config
        self.errors: list[str] = []

    def validate(self) -> None:
        """Ejecuta todas las validaciones y bloquea ante errores."""

        self.errors.clear()
        self._validate_required_files()
        self._validate_root_keys()
        self._validate_canonical_schema()
        self._validate_pipeline()

        if self.errors:
            details = "\n".join(f"- {error}" for error in self.errors)
            raise ConfigValidationError(
                f"Configuración inválida ({len(self.errors)} error(es)):\n{details}"
            )

    def _validate_required_files(self) -> None:
        """Comprueba que todos los archivos obligatorios estén cargados."""

        for filename in ConfigLoader.REQUIRED_FILES:
            if filename not in self.config:
                self.errors.append(f"Falta el archivo obligatorio: {filename}")

    def _validate_root_keys(self) -> None:
        """Comprueba las claves principales reales de cada archivo YAML."""

        for filename, required_keys in self.REQUIRED_ROOT_KEYS.items():
            data = self.config.get(filename)
            if data is None:
                continue

            for root_key in required_keys:
                if root_key not in data:
                    self.errors.append(
                        f"{filename}: falta la clave raíz obligatoria '{root_key}'"
                    )

    def _validate_canonical_schema(self) -> None:
        """Valida nombres y posiciones del esquema del dataset final."""

        data = self.config.get("canonical_schema.yaml", {})
        columns = data.get("columns", [])

        if not isinstance(columns, list) or not columns:
            self.errors.append(
                "canonical_schema.yaml: 'columns' debe ser una lista no vacía"
            )
            return

        positions: list[int] = []
        names: list[str] = []

        for index, column in enumerate(columns, start=1):
            if not isinstance(column, Mapping):
                self.errors.append(
                    f"canonical_schema.yaml: columna {index} no es un diccionario"
                )
                continue

            position = column.get("position")
            name = column.get("name")

            if not isinstance(position, int):
                self.errors.append(
                    f"canonical_schema.yaml: columna {index} sin posición válida"
                )
            else:
                positions.append(position)

            if not isinstance(name, str) or not name.strip():
                self.errors.append(
                    f"canonical_schema.yaml: columna {index} sin nombre válido"
                )
            else:
                names.append(name)

        self._check_duplicates(positions, "posiciones", "canonical_schema.yaml")
        self._check_duplicates(names, "nombres de columna", "canonical_schema.yaml")

        if positions and sorted(positions) != list(range(1, len(positions) + 1)):
            self.errors.append(
                "canonical_schema.yaml: las posiciones deben ser consecutivas desde 1"
            )

    def _validate_pipeline(self) -> None:
        """Valida órdenes y dependencias declaradas en el pipeline."""

        data = self.config.get("pipeline.yaml", {})
        stages = data.get("stages", {})

        if not isinstance(stages, Mapping) or not stages:
            self.errors.append("pipeline.yaml: 'stages' debe ser un diccionario no vacío")
            return

        orders: list[int] = []
        stage_names = set(stages)

        for stage_name, stage in stages.items():
            if not isinstance(stage, Mapping):
                self.errors.append(
                    f"pipeline.yaml: la etapa '{stage_name}' no es un diccionario"
                )
                continue

            order = stage.get("order")
            if not isinstance(order, int):
                self.errors.append(
                    f"pipeline.yaml: la etapa '{stage_name}' no tiene orden válido"
                )
            else:
                orders.append(order)

            requires = stage.get("requires", [])
            if not isinstance(requires, list):
                self.errors.append(
                    f"pipeline.yaml: 'requires' de '{stage_name}' debe ser una lista"
                )
                continue

            for dependency in requires:
                if dependency not in stage_names:
                    self.errors.append(
                        f"pipeline.yaml: '{stage_name}' depende de una etapa inexistente: "
                        f"'{dependency}'"
                    )

        self._check_duplicates(orders, "órdenes de etapa", "pipeline.yaml")

    def _check_duplicates(
        self,
        values: list[Any],
        label: str,
        filename: str,
    ) -> None:
        """Registra valores duplicados dentro de una colección."""

        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            self.errors.append(
                f"{filename}: {label} duplicados: {', '.join(map(str, duplicates))}"
            )


def validate_project_config(config_dir: str = "config") -> None:
    """Carga y valida toda la configuración del proyecto."""

    config = ConfigLoader(config_dir).load_all()
    ConfigValidator(config).validate()
