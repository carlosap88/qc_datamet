# QC_DATAMET
## Arquitectura del Sistema

**Versión:** 0.1.0  
**Estado:** Alpha  
**Autor:** Roberto Carlos Arqqui Poma  
**Institución:** Dirección de Meteorología Aeronáutica y Espacial  
**Organización:** Fuerza Aérea del Perú  
**Lenguaje:** Python 3.12+

---

# 1. Propósito

QC_DATAMET es una plataforma modular para la ingestión, normalización,
consolidación, control de calidad, análisis y publicación de observaciones
meteorológicas aeronáuticas históricas y operacionales.

El sistema está diseñado para preservar la trazabilidad completa de cada
registro y permitir una evolución progresiva desde archivos Excel históricos
hasta productos institucionales, bases de datos, servicios web y procesos de
control de calidad avanzados.

---

# 2. Principios de diseño

QC_DATAMET sigue los siguientes principios:

1. Los datos originales son inmutables.
2. Ninguna observación se elimina durante el control de calidad.
3. Toda modificación o corrección debe ser trazable.
4. La configuración se mantiene fuera del código mediante archivos YAML.
5. Cada etapa del pipeline tiene una única responsabilidad.
6. Cada control de calidad debe ser independiente y comprobable.
7. Las etapas pueden generar checkpoints y reanudar ejecuciones.
8. Las dependencias entre etapas deben validarse antes de ejecutar.
9. El código debe permanecer desacoplado de los formatos de entrada.
10. Las funciones implementadas deben disponer de pruebas automatizadas.

---

# 3. Arquitectura general

```text
Fuentes de datos
    │
    ├── Excel
    ├── CSV
    ├── METAR / SPECI
    ├── TAF
    └── BUFR (futuro)
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
Stages 07–12 Quality Control
    │
    ▼
Stages 13–16 Reporting, Export and Publication
```

La arquitectura combina:

- una capa de configuración;
- una capa de acceso a datos;
- una capa de pipeline;
- una capa de control de calidad;
- una capa de reportes y visualización;
- una capa de exportación y publicación.

---

# 4. Estructura del proyecto

```text
qc_datamet/
│
├── qc_datamet/                  # Paquete Python importable
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── version.py
│   │
│   ├── config/                  # Código para cargar y validar YAML
│   ├── pipeline/                # Orquestador, estado y etapas
│   ├── io/                      # Lectores y escritores
│   ├── qc/                      # Controles de calidad
│   ├── reports/                 # Generadores de reportes
│   ├── visualization/           # Gráficos y visualizaciones
│   └── utils/                   # Utilidades comunes
│
├── config/                      # Configuración operativa YAML
├── data/                        # Datos de entrada, proceso y salida
├── docs/                        # Documentación técnica
├── tests/                       # Pruebas automatizadas
├── assets/                      # Recursos gráficos y plantillas
├── reports/                     # Productos generados
├── logs/                        # Registros de ejecución
│
├── main.py                      # Punto de entrada de compatibilidad
├── pyproject.toml               # Configuración del paquete
├── requirements.txt
├── README.md
└── LICENSE
```

La carpeta externa `qc_datamet/` corresponde al repositorio. La carpeta
interna `qc_datamet/` corresponde al paquete Python importable.

---

# 5. Paquete Python

Todos los módulos deben importarse desde el paquete `qc_datamet`.

Ejemplo correcto:

```python
from qc_datamet.pipeline.orchestrator import PipelineOrchestrator
```

Ejemplo incorrecto:

```python
from src.pipeline.orchestrator import PipelineOrchestrator
```

La carpeta `src` no forma parte de la arquitectura oficial adoptada para el
proyecto.

---

# 6. Puntos de entrada

QC_DATAMET debe poder ejecutarse de tres formas:

```bash
qc-datamet
```

```bash
python -m qc_datamet
```

```bash
python main.py
```

El archivo `main.py` debe contener únicamente el puente hacia la interfaz de
línea de comandos. La lógica del negocio nunca debe implementarse allí.

---

# 7. Configuración

Toda la configuración operativa reside en `config/`.

