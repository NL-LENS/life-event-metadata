# teamnl-events-dataset
Repository to coordinate work around the creation of an event-based dataset in the CBS ME

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Building the database

Run

```python
python build_database.py
```

## Content

### `data/` directory
- `data-designs-with-event_preflabel.csv` is an export of a SPARQL query run on Triply (see [here](https://kg.odissei.nl/odissei/-/queries/Data-designs-with-events/3)) on the KG. It is intended to list all the CBS data designs in the Portal which contain RINPERSOON AND a variable which mentions "Tijdstip" in its metadata. The query found 818 RINPERSOON + Time combinations, from 258 datasets
- `data-designs-extended.csv` is an export of a SPARQL query run in the notebook `sparql_exploration.ipynb`
- `Datasets 9424.csv`: Datasets in 9424 project from CBS, but still incomplete (no KINDOUDERTAB)
- `event_dataset.duckdb`: database created by `build_database.py`



### Notebooks
- `exploration.ipynb` explores `data/data-design-with-event_preflabel.csv`
- `sparql_exploration.ipynb` extends the original query, queries against the API, and stores results in `data/data-designs-extended.csv`

## Resources
- CBS pdf scraper: https://github.com/odissei-data/cbs-pdf-names-scraper
