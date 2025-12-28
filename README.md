# Cosilico Arch

**Foundational archive for all raw government source files.**

Arch is the unified source of truth for statutes, regulations, IRS guidance, microdata, crosstabs, and parameters that power Cosilico's rules engine.

## Features

- **Federal statutes** — All 54 titles of the US Code from official USLM XML
- **IRS guidance** — Revenue Procedures, Revenue Rulings, Notices (570+ documents)
- **State codes** — NY Open Legislation API, more states coming
- **Microdata** — CPS ASEC, IRS PUF, SIPP (via microplex integration)
- **Crosstabs** — IRS SOI, Census tables
- **Provenance** — Every file tracked with fetch date, source URL, checksums
- **REST API** — Query documents by citation, keyword, or path
- **Change detection** — Know when upstream sources update

## Quick Start

```bash
# Install
pip install cosilico-arch

# Run the API server
arch serve

# Or use the CLI
arch get "26 USC 32"        # Get IRC § 32 (EITC)
arch search "earned income" # Search across documents
```

## CLI Usage

```bash
# Download sources
arch download 26                    # Download Title 26 (IRC) from uscode.gov
arch download-state ny              # Download NY state laws
arch irs-guidance --year 2024       # Fetch IRS guidance for 2024

# Query
arch get "26 USC 32"                # Get specific section
arch search "child tax credit"      # Full-text search
arch stats                          # Show database stats

# API
arch serve                          # Start REST API at localhost:8000
```

## Python API

```python
from arch import Arch

archive = Arch()

# Get a specific section
eitc = archive.get("26 USC 32")
print(eitc.title)        # "Earned income"
print(eitc.text)         # Full section text
print(eitc.subsections)  # Hierarchical structure

# Search
results = archive.search("child tax credit", title=26)
for section in results:
    print(f"{section.citation}: {section.title}")

# Get historical version
eitc_2020 = archive.get("26 USC 32", as_of="2020-01-01")
```

## REST API

```bash
# Get section by citation
curl http://localhost:8000/v1/sections/26/32

# Search
curl "http://localhost:8000/v1/search?q=earned+income&title=26"

# Get specific subsection
curl http://localhost:8000/v1/sections/26/32/a/1

# Historical version
curl "http://localhost:8000/v1/sections/26/32?as_of=2020-01-01"
```

## Data Sources

| Category | Source | Format | Files |
|----------|--------|--------|-------|
| Statutes | uscode.house.gov | USLM XML | 8 titles, 20k+ sections |
| IRS Guidance | irs.gov/pub/irs-drop | PDF/HTML | 570+ documents |
| State Laws | NY Open Legislation | JSON | Tax, Social Services |
| Microdata | Census, IRS | ZIP | CPS, PUF, SIPP |
| Crosstabs | IRS SOI, Census | XLSX | Income tables |

## Architecture

```
arch/
├── src/arch/
│   ├── __init__.py
│   ├── archive.py        # Main Arch class
│   ├── models.py         # Pydantic models for statutes
│   ├── models_guidance.py # Models for IRS guidance
│   ├── parsers/
│   │   ├── uslm.py       # USLM XML parser
│   │   └── ny_laws.py    # NY Open Legislation parser
│   ├── fetchers/
│   │   ├── irs_bulk.py   # IRS bulk guidance fetcher
│   │   └── irs_guidance.py
│   ├── api/
│   │   └── main.py       # FastAPI app
│   ├── cli.py            # Command-line interface
│   └── storage/
│       ├── base.py       # Storage interface
│       ├── sqlite.py     # SQLite + FTS5 backend
│       └── postgres.py   # PostgreSQL backend
├── data/                  # Downloaded data (gitignored)
├── catalog/               # Structured document catalog
│   ├── guidance/          # IRS guidance documents
│   ├── statute/           # Statute extracts
│   └── parameters/        # Policy parameters by year
└── sources/               # Raw source archives
```

## Storage

Arch uses two storage tiers:

- **Cloudflare R2** — Raw files (PDFs, XML, ZIPs)
- **PostgreSQL (Supabase)** — Parsed content, metadata, full-text search

The `arch` schema in cosilico-db tracks:
- File provenance (source URL, fetch timestamp, checksums)
- Parsed content with tsvector for search
- Cross-references between documents

## Deployment

### Modal (Serverless)

```bash
# Deploy to Modal
modal deploy modal_app.py

# Upload database to Modal Volume
modal volume put arch-db arch.db /data/arch.db
```

### Docker

```bash
# Build and run
docker build -t arch .
docker run -p 8000:8000 -v $(pwd)/arch.db:/app/arch.db arch
```

## License

Apache 2.0

## Related Repos

- [rac](https://github.com/CosilicoAI/rac) — Core DSL engine
- [rac-us](https://github.com/CosilicoAI/rac-us) — US federal rules in RAC
- [microplex](https://github.com/CosilicoAI/microplex) — Microdata processing
- [cosilico-db](https://github.com/CosilicoAI/cosilico-db) — PostgreSQL schema