| Archivo | Responsabilidad |
|---|---|
| `settings.yaml` | Configuración global del sistema |
| `pipeline.yaml` | Orden, activación y dependencias de las etapas |
| `excel_schema.yaml` | Contrato físico de los archivos Excel |
| `data_dictionary.yaml` | Significado, tipos, unidades y mapeos semánticos |
| `canonical_schema.yaml` | Estructura y orden del dataset final |
| `stations.yaml` | Catálogo maestro de estaciones |
| `variables.yaml` | Catálogo de variables meteorológicas |
| `units.yaml` | Catálogo y conversiones de unidades |
| `qc_rules.yaml` | Reglas de control de calidad |
| `reports.yaml` | Configuración de reportes |
| `descriptors/` | Catálogos de códigos y descriptores |

Las reglas meteorológicas no deben codificarse directamente en los módulos
Python cuando puedan representarse mediante configuración.

---

# 8. Pipeline oficial

El flujo oficial consta de dieciséis etapas:

| Etapa | Nombre | Estado inicial |
|---:|---|---|
| 01 | Discovery | En desarrollo |
| 02 | Ingestion | Pendiente |
| 03 | Structure Validation | Pendiente |
| 04 | Consolidation | Pendiente |
| 05 | Preprocessing | Pendiente |
| 06 | Prepared Data Export | Pendiente |
| 07 | Basic Quality Control | Pendiente |
| 08 | Basic QC Summary | Pendiente |
| 09 | Meteorological Quality Control | Pendiente |
| 10 | Meteorological QC Summary | Pendiente |
| 11 | Advanced Quality Control | Pendiente |
| 12 | Final Quality Assessment | Pendiente |
| 13 | Reporting | Pendiente |
| 14 | Graphics | Pendiente |
| 15 | Final Export | Pendiente |
| 16 | Publication | Pendiente |

Solo deben mantenerse habilitadas las etapas que dispongan de implementación
y pruebas suficientes.

---

# 9. Contrato de una etapa

Cada etapa debe implementar un contrato común mediante `BaseStage`.

Métodos mínimos:

```python
validate_inputs()
execute()
validate_outputs()
save_checkpoint()
```

Cada etapa debe:

- recibir un contexto de ejecución;
- validar sus entradas;
- ejecutar una sola responsabilidad;
- generar metadata;
- registrar errores y advertencias;
- validar sus salidas;
- devolver el contexto actualizado;
- guardar un checkpoint cuando corresponda.

---

# 10. Estado del pipeline

`PipelineState` debe registrar, como mínimo:

- `run_id`;
- etapa actual;
- etapas completadas;
- fecha y hora de inicio;
- fecha y hora de finalización;
- archivos encontrados;
- registros procesados;
- advertencias;
- errores;
- rutas de checkpoints;
- versión del sistema.

El estado debe ser serializable para permitir reanudación y auditoría.

---

# 11. Checkpoints

Los checkpoints se dividen en dos componentes:

```text
metadata → JSON
dataset  → Parquet
```

JSON se utiliza para estado, estadísticas y trazabilidad. Parquet se utiliza
para DataFrames y datasets intermedios de gran volumen.

Los checkpoints deben permitir:

- reanudar una ejecución interrumpida;
- evitar repetir etapas ya completadas;
- reproducir el procesamiento;
- comparar resultados entre ejecuciones.

---

# 12. Flujo de datos

```text
Archivo original
    │
    ▼
Inventario y hash
    │
    ▼
Lectura
    │
    ▼
Validación estructural
    │
    ▼
Consolidación
    │
    ▼
Normalización semántica
    │
    ▼
Dataset preparado
    │
    ▼
Controles de calidad
    │
    ▼
Flags y evaluación final
    │
    ▼
Reportes y exportaciones
```

Cada registro debe conservar información de procedencia, como:

- archivo de origen;
- hoja de origen;
- fila de origen;
- hash del archivo;
- fecha de procesamiento;
- versión del pipeline.

---

# 13. Datos y almacenamiento

La estructura de datos recomendada es:

```text
data/
├── raw/
│   ├── excel/
│   ├── csv/
│   ├── metar/
│   └── bufr/
├── staging/
├── processed/
├── consolidated/
├── parquet/
│   ├── cache/
│   ├── daily/
│   ├── monthly/
│   └── yearly/
├── quarantine/
│   ├── files/
│   └── records/
└── final/
```

Los archivos originales permanecen en `raw/` y no deben modificarse.

---

# 14. Control de calidad

El sistema de QC se organiza en tres niveles:

## 14.1 Control básico

