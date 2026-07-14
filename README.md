# QC_DataMet v0.1.0

> **Quality Control Platform for Aeronautical Meteorological
> Observations**

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Status](https://img.shields.io/badge/status-development-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Architecture](https://img.shields.io/badge/architecture-modular-success.svg)
![Pipeline](https://img.shields.io/badge/pipeline-16%20stages-blueviolet.svg)

------------------------------------------------------------------------

## Overview

**QC_DataMet** is a professional Python platform for the ingestion,
consolidation, normalization, quality control (QC), climatological
analysis and publication of aeronautical meteorological observations.

The project has been designed to process historical and operational
meteorological databases while preserving complete traceability of every
observation.

The architecture follows a modular pipeline that allows new data
sources, QC algorithms and products to be incorporated without modifying
the existing workflow.

------------------------------------------------------------------------

# Key Features

-   Modular Pipeline Architecture
-   Multiple Excel file ingestion
-   CSV, METAR, BUFR and Parquet ready
-   YAML-based configuration
-   Automatic normalization
-   Physical and temporal QC
-   Meteorological consistency checks
-   Climatological and statistical analysis
-   Quality Flag system
-   Automatic reports
-   Graphics generation
-   Full audit trail
-   Scalable architecture

------------------------------------------------------------------------

# Processing Pipeline

``` text
Raw Data
   │
   ▼
Stage01 Discovery
   │
   ▼
Stage02 Ingestion
   │
   ▼
Stage03 Structure Validation
   │
   ▼
Stage04 Consolidation
   │
   ▼
Stage05 Preprocessing
   │
   ▼
Stage06 Prepared Data Export
   │
   ▼
Stage07 Basic Quality Control
   │
   ▼
Stage08 Basic QC Summary
   │
   ▼
Stage09 Meteorological QC
   │
   ▼
Stage10 Meteorological QC Summary
   │
   ▼
Stage11 Advanced QC
   │
   ▼
Stage12 Final Quality Assessment
   │
   ▼
Stage13 Reporting
   │
   ▼
Stage14 Graphics
   │
   ▼
Stage15 Final Export
   │
   ▼
Stage16 Publication
```

------------------------------------------------------------------------

# Development Roadmap

  Version    Main Goal
  ---------- ---------------------------------------------------
  **v1.0**   Ingestion, preprocessing and basic QC
  **v1.1**   Fundamental Quality Control
  **v1.2**   Meteorological consistency
  **v1.3**   Climatology and statistics
  **v1.4**   Reports, graphics and publication
  **v2.0**   Institutional platform (API, Database, Dashboard)

## Official Stages

    Stage Description
  ------- --------------------------------
       01 Discovery
       02 Ingestion
       03 Structure Validation
       04 Consolidation
       05 Preprocessing
       06 Prepared Data Export
       07 Basic Quality Control
       08 Basic QC Summary
       09 Meteorological Quality Control
       10 Meteorological QC Summary
       11 Advanced Quality Control
       12 Final Quality Assessment
       13 Reporting
       14 Graphics
       15 Final Export
       16 Publication

------------------------------------------------------------------------

# Project Architecture

``` text
qc_datamet/
├── assets/
├── config/
├── data/
├── docs/
├── logs/
├── notebooks/
├── reports/
├── scripts/
├── src/
├── tests/
├── main.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

Detailed documentation:

-   docs/architecture.md
-   docs/pipeline.md
-   docs/configuration.md
-   docs/qc_rules.md
-   docs/data_dictionary.md
-   docs/user_manual.md

------------------------------------------------------------------------

# Design Principles

1.  Original data are immutable.
2.  Every observation is preserved.
3.  All corrections are traceable.
4.  Configuration is externalized in YAML.
5.  Each Stage has a single responsibility.
6.  Each QC check is independent.
7.  The pipeline supports checkpoints and restart.
8.  The architecture is designed for long-term scalability.

------------------------------------------------------------------------

# Supported Data Sources

  Input                       Status
  --------------------------- ---------
  Excel (.xlsx/.xlsm/.xlsb)   ✅
  CSV                         ✅
  METAR                       🚧
  BUFR                        🚧
  Parquet                     ✅
  NetCDF                      Planned
  Database                    Planned

------------------------------------------------------------------------

# Outputs

-   CSV
-   Excel
-   Parquet
-   PDF Reports
-   PNG Graphics
-   Executive Summaries
-   QC Statistics

------------------------------------------------------------------------

# Technologies

-   Python 3.12+
-   pandas
-   NumPy
-   PyYAML
-   openpyxl
-   matplotlib
-   scipy
-   reportlab
-   pytest

------------------------------------------------------------------------

# Installation

``` bash
git clone https://github.com/<user>/qc_datamet.git
cd qc_datamet
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

------------------------------------------------------------------------

# Running

``` bash
python main.py
```

------------------------------------------------------------------------

# Project Status

QC_DataMet is under active development following the official roadmap.

------------------------------------------------------------------------

# Contributing

Contributions are welcome. Future contribution guidelines will be
published in `docs/contributing.md`.

------------------------------------------------------------------------

# License

MIT License.

------------------------------------------------------------------------

# Author

**Roberto Carlos Arqqui Poma**

Meteorological Software Developer

Peru
