#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 01: preparación, descubrimiento e inventario de archivos."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qc_datamet.pipeline.base_stage import BaseStage
from qc_datamet.utils.logger import get_logger


class Stage01Discovery(BaseStage):
    """Prepara directorios y descubre los archivos de entrada configurados."""

    name = "stage01_discovery"

    # qc_datamet/pipeline/stages/stage01_discovery.py
    # parents[3] corresponde a la raíz del repositorio.
    PROJECT_ROOT = Path(__file__).resolve().parents[3]

    def validate_inputs(self, data: Any) -> None:
        """Stage01 no recibe resultados de etapas anteriores."""

        if data is not None:
            raise ValueError(
                "Stage01Discovery no admite datos de entrada."
            )

    def execute(self, data: Any = None) -> list[dict[str, Any]]:
        """Prepara directorios y genera el inventario de archivos."""

        settings = self.config.get("settings.yaml", {})
        reports = self.config.get("reports.yaml", {}).get("reports", {})

        logger = get_logger(
            name=self.name,
            settings=settings,
            project_root=self.PROJECT_ROOT,
        )

        logger.info(
            "Inicio de Stage01Discovery | run_id=%s",
            self.state.run_id,
        )

        self._create_project_directories(settings, logger)

        inventory: list[dict[str, Any]] = []

        data_config = settings.get("data", {})
        raw_config = data_config.get("raw", {})
        input_config = settings.get("input", {})

        for source_type, source_settings in input_config.items():
            if not isinstance(source_settings, dict):
                continue

            if not source_settings.get("enabled", False):
                logger.info(
                    "Fuente deshabilitada: %s",
                    source_type,
                )
                continue

            configured_directory = raw_config.get(source_type)

            if not configured_directory:
                message = (
                    f"No existe una ruta raw configurada para "
                    f"'{source_type}'."
                )
                self.state.add_warning(message)
                logger.warning(message)
                continue

            source_directory = self._resolve_path(
                configured_directory
            )

            extensions = self._get_extensions(source_settings)

            if not extensions:
                message = (
                    f"No existen extensiones configuradas para "
                    f"'{source_type}'."
                )
                self.state.add_warning(message)
                logger.warning(message)
                continue

            recursive = bool(
                source_settings.get("recursive", True)
            )

            discovered_files = self._discover_files(
                directory=source_directory,
                extensions=extensions,
                recursive=recursive,
                logger=logger,
            )

            logger.info(
                "Fuente=%s | directorio=%s | archivos=%d",
                source_type,
                source_directory,
                len(discovered_files),
            )

            for file_path in discovered_files:
                item = self._build_inventory_item(
                    file_path=file_path,
                    source_type=source_type,
                )

                inventory.append(item)
                self.state.add_discovered_file(file_path)

        inventory, duplicate_count = self._remove_duplicates(
            inventory=inventory,
            logger=logger,
        )

        inventory.sort(
            key=lambda item: (
                item["source_type"],
                item["relative_path"].lower(),
            )
        )

        statistics = self._register_statistics(
            inventory=inventory,
            duplicate_count=duplicate_count,
        )

        inventory_path = self._save_inventory(
            inventory=inventory,
            settings=settings,
        )

        report_path = self._save_report(
            inventory=inventory,
            statistics=statistics,
            reports_config=reports,
        )

        if inventory_path is not None:
            self.state.set_statistic(
                "stage01_inventory_path",
                str(inventory_path),
            )
            self.state.set_checkpoint(
                f"{self.name}_inventory",
                inventory_path,
            )

        if report_path is not None:
            self.state.set_statistic(
                "stage01_report_path",
                str(report_path),
            )

        logger.info(
            "Fin de Stage01Discovery | archivos=%d | "
            "duplicados=%d | advertencias=%d | errores=%d",
            len(inventory),
            duplicate_count,
            len(self.state.warnings),
            len(self.state.errors),
        )

        return inventory

    def validate_outputs(self, result: Any) -> None:
        """Valida la estructura del inventario generado."""

        if not isinstance(result, list):
            raise TypeError(
                "Stage01Discovery debe devolver una lista."
            )

        required_fields = {
            "source_type",
            "path",
            "relative_path",
            "filename",
            "stem",
            "extension",
            "size_bytes",
            "modified_utc",
            "sha256",
        }

        for position, item in enumerate(result, start=1):
            if not isinstance(item, dict):
                raise TypeError(
                    f"El elemento {position} no es un diccionario."
                )

            missing_fields = required_fields - set(item)

            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise ValueError(
                    f"El elemento {position} no contiene: {missing}"
                )

    # =========================================================================
    # DIRECTORIOS
    # =========================================================================

    def _create_project_directories(
        self,
        settings: dict[str, Any],
        logger: logging.Logger,
    ) -> None:
        """Crea todos los directorios configurados para el proyecto."""

        execution = settings.get("execution", {})

        if not execution.get(
            "create_missing_directories",
            True,
        ):
            return

        configured_paths = self._collect_directory_paths(settings)

        created_count = 0

        for configured_path in configured_paths:
            directory = self._resolve_path(configured_path)

            if directory.exists():
                continue

            directory.mkdir(parents=True, exist_ok=True)
            created_count += 1

            logger.info(
                "Directorio creado: %s",
                directory,
            )

        self.state.set_statistic(
            "stage01_directories_created",
            created_count,
        )

    def _collect_directory_paths(
        self,
        settings: dict[str, Any],
    ) -> list[str]:
        """Obtiene las rutas que Stage01 debe garantizar."""

        paths: list[str] = []

        project_paths = settings.get("paths", {})

        for key in (
            "assets",
            "config",
            "data",
            "docs",
            "logs",
            "reports",
            "scripts",
            "tests",
        ):
            value = project_paths.get(key)

            if isinstance(value, str):
                paths.append(value)

        data_config = settings.get("data", {})

        paths.extend(
            self._extract_paths(data_config)
        )

        logging_directory = (
            settings.get("logging", {}).get("directory")
        )

        if isinstance(logging_directory, str):
            paths.append(logging_directory)

        # Elimina rutas repetidas conservando el orden.
        return list(dict.fromkeys(paths))

    def _extract_paths(self, value: Any) -> list[str]:
        """Extrae recursivamente todas las rutas de una estructura."""

        paths: list[str] = []

        if isinstance(value, str):
            paths.append(value)

        elif isinstance(value, dict):
            for nested_value in value.values():
                paths.extend(
                    self._extract_paths(nested_value)
                )

        return paths

    def _resolve_path(
        self,
        configured_path: str | Path,
    ) -> Path:
        """Resuelve una ruta respecto a la raíz del proyecto."""

        path = Path(configured_path)

        if not path.is_absolute():
            path = self.PROJECT_ROOT / path

        return path.resolve()

    # =========================================================================
    # DESCUBRIMIENTO
    # =========================================================================

    @staticmethod
    def _get_extensions(
        source_settings: dict[str, Any],
    ) -> set[str]:
        """Normaliza las extensiones configuradas."""

        extensions: set[str] = set()

        for extension in source_settings.get("extensions", []):
            normalized = str(extension).strip().lower()

            if not normalized:
                continue

            if not normalized.startswith("."):
                normalized = f".{normalized}"

            extensions.add(normalized)

        return extensions

    def _discover_files(
        self,
        directory: Path,
        extensions: set[str],
        recursive: bool,
        logger: logging.Logger,
    ) -> list[Path]:
        """Descubre archivos válidos sin abrir su contenido."""

        if not directory.is_dir():
            message = (
                f"El directorio de entrada no existe: {directory}"
            )
            self.state.add_warning(message)
            logger.warning(message)
            return []

        iterator = (
            directory.rglob("*")
            if recursive
            else directory.glob("*")
        )

        discovered: list[Path] = []

        for path in iterator:
            if not path.is_file():
                continue

            if self._is_ignored_file(path):
                logger.debug(
                    "Archivo temporal u oculto ignorado: %s",
                    path,
                )
                continue

            if path.suffix.lower() not in extensions:
                continue

            try:
                size_bytes = path.stat().st_size
            except OSError as error:
                message = (
                    f"No se pudo obtener metadata de {path}: {error}"
                )
                self.state.add_warning(message)
                logger.warning(message)
                continue

            if size_bytes == 0:
                message = f"Archivo vacío ignorado: {path}"
                self.state.add_warning(message)
                logger.warning(message)
                continue

            discovered.append(path.resolve())

        return sorted(
            discovered,
            key=lambda item: item.as_posix().lower(),
        )

    @staticmethod
    def _is_ignored_file(path: Path) -> bool:
        """Indica si un archivo es temporal, oculto o de sistema."""

        ignored_names = {
            "thumbs.db",
            "desktop.ini",
            ".ds_store",
        }

        if path.name.lower() in ignored_names:
            return True

        if path.name.startswith("~$"):
            return True

        if path.name.startswith("."):
            return True

        return any(
            part.startswith(".")
            for part in path.parts
            if part not in {".", ".."}
        )

    # =========================================================================
    # INVENTARIO
    # =========================================================================

    def _build_inventory_item(
        self,
        file_path: Path,
        source_type: str,
    ) -> dict[str, Any]:
        """Construye la metadata técnica del archivo."""

        stat = file_path.stat()

        try:
            relative_path = file_path.relative_to(
                self.PROJECT_ROOT
            )
        except ValueError:
            relative_path = file_path

        return {
            "source_type": source_type,
            "path": str(file_path),
            "relative_path": relative_path.as_posix(),
            "filename": file_path.name,
            "stem": file_path.stem,
            "extension": file_path.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(
                stat.st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "sha256": self._calculate_sha256(file_path),
        }

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calcula el hash SHA-256 por bloques."""

        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            for block in iter(
                lambda: file.read(1024 * 1024),
                b"",
            ):
                digest.update(block)

        return digest.hexdigest()

    def _remove_duplicates(
        self,
        inventory: list[dict[str, Any]],
        logger: logging.Logger,
    ) -> tuple[list[dict[str, Any]], int]:
        """Elimina archivos con contenido exactamente duplicado."""

        unique_items: list[dict[str, Any]] = []
        hashes: dict[str, str] = {}
        duplicate_count = 0

        for item in inventory:
            file_hash = item["sha256"]

            if file_hash in hashes:
                duplicate_count += 1

                message = (
                    "Archivo duplicado ignorado: "
                    f"{item['relative_path']} es idéntico a "
                    f"{hashes[file_hash]}"
                )

                self.state.add_warning(message)
                logger.warning(message)
                continue

            hashes[file_hash] = item["relative_path"]
            unique_items.append(item)

        return unique_items, duplicate_count

    # =========================================================================
    # ESTADÍSTICAS
    # =========================================================================

    def _register_statistics(
        self,
        inventory: list[dict[str, Any]],
        duplicate_count: int,
    ) -> dict[str, Any]:
        """Calcula y registra estadísticas de Stage01."""

        statistics = {
            "files_found": len(inventory),
            "total_size_bytes": sum(
                item["size_bytes"]
                for item in inventory
            ),
            "files_by_extension": dict(
                Counter(
                    item["extension"]
                    for item in inventory
                )
            ),
            "files_by_source_type": dict(
                Counter(
                    item["source_type"]
                    for item in inventory
                )
            ),
            "duplicates_ignored": duplicate_count,
        }

        for name, value in statistics.items():
            self.state.set_statistic(
                f"stage01_{name}",
                value,
            )

        return statistics

    # =========================================================================
    # SALIDAS
    # =========================================================================

    def _get_staging_path(
        self,
        settings: dict[str, Any],
        key: str,
        default: str,
    ) -> Path:
        """Obtiene una ruta de staging compatible con formatos antiguos."""

        staging = settings.get("data", {}).get("staging", {})

        if isinstance(staging, dict):
            configured_path = staging.get(key, default)

        elif isinstance(staging, str):
            configured_path = str(Path(staging) / key)

        else:
            configured_path = default

        return self._resolve_path(configured_path)

    def _save_inventory(
        self,
        inventory: list[dict[str, Any]],
        settings: dict[str, Any],
    ) -> Path | None:
        """Guarda el inventario JSON."""

        execution = settings.get("execution", {})

        if not execution.get(
            "save_intermediate_files",
            True,
        ):
            return None

        inventory_directory = self._get_staging_path(
            settings=settings,
            key="inventory",
            default="./data/staging/inventory",
        )

        inventory_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            inventory_directory
            / f"{self.state.run_id}_file_inventory.json"
        )

        output_path.write_text(
            json.dumps(
                inventory,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return output_path

    def _save_report(
        self,
        inventory: list[dict[str, Any]],
        statistics: dict[str, Any],
        reports_config: dict[str, Any],
    ) -> Path | None:
        """Genera el reporte técnico TXT de Stage01."""

        general = reports_config.get("general", {})

        if not general.get("enabled", True):
            return None

        if not general.get("generate_reports", True):
            return None

        configured_directory = (
            reports_config
            .get("directories", {})
            .get("import", "./reports/import")
        )

        report_directory = self._resolve_path(
            configured_directory
        )

        report_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        report_path = (
            report_directory
            / f"{self.state.run_id}_stage01_discovery_report.txt"
        )

        total_mb = (
            statistics["total_size_bytes"]
            / (1024 * 1024)
        )

        lines = [
            "=" * 78,
            "QC_DataMet v0.1.0 - REPORTE STAGE01 DISCOVERY",
            "=" * 78,
            f"Run ID                 : {self.state.run_id}",
            (
                "Fecha UTC              : "
                f"{datetime.now(timezone.utc).isoformat()}"
            ),
            (
                "Archivos encontrados   : "
                f"{statistics['files_found']}"
            ),
            f"Tamaño total           : {total_mb:.2f} MB",
            (
                "Duplicados ignorados   : "
                f"{statistics['duplicates_ignored']}"
            ),
            f"Advertencias           : {len(self.state.warnings)}",
            f"Errores                 : {len(self.state.errors)}",
            "",
            "ARCHIVOS POR TIPO DE FUENTE",
            "-" * 78,
        ]

        for source_type, count in sorted(
            statistics["files_by_source_type"].items()
        ):
            lines.append(
                f"{source_type:<20}: {count}"
            )

        lines.extend([
            "",
            "ARCHIVOS POR EXTENSIÓN",
            "-" * 78,
        ])

        for extension, count in sorted(
            statistics["files_by_extension"].items()
        ):
            lines.append(
                f"{extension:<20}: {count}"
            )

        lines.extend([
            "",
            "ARCHIVOS INVENTARIADOS",
            "-" * 78,
        ])

        for item in inventory:
            size_mb = item["size_bytes"] / (1024 * 1024)

            lines.extend([
                f"Archivo        : {item['relative_path']}",
                f"Tipo           : {item['source_type']}",
                f"Extensión      : {item['extension']}",
                f"Tamaño         : {size_mb:.2f} MB",
                f"Modificado UTC : {item['modified_utc']}",
                f"SHA-256        : {item['sha256']}",
                "-" * 78,
            ])

        if self.state.warnings:
            lines.extend([
                "",
                "ADVERTENCIAS",
                "-" * 78,
            ])
            lines.extend(
                f"- {warning}"
                for warning in self.state.warnings
            )

        if self.state.errors:
            lines.extend([
                "",
                "ERRORES",
                "-" * 78,
            ])
            lines.extend(
                f"- {error}"
                for error in self.state.errors
            )

        lines.extend([
            "",
            "=" * 78,
            "FIN DEL REPORTE",
            "=" * 78,
        ])

        report_path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        return report_path