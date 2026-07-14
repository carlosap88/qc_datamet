#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 01: descubrimiento e inventario de archivos de entrada."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qc_datamet.pipeline.base_stage import BaseStage
from qc_datamet.utils import get_logger


class Stage01Discovery(BaseStage):
    """Descubre archivos de entrada sin abrir ni procesar su contenido."""

    name = "stage01_discovery"
    PROJECT_ROOT = Path(__file__).resolve().parents[3]

    def validate_inputs(self, data: Any) -> None:
        """Stage01 no requiere datos provenientes de una etapa anterior."""

        if data is not None:
            raise ValueError("Stage01Discovery no admite datos de entrada.")

    def execute(self, data: Any = None) -> list[dict[str, Any]]:
        """Descubre archivos, genera inventario, log y reporte técnico."""

        settings = self.config.get("settings.yaml", {})
        reports_config = self.config.get("reports.yaml", {}).get("reports", {})
        logger = get_logger(self.name, settings, self.PROJECT_ROOT)

        logger.info("Inicio de Stage01 Discovery | run_id=%s", self.state.run_id)

        data_config = settings.get("data", {})
        input_config = settings.get("input", {})
        execution_config = settings.get("execution", {})
        create_directories = execution_config.get(
            "create_missing_directories",
            True,
        )

        inventory: list[dict[str, Any]] = []
        duplicates_ignored = 0

        for source_type, source_settings in input_config.items():
            if not isinstance(source_settings, dict):
                continue
            if not source_settings.get("enabled", False):
                logger.info("Fuente deshabilitada: %s", source_type)
                continue

            raw_directory = data_config.get("raw", {}).get(source_type)
            if not raw_directory:
                message = f"No existe una ruta configurada para '{source_type}'."
                self.state.add_warning(message)
                logger.warning(message)
                continue

            source_directory = self._resolve_path(raw_directory)
            if not source_directory.exists():
                if create_directories:
                    source_directory.mkdir(parents=True, exist_ok=True)
                    message = f"Se creó el directorio de entrada: {source_directory}"
                    self.state.add_warning(message)
                    logger.warning(message)
                else:
                    message = f"El directorio no existe: {source_directory}"
                    self.state.add_warning(message)
                    logger.warning(message)
                    continue

            extensions = {
                str(extension).lower()
                for extension in source_settings.get("extensions", [])
            }
            if not extensions:
                message = (
                    f"No existen extensiones configuradas para '{source_type}'."
                )
                self.state.add_warning(message)
                logger.warning(message)
                continue

            recursive = source_settings.get("recursive", True)
            files = self._discover_files(
                directory=source_directory,
                extensions=extensions,
                recursive=recursive,
                logger=logger,
            )

            logger.info(
                "Fuente %s | directorio=%s | archivos=%d",
                source_type,
                source_directory,
                len(files),
            )

            for file_path in files:
                inventory.append(
                    self._build_inventory_item(file_path, source_type)
                )
                self.state.add_discovered_file(file_path)

        inventory, duplicates_ignored = self._remove_duplicate_content(
            inventory,
            logger,
        )
        inventory.sort(key=lambda item: item["relative_path"])

        statistics = self._register_statistics(
            inventory,
            duplicates_ignored,
        )
        inventory_path = self._save_inventory(inventory, settings)
        report_path = self._save_report(
            inventory=inventory,
            statistics=statistics,
            reports_config=reports_config,
        )

        if inventory_path is not None:
            self.state.set_statistic(
                "stage01_inventory_path",
                str(inventory_path),
            )
        if report_path is not None:
            self.state.set_statistic(
                "stage01_report_path",
                str(report_path),
            )

        logger.info(
            "Fin de Stage01 Discovery | archivos=%d | duplicados=%d | "
            "advertencias=%d | errores=%d",
            len(inventory),
            duplicates_ignored,
            len(self.state.warnings),
            len(self.state.errors),
        )

        return inventory

    def validate_outputs(self, result: Any) -> None:
        """Valida la estructura del inventario generado."""

        if not isinstance(result, list):
            raise TypeError("Stage01Discovery debe devolver una lista.")

        required_fields = {
            "source_type",
            "path",
            "relative_path",
            "filename",
            "extension",
            "size_bytes",
            "modified_utc",
            "sha256",
        }

        for index, item in enumerate(result, start=1):
            if not isinstance(item, dict):
                raise TypeError(
                    f"El elemento {index} del inventario no es un diccionario."
                )

            missing_fields = required_fields - item.keys()
            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise ValueError(
                    f"El elemento {index} no contiene: {missing}"
                )

    def _resolve_path(self, configured_path: str | Path) -> Path:
        """Resuelve una ruta relativa respecto a la raíz del proyecto."""

        path = Path(configured_path)
        if not path.is_absolute():
            path = self.PROJECT_ROOT / path
        return path.resolve()

    def _discover_files(
        self,
        directory: Path,
        extensions: set[str],
        recursive: bool,
        logger: Any,
    ) -> list[Path]:
        """Busca archivos válidos dentro de un directorio."""

        iterator = directory.rglob("*") if recursive else directory.glob("*")
        files: list[Path] = []

        for path in iterator:
            if not path.is_file():
                continue
            if path.name.startswith(("~$", ".")):
                logger.debug("Archivo temporal u oculto ignorado: %s", path)
                continue
            if path.suffix.lower() not in extensions:
                continue
            if path.stat().st_size == 0:
                message = f"Archivo vacío ignorado: {path}"
                self.state.add_warning(message)
                logger.warning(message)
                continue
            files.append(path.resolve())

        return sorted(files)

    def _build_inventory_item(
        self,
        file_path: Path,
        source_type: str,
    ) -> dict[str, Any]:
        """Construye la metadata técnica de un archivo."""

        stat = file_path.stat()
        modified_utc = datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat()

        try:
            relative_path = file_path.relative_to(self.PROJECT_ROOT)
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
            "modified_utc": modified_utc,
            "sha256": self._calculate_sha256(file_path),
        }

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calcula el hash SHA-256 de un archivo."""

        digest = hashlib.sha256()
        with file_path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _remove_duplicate_content(
        self,
        inventory: list[dict[str, Any]],
        logger: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        """Elimina duplicados exactos utilizando el hash SHA-256."""

        unique: list[dict[str, Any]] = []
        hashes: dict[str, str] = {}
        duplicates = 0

        for item in inventory:
            file_hash = item["sha256"]
            if file_hash in hashes:
                duplicates += 1
                message = (
                    "Archivo duplicado ignorado: "
                    f"{item['relative_path']} es igual a {hashes[file_hash]}"
                )
                self.state.add_warning(message)
                logger.warning(message)
                continue

            hashes[file_hash] = item["relative_path"]
            unique.append(item)

        return unique, duplicates

    def _register_statistics(
        self,
        inventory: list[dict[str, Any]],
        duplicates_ignored: int,
    ) -> dict[str, Any]:
        """Registra y devuelve estadísticas del inventario."""

        statistics = {
            "files_found": len(inventory),
            "total_size_bytes": sum(
                item["size_bytes"] for item in inventory
            ),
            "files_by_extension": dict(
                Counter(item["extension"] for item in inventory)
            ),
            "files_by_source_type": dict(
                Counter(item["source_type"] for item in inventory)
            ),
            "duplicates_ignored": duplicates_ignored,
        }

        for name, value in statistics.items():
            self.state.set_statistic(f"stage01_{name}", value)

        return statistics

    def _save_inventory(
        self,
        inventory: list[dict[str, Any]],
        settings: dict[str, Any],
    ) -> Path | None:
        """Guarda el inventario como JSON en data/staging/inventory."""

        if not settings.get("execution", {}).get(
            "save_intermediate_files",
            True,
        ):
            return None

        staging_path = settings.get("data", {}).get(
            "staging",
            "./data/staging",
        )
        inventory_directory = self._resolve_path(staging_path) / "inventory"
        inventory_directory.mkdir(parents=True, exist_ok=True)

        output_path = (
            inventory_directory
            / f"{self.state.run_id}_file_inventory.json"
        )
        output_path.write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path

    def _save_report(
        self,
        inventory: list[dict[str, Any]],
        statistics: dict[str, Any],
        reports_config: dict[str, Any],
    ) -> Path | None:
        """Genera un reporte técnico TXT de Stage01."""

        general = reports_config.get("general", {})
        if not general.get("enabled", True):
            return None
        if not general.get("generate_reports", True):
            return None

        configured_directory = reports_config.get("directories", {}).get(
            "import",
            "./reports/import",
        )
        report_directory = self._resolve_path(configured_directory)
        report_directory.mkdir(parents=True, exist_ok=True)

        report_path = (
            report_directory
            / f"{self.state.run_id}_stage01_discovery_report.txt"
        )

        total_mb = statistics["total_size_bytes"] / (1024 * 1024)
        lines = [
            "=" * 72,
            "QC_DataMet v0.1.0 - REPORTE STAGE01 DISCOVERY",
            "=" * 72,
            f"Run ID                : {self.state.run_id}",
            f"Fecha UTC             : {datetime.now(timezone.utc).isoformat()}",
            f"Archivos encontrados  : {statistics['files_found']}",
            f"Tamaño total          : {total_mb:.2f} MB",
            f"Duplicados ignorados  : {statistics['duplicates_ignored']}",
            f"Advertencias          : {len(self.state.warnings)}",
            f"Errores                : {len(self.state.errors)}",
            "",
            "ARCHIVOS POR EXTENSIÓN",
            "-" * 72,
        ]

        for extension, count in sorted(
            statistics["files_by_extension"].items()
        ):
            lines.append(f"{extension:<12}: {count}")

        lines.extend(["", "ARCHIVOS INVENTARIADOS", "-" * 72])
        for item in inventory:
            size_mb = item["size_bytes"] / (1024 * 1024)
            lines.append(
                f"{item['relative_path']} | {size_mb:.2f} MB | "
                f"{item['sha256']}"
            )

        if self.state.warnings:
            lines.extend(["", "ADVERTENCIAS", "-" * 72])
            lines.extend(f"- {message}" for message in self.state.warnings)

        lines.extend(["", "=" * 72, "FIN DEL REPORTE", "=" * 72])
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path
