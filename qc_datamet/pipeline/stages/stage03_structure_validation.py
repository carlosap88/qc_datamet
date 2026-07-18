#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 03: validación estructural de los datos ingeridos."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from qc_datamet.pipeline.base_stage import BaseStage
from qc_datamet.utils.logger import get_logger


class Stage03StructureValidation(BaseStage):
    """
    Valida la estructura física de cada DataFrame contra excel_schema.yaml.

    Esta etapa:

    - compara la cantidad de columnas;
    - compara nombres y orden de encabezados;
    - detecta encabezados vacíos;
    - detecta encabezados duplicados;
    - identifica columnas faltantes y adicionales;
    - no convierte tipos ni modifica valores meteorológicos.
    """

    name = "stage03_structure_validation"

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    REPORT_FILENAME = "03_Structure_Validation_Report.txt"

    # =========================================================================
    # VALIDACIÓN DE ENTRADA
    # =========================================================================

    def validate_inputs(self, data: Any) -> None:
        """Valida la salida recibida desde Stage02."""

        if not isinstance(data, list):
            raise TypeError(
                "Stage03 debe recibir la lista generada por Stage02."
            )

        for position, file_result in enumerate(data, start=1):
            if not isinstance(file_result, dict):
                raise TypeError(
                    f"El resultado {position} de Stage02 "
                    "no es un diccionario."
                )

            if "sheets" not in file_result:
                raise ValueError(
                    f"El resultado {position} no contiene 'sheets'."
                )

            if not isinstance(file_result["sheets"], list):
                raise TypeError(
                    f"'sheets' del resultado {position} debe ser una lista."
                )

    # =========================================================================
    # EJECUCIÓN
    # =========================================================================

    def execute(
        self,
        data: Any = None,
    ) -> list[dict[str, Any]]:
        """Valida estructuralmente cada hoja leída por Stage02."""

        stage_started = perf_counter()
        stage02_results: list[dict[str, Any]] = data

        settings = self.config.get("settings.yaml", {})

        logger = get_logger(
            name=self.name,
            settings=settings,
            project_root=self.PROJECT_ROOT,
        )

        expected_headers = self._get_expected_headers()
        schema_name, schema_version = self._get_schema_metadata()
        expected_column_count = len(expected_headers)

        logger.info(
            "Inicio de Stage03 Structure Validation | "
            "archivos=%d | columnas_esperadas=%d | esquema=%s | versión=%s",
            len(stage02_results),
            expected_column_count,
            schema_name,
            schema_version,
        )

        results: list[dict[str, Any]] = []

        for file_result in stage02_results:
            validated_file = self._validate_file(
                file_result=file_result,
                expected_headers=expected_headers,
                logger=logger,
            )
            results.append(validated_file)

        elapsed_seconds = perf_counter() - stage_started

        statistics = self._register_statistics(
            results=results,
            elapsed_seconds=elapsed_seconds,
        )

        report_path = self._save_report(
            results=results,
            statistics=statistics,
            settings=settings,
            schema_name=schema_name,
            schema_version=schema_version,
        )

        if report_path is not None:
            self.state.set_statistic(
                "stage03_report_path",
                str(report_path),
            )

        self._print_summary(
            results=results,
            statistics=statistics,
            report_path=report_path,
            settings=settings,
            schema_name=schema_name,
            schema_version=schema_version,
        )

        logger.info(
            "Fin de Stage03 Structure Validation | "
            "hojas=%d | válidas=%d | inválidas=%d | "
            "integridad=%.2f%% | tiempo=%.3fs",
            statistics["sheets_validated"],
            statistics["sheets_valid"],
            statistics["sheets_invalid"],
            statistics["integrity"],
            statistics["elapsed_seconds"],
        )

        return results

    # =========================================================================
    # ESQUEMA
    # =========================================================================

    def _get_expected_headers(self) -> list[str]:
        """Obtiene los encabezados esperados desde excel_schema.yaml."""

        schema_file = self.config.get("excel_schema.yaml", {})

        if not isinstance(schema_file, dict):
            raise TypeError(
                "excel_schema.yaml debe contener un diccionario."
            )

        schema = schema_file.get(
            "excel_schema",
            schema_file,
        )

        if not isinstance(schema, dict):
            raise TypeError(
                "La raíz 'excel_schema' debe ser un diccionario."
            )

        columns = schema.get("columns", [])

        if not isinstance(columns, (list, dict)):
            raise TypeError(
                "excel_schema.yaml: 'columns' debe ser una lista "
                "o un diccionario."
            )

        expected_headers: list[str] = []

        if isinstance(columns, list):
            for column in columns:
                if isinstance(column, str):
                    header = column

                elif isinstance(column, dict):
                    header = (
                        column.get("source_name")
                        or column.get("name")
                        or column.get("header")
                    )

                else:
                    continue

                if header is not None:
                    expected_headers.append(
                        self._normalize_header(header)
                    )

        else:
            for column_name, column_config in columns.items():
                if isinstance(column_config, dict):
                    header = (
                        column_config.get("source_name")
                        or column_config.get("name")
                        or column_name
                    )
                else:
                    header = column_name

                expected_headers.append(
                    self._normalize_header(header)
                )

        if not expected_headers:
            raise ValueError(
                "No se encontraron encabezados definidos "
                "en excel_schema.yaml."
            )

        return expected_headers

    def _get_schema_metadata(self) -> tuple[str, str]:
        """Obtiene el nombre y la versión declarada del esquema."""

        schema_file = self.config.get("excel_schema.yaml", {})
        schema = (
            schema_file.get("excel_schema", schema_file)
            if isinstance(schema_file, dict)
            else {}
        )

        version = (
            str(schema.get("version", "No definida"))
            if isinstance(schema, dict)
            else "No definida"
        )

        return "excel_schema.yaml", version

    # =========================================================================
    # VALIDACIÓN POR ARCHIVO
    # =========================================================================

    def _validate_file(
        self,
        file_result: dict[str, Any],
        expected_headers: list[str],
        logger: Any,
    ) -> dict[str, Any]:
        """Valida todas las hojas útiles de un archivo."""

        validated_file = dict(file_result)
        validated_sheets: list[dict[str, Any]] = []

        for sheet in file_result.get("sheets", []):
            validated_sheet = self._validate_sheet(
                sheet=sheet,
                expected_headers=expected_headers,
            )

            validated_sheets.append(validated_sheet)

            logger.info(
                "Estructura validada | estación=%s | archivo=%s | "
                "hoja=%s | válida=%s | columnas=%d",
                file_result.get("station_id", "UNKNOWN"),
                file_result.get("filename", "Sin nombre"),
                validated_sheet["sheet_name"],
                validated_sheet["structure_valid"],
                validated_sheet["columns_found"],
            )

        validated_file["sheets"] = validated_sheets
        validated_file["structure_valid"] = bool(
            validated_sheets
        ) and all(
            sheet["structure_valid"]
            for sheet in validated_sheets
        )

        validated_file["validation_errors"] = [
            error
            for sheet in validated_sheets
            for error in sheet["validation_errors"]
        ]

        return validated_file

    def _validate_sheet(
        self,
        sheet: dict[str, Any],
        expected_headers: list[str],
    ) -> dict[str, Any]:
        """Valida una hoja contra los encabezados esperados."""

        dataframe = sheet.get("dataframe")

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"La hoja '{sheet.get('sheet_name')}' "
                "no contiene un DataFrame."
            )

        result = dict(sheet)
        checks_total = 7

        if dataframe.empty:
            checks_passed = 0
            result.update(
                {
                    "structure_valid": False,
                    "columns_expected": len(expected_headers),
                    "columns_found": 0,
                    "headers_found": [],
                    "missing_columns": expected_headers,
                    "extra_columns": [],
                    "duplicate_headers": [],
                    "empty_header_positions": [],
                    "column_count_valid": False,
                    "header_order_valid": False,
                    "headers_valid": False,
                    "validation_checks": checks_total,
                    "validation_passed": checks_passed,
                    "validation_failed": checks_total - checks_passed,
                    "integrity": 0.0,
                    "validation_errors": [
                        "La hoja no contiene datos."
                    ],
                    "dataframe": dataframe,
                }
            )
            return result

        # Stage02 conserva la primera fila física como encabezado.
        raw_headers = dataframe.iloc[0].tolist()

        normalized_headers = [
            self._normalize_header(value)
            for value in raw_headers
        ]

        empty_header_positions = [
            position
            for position, header in enumerate(
                normalized_headers,
                start=1,
            )
            if not header
        ]

        non_empty_headers = [
            header
            for header in normalized_headers
            if header
        ]

        duplicate_headers = sorted(
            header
            for header, count in Counter(
                non_empty_headers
            ).items()
            if count > 1
        )

        missing_columns = [
            header
            for header in expected_headers
            if header not in normalized_headers
        ]

        extra_columns = [
            header
            for header in normalized_headers
            if header
            and header not in expected_headers
        ]

        columns_found = len(normalized_headers)
        columns_expected = len(expected_headers)

        column_count_valid = (
            columns_found == columns_expected
        )

        header_order_valid = (
            normalized_headers == expected_headers
        )

        headers_valid = (
            not empty_header_positions
            and not duplicate_headers
            and not missing_columns
            and not extra_columns
        )

        checks = [
            column_count_valid,
            header_order_valid,
            headers_valid,
            not duplicate_headers,
            not missing_columns,
            not extra_columns,
            not empty_header_positions,
        ]

        checks_passed = sum(checks)
        checks_failed = checks_total - checks_passed
        integrity = round(
            (checks_passed / checks_total) * 100,
            2,
        )

        validation_errors: list[str] = []

        if not column_count_valid:
            validation_errors.append(
                "Cantidad de columnas incorrecta: "
                f"esperadas={columns_expected}, "
                f"encontradas={columns_found}."
            )

        if empty_header_positions:
            validation_errors.append(
                "Encabezados vacíos en posiciones: "
                + ", ".join(
                    str(position)
                    for position in empty_header_positions
                )
                + "."
            )

        if duplicate_headers:
            validation_errors.append(
                "Encabezados duplicados: "
                + ", ".join(duplicate_headers)
                + "."
            )

        if missing_columns:
            validation_errors.append(
                "Columnas faltantes: "
                + ", ".join(missing_columns)
                + "."
            )

        if extra_columns:
            validation_errors.append(
                "Columnas adicionales: "
                + ", ".join(extra_columns)
                + "."
            )

        if not header_order_valid:
            validation_errors.append(
                "El orden de los encabezados no coincide "
                "con excel_schema.yaml."
            )

        structure_valid = not validation_errors

        result.update(
            {
                "structure_valid": structure_valid,
                "columns_expected": columns_expected,
                "columns_found": columns_found,
                "headers_found": normalized_headers,
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
                "duplicate_headers": duplicate_headers,
                "empty_header_positions": empty_header_positions,
                "column_count_valid": column_count_valid,
                "header_order_valid": header_order_valid,
                "headers_valid": headers_valid,
                "validation_checks": checks_total,
                "validation_passed": checks_passed,
                "validation_failed": checks_failed,
                "integrity": integrity,
                "validation_errors": validation_errors,
                # El DataFrame no se modifica todavía.
                "dataframe": dataframe,
            }
        )

        return result

    # =========================================================================
    # NORMALIZACIÓN DE ENCABEZADOS
    # =========================================================================

    @staticmethod
    def _normalize_header(value: Any) -> str:
        """
        Normaliza un encabezado únicamente para compararlo.

        No modifica todavía los nombres reales del DataFrame.
        """

        if value is None or pd.isna(value):
            return ""

        text = str(value)

        # Normaliza caracteres Unicode.
        text = unicodedata.normalize(
            "NFKC",
            text,
        )

        # Sustituye espacio no separable.
        text = text.replace("\u00a0", " ")

        # Elimina tabulaciones, saltos y espacios repetidos.
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # =========================================================================
    # ESTADÍSTICAS
    # =========================================================================

    def _register_statistics(
        self,
        results: list[dict[str, Any]],
        elapsed_seconds: float,
    ) -> dict[str, Any]:
        """Registra estadísticas generales de Stage03."""

        sheets = [
            sheet
            for file_result in results
            for sheet in file_result.get("sheets", [])
        ]

        validation_checks = sum(
            int(sheet.get("validation_checks", 0))
            for sheet in sheets
        )
        validation_passed = sum(
            int(sheet.get("validation_passed", 0))
            for sheet in sheets
        )
        validation_failed = (
            validation_checks - validation_passed
        )

        integrity = round(
            (
                validation_passed
                / validation_checks
                * 100
            )
            if validation_checks
            else 0.0,
            2,
        )

        statistics = {
            "files_validated": len(results),
            "files_valid": sum(
                bool(result.get("structure_valid"))
                for result in results
            ),
            "files_invalid": sum(
                not bool(result.get("structure_valid"))
                for result in results
            ),
            "sheets_validated": len(sheets),
            "sheets_valid": sum(
                bool(sheet.get("structure_valid"))
                for sheet in sheets
            ),
            "sheets_invalid": sum(
                not bool(sheet.get("structure_valid"))
                for sheet in sheets
            ),
            "missing_columns": sum(
                len(sheet.get("missing_columns", []))
                for sheet in sheets
            ),
            "extra_columns": sum(
                len(sheet.get("extra_columns", []))
                for sheet in sheets
            ),
            "duplicate_headers": sum(
                len(sheet.get("duplicate_headers", []))
                for sheet in sheets
            ),
            "empty_headers": sum(
                len(sheet.get("empty_header_positions", []))
                for sheet in sheets
            ),
            "validation_checks": validation_checks,
            "validation_passed": validation_passed,
            "validation_failed": validation_failed,
            "integrity": integrity,
            "elapsed_seconds": round(elapsed_seconds, 3),
        }

        for name, value in statistics.items():
            self.state.set_statistic(
                f"stage03_{name}",
                value,
            )

        return statistics

    # =========================================================================
    # REPORTE
    # =========================================================================

    def _save_report(
        self,
        results: list[dict[str, Any]],
        statistics: dict[str, Any],
        settings: dict[str, Any],
        schema_name: str,
        schema_version: str,
    ) -> Path | None:
        """Genera el reporte técnico de validación estructural."""

        reports_config = (
            self.config
            .get("reports.yaml", {})
            .get("reports", {})
        )

        general = reports_config.get("general", {})

        if not general.get("enabled", True):
            return None

        if not general.get("generate_reports", True):
            return None

        configured_directory = (
            reports_config
            .get("directories", {})
            .get("validation", "./reports/validation")
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
            / self.REPORT_FILENAME
        )

        project = settings.get("project", {})
        project_name = project.get(
            "name",
            "QC_DataMet",
        )
        project_version = project.get(
            "version",
            "0.1.0",
        )

        execution_date = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

        width = 100
        metric_width = 36

        def metric(
            label: str,
            value: Any,
        ) -> str:
            """Genera una línea alineada mediante puntos."""

            dots = "." * max(
                1,
                metric_width - len(label),
            )

            return f"{label} {dots} {value}"

        def status_text(
            condition: bool,
        ) -> str:
            """Devuelve OK o ERROR según el resultado."""

            return "OK" if condition else "ERROR"

        def count_text(
            values: list[Any],
            empty_text: str,
        ) -> str:
            """Devuelve un texto descriptivo para una colección."""

            if not values:
                return empty_text

            return str(len(values))

        lines: list[str] = [
            "=" * width,
            f"{project_name} v{project_version}",
            "STAGE 03 - VALIDACIÓN ESTRUCTURAL",
            "=" * width,
            "",
            metric(
                "Fecha de ejecución",
                execution_date,
            ),
            "",
            "RESUMEN GENERAL",
            "-" * width,
            metric(
                "Archivos procesados",
                statistics.get(
                    "files_validated",
                    0,
                ),
            ),
            metric(
                "Archivos válidos",
                statistics.get(
                    "files_valid",
                    0,
                ),
            ),
            metric(
                "Archivos inválidos",
                statistics.get(
                    "files_invalid",
                    0,
                ),
            ),
            "",
            metric(
                "Hojas procesadas",
                statistics.get(
                    "sheets_validated",
                    0,
                ),
            ),
            metric(
                "Hojas válidas",
                statistics.get(
                    "sheets_valid",
                    0,
                ),
            ),
            metric(
                "Hojas inválidas",
                statistics.get(
                    "sheets_invalid",
                    0,
                ),
            ),
            "",
            metric(
                "Validaciones ejecutadas",
                statistics.get(
                    "validation_checks",
                    0,
                ),
            ),
            metric(
                "Validaciones superadas",
                statistics.get(
                    "validation_passed",
                    0,
                ),
            ),
            metric(
                "Validaciones fallidas",
                statistics.get(
                    "validation_failed",
                    0,
                ),
            ),
            "",
            metric(
                "Integridad promedio",
                (
                    f"{statistics.get('integrity', 0.0):.2f} %"
                ),
            ),
            metric(
                "Tiempo total Stage03",
                (
                    f"{statistics.get('elapsed_seconds', 0.0):.3f} s"
                ),
            ),
            "",
            "DETALLE POR ARCHIVO Y HOJA",
            "=" * width,
        ]

        for file_result in results:
            station_id = file_result.get(
                "station_id",
                "UNKNOWN",
            )

            filename = file_result.get(
                "relative_path",
                file_result.get(
                    "filename",
                    "Sin nombre",
                ),
            )

            lines.extend(
                [
                    "",
                    "ARCHIVO",
                    "-" * width,
                    metric(
                        "Estación",
                        station_id,
                    ),
                    metric(
                        "Archivo",
                        filename,
                    ),
                ]
            )

            for sheet in file_result.get(
                "sheets",
                [],
            ):
                sheet_name = sheet.get(
                    "sheet_name",
                    "Sin nombre",
                )

                structure_valid = sheet.get(
                    "structure_valid",
                    False,
                )

                result_status = (
                    "VÁLIDA"
                    if structure_valid
                    else "INVÁLIDA"
                )

                integrity = float(
                    sheet.get(
                        "integrity",
                        0.0,
                    )
                )

                duplicate_headers = sheet.get(
                    "duplicate_headers",
                    [],
                ) or []

                missing_columns = sheet.get(
                    "missing_columns",
                    [],
                ) or []

                extra_columns = sheet.get(
                    "extra_columns",
                    [],
                ) or []

                empty_header_positions = sheet.get(
                    "empty_header_positions",
                    [],
                ) or []

                validation_errors = sheet.get(
                    "validation_errors",
                    [],
                ) or []

                expected_columns = sheet.get(
                    "columns_expected",
                    sheet.get(
                        "expected_columns",
                        0,
                    ),
                )

                found_columns = sheet.get(
                    "columns_found",
                    sheet.get(
                        "actual_columns",
                        0,
                    ),
                )

                lines.extend(
                    [
                        "",
                        "=" * width,
                        f"HOJA: {sheet_name}",
                        "=" * width,
                        "",
                        "ESTADO GENERAL",
                        "-" * width,
                        metric(
                            "Resultado estructural",
                            result_status,
                        ),
                        metric(
                            "Integridad estructural",
                            f"{integrity:.2f} %",
                        ),
                        "",
                        "ESQUEMA DE VALIDACIÓN",
                        "-" * width,
                        metric(
                            "Esquema utilizado",
                            schema_name,
                        ),
                        metric(
                            "Versión del esquema",
                            schema_version,
                        ),
                        metric(
                            "Columnas esperadas",
                            expected_columns,
                        ),
                        metric(
                            "Columnas encontradas",
                            found_columns,
                        ),
                        "",
                        "VALIDACIONES REALIZADAS",
                        "-" * width,
                        metric(
                            "Cantidad de columnas",
                            status_text(
                                sheet.get(
                                    "column_count_valid",
                                    False,
                                )
                            ),
                        ),
                        metric(
                            "Orden de columnas",
                            status_text(
                                sheet.get(
                                    "header_order_valid",
                                    False,
                                )
                            ),
                        ),
                        metric(
                            "Encabezados",
                            status_text(
                                sheet.get(
                                    "headers_valid",
                                    False,
                                )
                            ),
                        ),
                        metric(
                            "Encabezados duplicados",
                            count_text(
                                duplicate_headers,
                                "Ninguno",
                            ),
                        ),
                        metric(
                            "Columnas faltantes",
                            count_text(
                                missing_columns,
                                "Ninguna",
                            ),
                        ),
                        metric(
                            "Columnas adicionales",
                            count_text(
                                extra_columns,
                                "Ninguna",
                            ),
                        ),
                        metric(
                            "Encabezados vacíos",
                            count_text(
                                empty_header_positions,
                                "Ninguno",
                            ),
                        ),
                        "",
                        "MÉTRICAS DE VALIDACIÓN",
                        "-" * width,
                        metric(
                            "Validaciones ejecutadas",
                            sheet.get(
                                "validation_checks",
                                0,
                            ),
                        ),
                        metric(
                            "Validaciones superadas",
                            sheet.get(
                                "validation_passed",
                                0,
                            ),
                        ),
                        metric(
                            "Validaciones fallidas",
                            sheet.get(
                                "validation_failed",
                                0,
                            ),
                        ),
                        metric(
                            "Porcentaje de cumplimiento",
                            f"{integrity:.2f} %",
                        ),
                        "",
                        "OBSERVACIONES",
                        "-" * width,
                    ]
                )

                if structure_valid and not validation_errors:
                    lines.append(
                        "No se detectaron inconsistencias estructurales."
                    )

                else:
                    lines.append(
                        "Se detectaron inconsistencias estructurales."
                    )

                    if validation_errors:
                        lines.extend(
                            [
                                "",
                                "ERRORES DETECTADOS",
                                "-" * width,
                            ]
                        )

                        for error in validation_errors:
                            lines.append(
                                f"• {error}"
                            )

                    if missing_columns:
                        lines.extend(
                            [
                                "",
                                "COLUMNAS FALTANTES",
                                "-" * width,
                            ]
                        )

                        for column in missing_columns:
                            lines.append(
                                f"• {column}"
                            )

                    if extra_columns:
                        lines.extend(
                            [
                                "",
                                "COLUMNAS ADICIONALES",
                                "-" * width,
                            ]
                        )

                        for column in extra_columns:
                            lines.append(
                                f"• {column}"
                            )

                    if duplicate_headers:
                        lines.extend(
                            [
                                "",
                                "ENCABEZADOS DUPLICADOS",
                                "-" * width,
                            ]
                        )

                        for header in duplicate_headers:
                            lines.append(
                                f"• {header}"
                            )

                    if empty_header_positions:
                        lines.extend(
                            [
                                "",
                                "ENCABEZADOS VACÍOS",
                                "-" * width,
                            ]
                        )

                        for position in empty_header_positions:
                            lines.append(
                                f"• Posición {position}"
                            )

                lines.extend(
                    [
                        "",
                        "=" * width,
                    ]
                )

        lines.extend(
            [
                "",
                "=" * width,
                "FIN DEL REPORTE",
                "=" * width,
            ]
        )

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
        results: list[dict[str, Any]],
        statistics: dict[str, Any],
        report_path: Path | None,
        settings: dict[str, Any],
        schema_name: str,
        schema_version: str,
    ) -> None:
        """Muestra el resumen de Stage03 en consola."""

        project = settings.get("project", {})
        project_name = project.get("name", "QC_DataMet")
        project_version = project.get("version", "0.1.0")

        width = 100

        def metric(label: str, value: Any) -> str:
            dots = "." * max(1, 31 - len(label))
            return f"{label} {dots} {value}"

        print()
        print("=" * width)
        print(f"{project_name} v{project_version}")
        print("STAGE 03 - VALIDACIÓN ESTRUCTURAL")
        print("=" * width)
        print()
        print(
            metric(
                "Archivos procesados",
                statistics["files_validated"],
            )
        )
        print(
            metric(
                "Archivos válidos",
                statistics["files_valid"],
            )
        )
        print(
            metric(
                "Archivos inválidos",
                statistics["files_invalid"],
            )
        )
        print()
        print(
            metric(
                "Hojas procesadas",
                statistics["sheets_validated"],
            )
        )
        print(
            metric(
                "Hojas válidas",
                statistics["sheets_valid"],
            )
        )
        print(
            metric(
                "Hojas inválidas",
                statistics["sheets_invalid"],
            )
        )
        print()
        print(
            metric(
                "Validaciones realizadas",
                statistics["validation_checks"],
            )
        )
        print(
            metric(
                "Validaciones superadas",
                statistics["validation_passed"],
            )
        )
        print(
            metric(
                "Validaciones fallidas",
                statistics["validation_failed"],
            )
        )
        print()
        print(
            metric(
                "Integridad promedio",
                f"{statistics['integrity']:.2f} %",
            )
        )
        print(
            metric(
                "Tiempo total Stage03",
                f"{statistics['elapsed_seconds']:.3f} s",
            )
        )
        print()
        print(metric("Esquema validado", schema_name))
        print(metric("Versión esquema", schema_version))
        print()
        print(
            metric(
                "Reporte técnico",
                report_path or "No generado",
            )
        )
        print("=" * width)
        print()

    # =========================================================================
    # VALIDACIÓN DE SALIDA
    # =========================================================================

    def validate_outputs(
        self,
        result: Any,
    ) -> None:
        """Valida la salida producida por Stage03."""

        if not isinstance(result, list):
            raise TypeError(
                "Stage03 debe devolver una lista."
            )

        for file_result in result:
            if not isinstance(file_result, dict):
                raise TypeError(
                    "Cada resultado de Stage03 debe ser un diccionario."
                )

            if "structure_valid" not in file_result:
                raise ValueError(
                    "El resultado no contiene 'structure_valid'."
                )

    # =========================================================================
    # RUTAS
    # =========================================================================

    def _resolve_path(
        self,
        configured_path: str | Path,
    ) -> Path:
        """Resuelve una ruta contra la raíz del proyecto."""

        path = Path(configured_path)

        if not path.is_absolute():
            path = self.PROJECT_ROOT / path

        return path.resolve()