- estructura;
- tipos de datos;
- valores faltantes;
- duplicados;
- rangos físicos básicos;
- fechas inválidas;
- identificación de estación.

## 14.2 Control meteorológico

- temperatura de rocío menor o igual a temperatura del aire;
- consistencia entre viento medio y ráfaga;
- consistencia entre visibilidad y fenómenos;
- coherencia entre nubosidad y techo;
- relaciones entre presión, temperatura y humedad.

## 14.3 Control avanzado

- persistencia temporal;
- saltos abruptos;
- climatología;
- estadística robusta;
- comparación espacial;
- detección de anomalías.

Las observaciones no se eliminan. Los problemas se representan mediante
banderas de calidad.

---

# 15. Banderas de calidad

Una observación puede contener múltiples flags.

Ejemplos:

```text
MISSING
OUT_OF_RANGE
DUPLICATE
TEMPORAL_INCONSISTENCY
METEOROLOGICAL_INCONSISTENCY
CLIMATOLOGICAL_OUTLIER
MANUALLY_REVIEWED
```

Cada flag debe incluir:

- código;
- severidad;
- variable afectada;
- regla aplicada;
- valor observado;
- mensaje descriptivo;
- fecha de evaluación.

---

# 16. Logging

El logging debe estar separado de la lógica del negocio.

Cada registro debe incluir:

- timestamp;
- nivel;
- módulo;
- función;
- etapa;
- estación;
- archivo;
- mensaje;
- duración cuando corresponda.

Niveles utilizados:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

---

# 17. Reportes y visualización

Los módulos de reportes y gráficos deben consumir únicamente resultados ya
procesados y no modificar los datos meteorológicos.

Productos previstos:

- reporte de importación;
- reporte estructural;
- resumen de datos faltantes;
- resumen de duplicados;
- reporte QC;
- estadísticas por estación;
- climatología mensual;
- series temporales;
- histogramas;
- mapas de calor;
- rosas de viento;
- reportes ejecutivos.

---

# 18. Exportación

Formatos previstos:

- CSV;
- Excel;
- Parquet;
- PDF;
- PNG;
- PostgreSQL;
- API REST;
- BUFR y NetCDF en versiones futuras.

El esquema canónico debe definir el orden y la estructura de las salidas.

---

# 19. Estrategia de pruebas

El proyecto debe incluir:

- pruebas unitarias;
- pruebas de configuración;
- pruebas de integración;
- pruebas de pipeline;
- pruebas de regresión;
- validación con datasets controlados.

Objetivo de cobertura:

```text
>= 90 % para módulos críticos
```

Las pruebas deben ejecutarse automáticamente mediante GitHub Actions.

---

# 20. Estándares de desarrollo

QC_DATAMET adopta:

- PEP 8;
- type hints;
- docstrings;
- Ruff;
- Black;
- Pytest;
- Conventional Commits;
- revisión mediante pull requests para cambios estructurales.

Ejemplos de commits:

```text
feat(config): add units catalog
refactor(core): adopt standard Python package structure
docs: update architecture documentation
fix(pipeline): validate stage dependencies
```

---

# 21. Escalabilidad

La arquitectura debe permitir incorporar nuevas fuentes y controles sin
modificar los módulos existentes.

Ejemplos futuros:

- PostgreSQL;
- dashboard web;
- API REST;
- ejecución en contenedores;
- procesamiento incremental;
- control de calidad en tiempo real;
- parser METAR/SPECI/TAF;
- decodificador BUFR;
- integración GOES y WRF;
- detección de anomalías mediante IA.

---

# 22. Estado actual

QC_DATAMET se encuentra en versión `0.1.0` y estado Alpha.

Prioridades inmediatas:

1. consolidar la estructura del paquete Python;
2. validar automáticamente los YAML;
3. implementar `PipelineState`;
4. implementar `BaseStage`;
5. implementar el orquestador;
6. completar y probar `Stage01Discovery`;
7. configurar integración continua.

Las etapas futuras deben permanecer deshabilitadas hasta disponer de código y
pruebas automatizadas.

---

# 23. Resumen

QC_DATAMET se concibe como una plataforma institucional y mantenible, no como
una colección de scripts aislados. Su arquitectura modular, el pipeline de
etapas independientes, la configuración externa, la trazabilidad, los
checkpoints y el sistema de banderas permiten desarrollar una solución sólida
para el control de calidad de datos meteorológicos aeronáuticos.
