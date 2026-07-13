# METEO_QC Architecture

**Project:** METEO_QC  
**Version:** 1.0.0  
**Author:** Roberto Arqui  
**Institution:** Dirección de Meteorología Aeronáutica (DIRMA)  
**Organization:** Fuerza Aérea del Perú (FAP)  
**Language:** Python 3.12+  
**Architecture:** Modular Pipeline Architecture

---

# 1. Purpose

METEO_QC is a professional software platform designed to perform automated Quality Control (QC) of historical and operational aeronautical meteorological observations in accordance with the recommendations of:

- World Meteorological Organization (WMO)
- International Civil Aviation Organization (ICAO)

The platform has been designed for long-term maintenance, scalability, reproducibility and institutional deployment.

---

# 2. Design Philosophy

The architecture follows the following software engineering principles.

- Separation of Responsibilities (SRP)
- Open / Closed Principle
- DRY (Don't Repeat Yourself)
- High Cohesion
- Low Coupling
- Configuration over Code
- Modular Design
- Pipeline Processing
- Reproducible Processing
- Data Traceability
- Testability

Every module has one responsibility only.

Business logic must never be located in **main.py**.

---

# 3. High-Level Architecture

```
                  +----------------+
                  |   main.py      |
                  +-------+--------+
                          |
                          |
                 Pipeline Orchestrator
                          |
     --------------------------------------------------
     |          |           |          |              |
 Import   Preprocessing      QC     Reports      Export
     |          |           |          |              |
     -----------------------------------------------
                     Shared DataFrame
```

Each stage receives a DataFrame and returns a DataFrame.

---

# 4. Project Structure

```
meteo_qc/

config/
data/
reports/
logs/
src/
tests/
docs/
assets/
```

Each directory has a well-defined responsibility.

---

# 5. Layered Architecture

The project follows a layered architecture.

```
Presentation Layer

main.py

↓

Pipeline Layer

stage01_import.py
stage02_preprocessing.py
stage03_qc.py
stage04_reports.py
stage05_export.py

↓

Business Layer

QC Modules
Normalization
Metadata

↓

Data Layer

Excel
CSV
Parquet
BUFR
METAR
Database

↓

Configuration Layer

YAML Files
```

---

# 6. Pipeline Architecture

The execution flow is composed of independent stages.

```
Import
    ↓
Preprocessing
    ↓
Quality Control
    ↓
Reports
    ↓
Export
```

Every stage:

- receives a DataFrame
- performs one responsibility
- returns a DataFrame
- produces logs
- generates metadata
- records execution time

---

# 7. Data Flow

```
Excel Files

      ↓

Import

      ↓

Merged DataFrame

      ↓

Normalization

      ↓

Quality Control

      ↓

Flags

      ↓

Reports

      ↓

Final Dataset

      ↓

CSV
Excel
Parquet
```

---

# 8. Configuration

All configuration is externalized.

```
config/

settings.yaml
excel_schema.yaml
variables.yaml
stations.yaml
units.yaml
qc_rules.yaml
data_dictionary.yaml
descriptors/
```

No meteorological rules shall be hardcoded.

---

# 9. Quality Control Modules

Each QC module is completely independent.

```
Schema Check

Datetime Check

Duplicate Check

Missing Check

Range Check

Consistency Check

Temporal Check

Metadata Check

Station Check

Spatial Check

Climatology Check

Statistical Check
```

Each module returns

- Updated DataFrame
- Flags
- Statistics
- Report
- Execution Time

---

# 10. Flags System

Observations are never deleted.

Problems are indicated through flags.

Example

```
Temperature = 72 °C

↓

Observation remains

↓

Flag = OUT_OF_RANGE
```

Multiple flags are allowed.

```
OUT_OF_RANGE

TEMPORAL

MISSING

CLIMATOLOGY
```

---

# 11. Metadata

Every processing stage generates metadata.

Example

```
Processing Time

Processed Records

Errors

Warnings

Corrected Values

Version

Execution Date

Hash

Station
```

---

# 12. Logging

Logging is completely separated.

```
pipeline.log

import.log

qc.log

errors.log
```

Each record contains

- Timestamp
- Module
- Function
- File
- Line
- Station
- Pipeline Stage
- Message
- Duration

---

# 13. Reports

Reports are generated automatically.

```
Import Report

Schema Report

Datetime Report

Duplicate Report

Missing Report

QC Report

Statistics Report

Climatology Report

Metadata Report

Executive Report
```

Output formats

- PDF
- CSV
- Excel

---

# 14. Graphics

Automatic graphics generation.

```
Histograms

Heatmaps

Wind Roses

Time Series

Boxplots

Monthly Climatology

Dashboard
```

---

# 15. Export

Supported formats

```
CSV

Excel

Parquet
```

Future versions

```
PostgreSQL

NetCDF

BUFR

SQLite

REST API
```

---

# 16. Performance

Designed for

- 30+ years of observations
- Millions of records
- Hundreds of Excel files
- Low memory consumption
- Parallel processing (future)
- Incremental execution

---

# 17. Scalability

The architecture allows adding new modules without modifying existing ones.

Example

```
src/qc/

solar_check.py

↓

No changes required in
duplicate_check.py
range_check.py
temporal_check.py
```

Only the pipeline registers the new module.

---

# 18. Error Handling

Errors never stop the pipeline unless critical.

Levels

- INFO
- WARNING
- ERROR
- CRITICAL

Every exception is logged.

---

# 19. Testing Strategy

The project includes automated tests.

```
Unit Tests

Integration Tests

Pipeline Tests

Regression Tests
```

Coverage should remain above 90%.

---

# 20. Coding Standards

The project follows

- PEP 8
- Type Hints
- NumPy Docstrings
- Ruff
- Black
- Pytest

---

# 21. Future Roadmap

Planned features include

- PostgreSQL backend
- Web Dashboard
- REST API
- Docker deployment
- Cloud execution
- Real-time QC
- METAR parser
- BUFR decoder
- NetCDF support
- GOES satellite integration
- WRF integration
- AI anomaly detection
- Automatic TAF generation
- Machine Learning models
- Statistical forecasting

---

# 22. Summary

METEO_QC is conceived as an institutional-grade software platform rather than a collection of scripts.

Its modular architecture, pipeline-oriented processing, external configuration, comprehensive logging, automated reporting, and extensibility make it suitable for long-term operational use within aeronautical meteorological services while remaining aligned with WMO and ICAO recommendations.

---
**End of Document**