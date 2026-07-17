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
from time import perf_counter
from typing import Any

from qc_datamet.pipeline.base_stage import BaseStage
from qc_datamet.utils.logger import get_logger


class Stage01Discovery(BaseStage):
    """Prepara directorios y descubre archivos de entrada configurados."""

    name = "stage01_discovery"

    PROJECT_ROOT = Path(__file__).resolve().parents[3]

    INVENTORY_FILENAME = "01_File_Inventory.json"
    REPORT_FILENAME = "01_Discovery_Report.txt"

    # =========================================================================
    # EJECUCIÓN
    # =========================================================================

    def validate_inputs(self, data: Any) -> None:
        """Stage01 no recibe resultados de etapas anteriores."""

        if data is not None:
            raise ValueError(
                "Stage01Discovery no admite datos de entrada."
            )

    def execute(self, data: Any = None) -> list[dict[str, Any]]:
        """Prepara directorios y genera el inventario técnico."""

        started = perf_counter()

        settings = self.config.get("settings.yaml", {})
        reports_config = (
            self.config
            .get("reports.yaml", {})
            .get("reports", {})
        )

        logger = get_logger(
            name=self.name,
            settings=settings,
            project_root=self.PROJECT_ROOT,
        )

        # El Run ID se conserva únicamente en el log y en el estado interno.
        logger.info(
            "Inicio de Stage01 Discovery | run_id=%s",
            self.state.run_id,
        )

        self._create_project_directories(
            settings=settings,
            logger=logger,
        )

        inventory = self._discover_all_sources(
            settings=settings,
            logger=logger,
        )

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

        elapsed_seconds = round(
            perf_counter() - started,
            3,
        )

        statistics["elapsed_seconds"] = elapsed_seconds

        report_path = self._save_report(
            inventory=inventory,
            statistics=statistics,
            settings=settings,
            reports_config=reports_config,
            inventory_path=inventory_path,
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

        self.state.set_statistic(
            "stage01_elapsed_seconds",
            elapsed_seconds,
        )

        self._print_summary(
            inventory=inventory,
            statistics=statistics,
            inventory_path=inventory_path,
            report_path=report_path,
            settings=settings,
        )

        logger.info(
            "Fin de Stage01 Discovery | archivos=%d | "
            "duplicados=%d | advertencias=%d | errores=%d | "
            "duracion=%.3f s",
            len(inventory),
            duplicate_count,
            len(self.state.warnings),
            len(self.state.errors),
            elapsed_seconds,
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
                missing = ", ".join(
                    sorted(missing_fields)
                )

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
        """Crea los directorios configurados que todavía no existen."""

        execution = settings.get("execution", {})

        if not execution.get(
            "create_missing_directories",
            True,
        ):
            self.state.set_statistic(
                "stage01_directories_created",
                0,
            )
            return

        configured_paths = self._collect_directory_paths(
            settings
        )

        created_count = 0

        for configured_path in configured_paths:
            directory = self._resolve_path(
                configured_path
            )

            if directory.exists():
                if not directory.is_dir():
                    raise NotADirectoryError(
                        f"La ruta configurada no es un directorio: "
                        f"{directory}"
                    )

                continue

            try:
                directory.mkdir(
                    parents=True,
                    exist_ok=True,
                )

            except OSError as error:
                message = (
                    f"No se pudo crear el directorio "
                    f"{directory}: {error}"
                )

                self.state.add_error(message)
                logger.error(message)
                raise

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

            if isinstance(value, str) and value.strip():
                paths.append(value)

        paths.extend(
            self._extract_paths(
                settings.get("data", {})
            )
        )

        logging_directory = (
            settings
            .get("logging", {})
            .get("directory")
        )

        if (
            isinstance(logging_directory, str)
            and logging_directory.strip()
        ):
            paths.append(logging_directory)

        return list(dict.fromkeys(paths))

    def _extract_paths(
        self,
        value: Any,
    ) -> list[str]:
        """Extrae recursivamente rutas almacenadas en diccionarios."""

        paths: list[str] = []

        if isinstance(value, str):
            if value.strip():
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

    def _discover_all_sources(
        self,
        settings: dict[str, Any],
        logger: logging.Logger,
    ) -> list[dict[str, Any]]:
        """Descubre archivos en todas las fuentes habilitadas."""

        inventory: list[dict[str, Any]] = []

        raw_config = (
            settings
            .get("data", {})
            .get("raw", {})
        )

        input_config = settings.get(
            "input",
            {},
        )

        if not isinstance(raw_config, dict):
            raise TypeError(
                "settings.yaml: 'data.raw' debe ser un diccionario."
            )

        if not isinstance(input_config, dict):
            raise TypeError(
                "settings.yaml: 'input' debe ser un diccionario."
            )

        for source_type, source_settings in input_config.items():
            if not isinstance(source_settings, dict):
                continue

            if not source_settings.get("enabled", False):
                logger.info(
                    "Fuente deshabilitada: %s",
                    source_type,
                )
                continue

            configured_directory = raw_config.get(
                source_type
            )

            if not configured_directory:
                message = (
                    "No existe una ruta raw configurada para "
                    f"'{source_type}'."
                )

                self.state.add_warning(message)
                logger.warning(message)
                continue

            source_directory = self._resolve_path(
                configured_directory
            )

            extensions = self._get_extensions(
                source_settings
            )

            if not extensions:
                message = (
                    "No existen extensiones configuradas para "
                    f"'{source_type}'."
                )

                self.state.add_warning(message)
                logger.warning(message)
                continue

            discovered_files = self._discover_files(
                directory=source_directory,
                extensions=extensions,
                recursive=bool(
                    source_settings.get(
                        "recursive",
                        True,
                    )
                ),
                logger=logger,
            )

            logger.info(
                "Fuente %-8s | directorio=%s | archivos=%d",
                source_type,
                source_directory,
                len(discovered_files),
            )

            for file_path in discovered_files:
                try:
                    inventory_item = (
                        self._build_inventory_item(
                            file_path=file_path,
                            source_type=source_type,
                        )
                    )

                except OSError as error:
                    message = (
                        f"No se pudo inventariar "
                        f"{file_path}: {error}"
                    )

                    self.state.add_warning(message)
                    logger.warning(message)
                    continue

                inventory.append(inventory_item)
                self.state.add_discovered_file(file_path)

        return inventory

    @staticmethod
    def _get_extensions(
        source_settings: dict[str, Any],
    ) -> set[str]:
        """Normaliza las extensiones configuradas."""

        extensions: set[str] = set()

        configured_extensions = source_settings.get(
            "extensions",
            [],
        )

        if not isinstance(
            configured_extensions,
            (list, tuple, set),
        ):
            return extensions

        for extension in configured_extensions:
            normalized = str(
                extension
            ).strip().lower()

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
        """Descubre archivos válidos sin abrir su contenido tabular."""

        if not directory.is_dir():
            message = (
                f"El directorio de entrada no existe: "
                f"{directory}"
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
                    f"No se pudo obtener metadata de "
                    f"{path}: {error}"
                )

                self.state.add_warning(message)
                logger.warning(message)
                continue

            if size_bytes == 0:
                message = (
                    f"Archivo vacío ignorado: {path}"
                )

                self.state.add_warning(message)
                logger.warning(message)
                continue

            discovered.append(
                path.resolve()
            )

        return sorted(
            discovered,
            key=lambda item: item.as_posix().lower(),
        )

    @staticmethod
    def _is_ignored_file(path: Path) -> bool:
        """Detecta archivos temporales, ocultos o del sistema."""

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
        """Construye la metadata técnica de un archivo."""

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
            "sha256": self._calculate_sha256(
                file_path
            ),
        }

    @staticmethod
    def _calculate_sha256(
        file_path: Path,
    ) -> str:
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
        known_hashes: dict[str, str] = {}
        duplicate_count = 0

        for item in inventory:
            file_hash = item["sha256"]

            if file_hash in known_hashes:
                duplicate_count += 1

                message = (
                    "Archivo duplicado ignorado: "
                    f"{item['relative_path']} es idéntico a "
                    f"{known_hashes[file_hash]}"
                )

                self.state.add_warning(message)
                logger.warning(message)
                continue

            known_hashes[file_hash] = (
                item["relative_path"]
            )

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

        for statistic_name, value in statistics.items():
            self.state.set_statistic(
                f"stage01_{statistic_name}",
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
        """Obtiene una ruta de staging compatible con formatos anteriores."""

        staging = (
            settings
            .get("data", {})
            .get("staging", {})
        )

        if isinstance(staging, dict):
            configured_path = staging.get(
                key,
                default,
            )

        elif isinstance(staging, str):
            configured_path = str(
                Path(staging) / key
            )

        else:
            configured_path = default

        return self._resolve_path(
            configured_path
        )

    def _prepare_output_path(
        self,
        path: Path,
        settings: dict[str, Any],
    ) -> Path:
        """Valida si un archivo existente puede reemplazarse."""

        overwrite = (
            settings
            .get("execution", {})
            .get("overwrite_outputs", True)
        )

        if path.exists() and not overwrite:
            raise FileExistsError(
                "El archivo de salida ya existe y "
                "overwrite_outputs está deshabilitado: "
                f"{path}"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    def _save_inventory(
        self,
        inventory: list[dict[str, Any]],
        settings: dict[str, Any],
    ) -> Path | None:
        """Guarda el inventario técnico como JSON."""

        execution = settings.get(
            "execution",
            {},
        )

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

        output_path = self._prepare_output_path(
            inventory_directory
            / self.INVENTORY_FILENAME,
            settings,
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
        settings: dict[str, Any],
        reports_config: dict[str, Any],
        inventory_path: Path | None,
    ) -> Path | None:
        """Genera el reporte técnico TXT de Stage01."""

        general = reports_config.get(
            "general",
            {},
        )

        if not general.get("enabled", True):
            return None

        if not general.get(
            "generate_reports",
            True,
        ):
            return None

        project = settings.get(
            "project",
            {},
        )

        project_name = project.get(
            "name",
            "QC_DataMet",
        )

        project_version = project.get(
            "version",
            "0.1.0",
        )

        organization = project.get(
            "organization",
            "Dirección de Meteorología Aeronáutica y Espacial",
        )

        institution = project.get(
            "institution",
            "Fuerza Aérea del Perú",
        )

        configured_directory = (
            reports_config
            .get("directories", {})
            .get("import", "./reports/import")
        )

        report_directory = self._resolve_path(
            configured_directory
        )

        report_path = self._prepare_output_path(
            report_directory / self.REPORT_FILENAME,
            settings,
        )

        files_by_source = statistics.get(
            "files_by_source_type",
            {},
        )

        files_by_extension = statistics.get(
            "files_by_extension",
            {},
        )

        execution_date = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

        elapsed_seconds = statistics.get(
            "elapsed_seconds",
            0.0,
        )

        width = 100

        lines: list[str] = [
            "=" * width,
            f"{project_name} v{project_version}",
            "STAGE 01 - DESCUBRIMIENTO E INVENTARIO DE ARCHIVOS",
            "=" * width,
            "",
            "INFORMACIÓN GENERAL",
            "-" * width,
            f"Proyecto             : {project_name}",
            f"Versión              : {project_version}",
            f"Organización         : {organization}",
            f"Institución          : {institution}",
            "Etapa                : Stage01 Discovery",
            f"Fecha de ejecución   : {execution_date}",
            "Estado               : COMPLETADO",
            f"Tiempo de ejecución  : {elapsed_seconds:.3f} s",
            "",
            "=" * width,
            "RESUMEN GENERAL",
            "=" * width,
            "",
            (
                "Archivos encontrados : "
                f"{statistics.get('files_found', 0)}"
            ),
            (
                "Tamaño total         : "
                f"{self._format_size(
                    statistics.get(
                        'total_size_bytes',
                        0,
                    )
                )}"
            ),
            (
                "Duplicados ignorados : "
                f"{statistics.get(
                    'duplicates_ignored',
                    0,
                )}"
            ),
            (
                "Directorios creados  : "
                f"{self.state.statistics.get(
                    'stage01_directories_created',
                    0,
                )}"
            ),
            (
                "Advertencias         : "
                f"{len(self.state.warnings)}"
            ),
            (
                "Errores              : "
                f"{len(self.state.errors)}"
            ),
            "",
            "=" * width,
            "ARCHIVOS POR TIPO DE FUENTE",
            "=" * width,
            "",
        ]

        input_config = settings.get(
            "input",
            {},
        )

        for source_type, source_config in input_config.items():
            if not isinstance(source_config, dict):
                continue

            enabled = bool(
                source_config.get(
                    "enabled",
                    False,
                )
            )

            quantity = files_by_source.get(
                source_type,
                0,
            )

            source_status = (
                "HABILITADO"
                if enabled
                else "DESHABILITADO"
            )

            lines.append(
                f"{source_type.upper():<15}: "
                f"{quantity:<5} | {source_status}"
            )

        lines.extend([
            "",
            "=" * width,
            "ARCHIVOS POR EXTENSIÓN",
            "=" * width,
            "",
        ])

        if files_by_extension:
            for extension, quantity in sorted(
                files_by_extension.items()
            ):
                lines.append(
                    f"{extension:<15}: {quantity}"
                )

        else:
            lines.append(
                "No se encontraron extensiones registradas."
            )

        lines.extend([
            "",
            "=" * width,
            "INVENTARIO DE ARCHIVOS",
            "=" * width,
            "",
            (
                f"{'N°':>3}  "
                f"{'TIPO':<10} "
                f"{'EXT.':<8} "
                f"{'TAMAÑO':>12}  "
                f"{'ESTADO':<8} "
                "ARCHIVO"
            ),
            "-" * width,
        ])

        if inventory:
            for index, item in enumerate(
                inventory,
                start=1,
            ):
                item_size = self._format_size(
                    item["size_bytes"]
                )

                lines.append(
                    f"{index:>3}  "
                    f"{item['source_type'].upper():<10} "
                    f"{item['extension']:<8} "
                    f"{item_size:>12}  "
                    f"{'OK':<8} "
                    f"{item['relative_path']}"
                )

                lines.append(
                    "     Modificado UTC : "
                    f"{item['modified_utc']}"
                )

                lines.append(
                    "     SHA-256        : "
                    f"{item['sha256']}"
                )

                lines.append("-" * width)

        else:
            lines.append(
                "No se encontraron archivos válidos para procesar."
            )

        if self.state.warnings:
            lines.extend([
                "",
                "=" * width,
                "ADVERTENCIAS",
                "=" * width,
                "",
            ])

            lines.extend(
                f"- {warning}"
                for warning in self.state.warnings
            )

        if self.state.errors:
            lines.extend([
                "",
                "=" * width,
                "ERRORES",
                "=" * width,
                "",
            ])

            lines.extend(
                f"- {error}"
                for error in self.state.errors
            )

        lines.extend([
            "",
            "=" * width,
            "SALIDAS GENERADAS",
            "=" * width,
            "",
            (
                "Inventario JSON      : "
                f"{inventory_path or 'No generado'}"
            ),
            f"Reporte técnico      : {report_path}",
            "",
            "=" * width,
            "PRÓXIMA ETAPA",
            "=" * width,
            "",
            "Stage02 - Ingesta de archivos",
            "",
            "Objetivo:",
            (
                "    Abrir los archivos descubiertos y "
                "verificar que puedan leerse correctamente."
            ),
            "",
            "Stage02 obtendrá:",
            "    - Número de hojas.",
            "    - Número de filas.",
            "    - Número de columnas.",
            "    - Motor de lectura utilizado.",
            "    - Tiempo de lectura.",
            "    - Estado de lectura de cada archivo.",
            "",
            "=" * width,
            "FIN DEL REPORTE",
            "=" * width,
        ])

        report_path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        return report_path

    # =========================================================================
    # PRESENTACIÓN
    # =========================================================================

    def _print_summary(
        self,
        inventory: list[dict[str, Any]],
        statistics: dict[str, Any],
        inventory_path: Path | None,
        report_path: Path | None,
        settings: dict[str, Any],
    ) -> None:
        """Muestra un resumen profesional de Stage01 en consola."""

        project = settings.get(
            "project",
            {},
        )

        project_name = project.get(
            "name",
            "QC_DataMet",
        )

        project_version = project.get(
            "version",
            "0.1.0",
        )

        width = 100

        print()
        print("=" * width)

        print(
            f"{project_name} v{project_version} — "
            "STAGE 01: DESCUBRIMIENTO E INVENTARIO"
        )

        print("=" * width)
        print("Estado              : COMPLETADO")

        print(
            "Archivos encontrados: "
            f"{statistics.get('files_found', 0)}"
        )

        print(
            "Tamaño total        : "
            f"{self._format_size(
                statistics.get(
                    'total_size_bytes',
                    0,
                )
            )}"
        )

        print(
            "Duplicados ignorados: "
            f"{statistics.get(
                'duplicates_ignored',
                0,
            )}"
        )

        print(
            "Directorios creados : "
            f"{self.state.statistics.get(
                'stage01_directories_created',
                0,
            )}"
        )

        print(
            "Advertencias        : "
            f"{len(self.state.warnings)}"
        )

        print(
            "Errores              : "
            f"{len(self.state.errors)}"
        )

        print(
            "Duración            : "
            f"{statistics.get('elapsed_seconds', 0.0):.3f} s"
        )

        print("-" * width)

        print(
            f"{'N°':>3}  "
            f"{'TIPO':<10} "
            f"{'EXT.':<8} "
            f"{'TAMAÑO':>12}  "
            "ARCHIVO"
        )

        print("-" * width)

        if inventory:
            for index, item in enumerate(
                inventory,
                start=1,
            ):
                item_size = self._format_size(
                    item["size_bytes"]
                )

                print(
                    f"{index:>3}  "
                    f"{item['source_type'].upper():<10} "
                    f"{item['extension']:<8} "
                    f"{item_size:>12}  "
                    f"{item['relative_path']}"
                )

        else:
            print(
                "No se encontraron archivos de entrada."
            )

        print("-" * width)
        print("RESUMEN POR TIPO DE FUENTE")

        files_by_source = statistics.get(
            "files_by_source_type",
            {},
        )

        input_config = settings.get(
            "input",
            {},
        )

        for source_type, source_config in input_config.items():
            if not isinstance(source_config, dict):
                continue

            enabled = bool(
                source_config.get(
                    "enabled",
                    False,
                )
            )

            quantity = files_by_source.get(
                source_type,
                0,
            )

            source_status = (
                "habilitado"
                if enabled
                else "deshabilitado"
            )

            print(
                f"  {source_type.upper():<12}: "
                f"{quantity:<5} ({source_status})"
            )

        print()
        print("RESUMEN POR EXTENSIÓN")

        files_by_extension = statistics.get(
            "files_by_extension",
            {},
        )

        if files_by_extension:
            for extension, count in sorted(
                files_by_extension.items()
            ):
                print(
                    f"  {extension:<12}: {count}"
                )

        else:
            print("  Sin extensiones.")

        print("=" * width)

        print(
            "Inventario JSON : "
            f"{inventory_path or 'No generado'}"
        )

        print(
            "Reporte técnico : "
            f"{report_path or 'No generado'}"
        )

        print("=" * width)
        print()

    @staticmethod
    def _format_size(
        size_bytes: int,
    ) -> str:
        """Convierte bytes a una unidad legible."""

        size = float(size_bytes)

        for unit in (
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        ):
            if size < 1024 or unit == "TB":
                return f"{size:,.2f} {unit}"

            size /= 1024

        return f"{size_bytes} B"