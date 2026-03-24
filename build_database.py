"""Build the teamnl_events DuckDB database from the ODISSEI Knowledge Graph.

Run from the repository root:
    python build_database.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

import duckdb
import polars as pl
from query_kg import extract_datasets_metadata, extract_variables_metadata  # noqa: E402

DB_PATH = Path(__file__).parent / "data" / "event_datasets.duckdb"


def build_datasets_table(con: duckdb.DuckDBPyConnection) -> None:
    print("Querying datasets metadata from ODISSEI KG …")
    df = extract_datasets_metadata()
    print(f"  Retrieved {len(df)} rows")

    df = df.rename({
        "dataset": "dataset_id",
        "shortTitle": "alt_title",
        "title": "title",
        "publicationDate": "publication_date",
        "validFrom": "valid_from",
        "validUntil": "valid_until",
        "frequency": "frequency",
        "doi": "doi",
        "samplingProcedure": "sampling_procedure",
        "keywords": "keywords",
        "isEventDataset": "is_event_dataset",
        "isFrequencyDataset": "is_frequency_dataset",
    })

    # Deduplicate on dataset_id (keep first occurrence)
    df = df.unique(subset=["dataset_id"], keep="first")

    con.execute("DROP TABLE IF EXISTS kg_datasets")
    con.register("_datasets_staging", df.to_arrow())
    con.execute("""
        CREATE TABLE kg_datasets AS
        SELECT
            dataset_id,
            title,
            alt_title,
            TRY_CAST(publication_date AS DATE) AS publication_date,
            TRY_CAST(valid_from AS DATE) AS valid_from,
            TRY_CAST(valid_until AS DATE) AS valid_until,
            frequency,
            doi,
            keywords,
            sampling_procedure,
            is_event_dataset,
            is_frequency_dataset
        FROM _datasets_staging
    """)
    con.unregister("_datasets_staging")

    count = con.execute("SELECT COUNT(*) FROM kg_datasets").fetchone()[0]
    print(f"  Wrote {count} datasets to DuckDB")


def build_variables_table(con: duckdb.DuckDBPyConnection) -> None:
    dataset_uris = [r[0] for r in con.execute("SELECT dataset_id FROM kg_datasets").fetchall()]
    print(f"Querying variables for {len(dataset_uris)} datasets …")

    df = extract_variables_metadata(dataset_uris)
    print(f"  Retrieved {len(df)} rows")

    df = df.rename({
        "var": "variable_id",
        "dataset": "dataset_id",
        "name": "variable_name",
        "label": "label_",
        "description": "description",
        "dataType": "data_type",
        "definition": "definition",
        "validFrom": "valid_from",
    })

    con.execute("DROP TABLE IF EXISTS kg_variables")
    con.register("_variables_staging", df.to_arrow())
    con.execute("""
        CREATE TABLE kg_variables AS
        SELECT
            variable_id,
            dataset_id,
            variable_name,
            label_,
            description,
            data_type,
            definition,
            TRY_CAST(valid_from AS DATE) AS valid_from,
            is_tijdstip
        FROM _variables_staging
    """)
    con.unregister("_variables_staging")

    count = con.execute("SELECT COUNT(*) FROM kg_variables").fetchone()[0]
    print(f"  Wrote {count} variables to DuckDB")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        build_datasets_table(con)
        build_variables_table(con)
    finally:
        con.close()
    print(f"\nDatabase written to {DB_PATH}")


if __name__ == "__main__":
    main()
