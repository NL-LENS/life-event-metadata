# teamnl-events-dataset
Repository to coordinate work around the creation of an event-based dataset in the CBS ME

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

or
```bash
uv sync
```

### Building the database

You can create a duckdb database with main metadata around a broad set of datasets
that could be relevant. Run

```python
python build_database.py
```

or ```bash
uv run build_database.py
```

The resulting database is stored at `./data/event_datasets.duckdb`. 

#### Database content

The database has two tables
- `kg_datasets`: datasets in the KG meeting certain criteria (see below).
- `kg_variables`: all variables of these datasets and corresponding metadata.

There are two types of datasets. They all are published by CBS, have a RINPERSOON column, and are
either an "tijdstip dataset" or a "frequency dataset"

*Tijdstip datasets* are identified as datasets that have at least one time variable
("tijdstip" occurs in the variable label), and this variable is linked to a
controlled vocabulary (SKOS).

*Frequency datasets* are datasets published at a certain frequency---the most
commonly-occurring in the knowledge graph as a whole, plus "school year" frequency
for education-related datasets. In frequency datasets, the frequency field is
a required property, while it's an optional property for event datasets.

The table `kg_variables` contains the metadata on all variables in the
`kg_datasets` table: data type, description, validity, an indicator of being a
"time variable" (`is_tijdstip`, defining an event dataset). There is also some metadata
about properties on the KG, such as how many predicates the variable has and which
predicate determined the value of `is_tijdstip`.


### Claude skills for exploring the KG

You can use the `explore-knowledge-graph` skill with Claude Code. See `.claude/`
for the source code.

## Content

### `data/` directory

Main data:
- `event_datasets.duckdb`: database created by `build_database.py`
- `Datasets 9424.csv`: Datasets in 9424 project from CBS, but still incomplete (ie, no KINDOUDERTAB)

Deprecated but kept for reference:
- `data-designs-with-event_preflabel.csv` is an export of a SPARQL query run on Triply (see [here](https://kg.odissei.nl/odissei/-/queries/Data-designs-with-events/3)) on the KG. It is intended to list all the CBS data designs in the Portal which contain RINPERSOON AND a variable which mentions "Tijdstip" in its metadata. The query found 818 RINPERSOON + Time combinations, from 258 datasets
- `data-designs-extended.csv` is an export of a SPARQL query run in the notebook `sparql_exploration.ipynb`

### Notebooks
- `sparql_exploration.ipynb` extends the original query, queries against the API, and stores results in `data/data-designs-extended.csv`

## Resources
- CBS pdf scraper: https://github.com/odissei-data/cbs-pdf-names-scraper

## Development

Install development version of the package:
```
python -m pip install -e ".[dev]"
```
