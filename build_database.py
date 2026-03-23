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
from query_kg import extract_datasets_metadata  # noqa: E402

DB_PATH = Path(__file__).parent / "data" / "teamnl_events.duckdb"


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

    con.execute("DROP TABLE IF EXISTS datasets")
    con.register("_datasets_staging", df.to_arrow())
    con.execute("""
        CREATE TABLE datasets AS
        SELECT
            dataset_id,
            title,
            alt_title,
            publication_date,
            valid_from,
            valid_until,
            frequency,
            doi,
            keywords,
            sampling_procedure,
            is_event_dataset,
            is_frequency_dataset
        FROM _datasets_staging
    """)
    con.unregister("_datasets_staging")

    count = con.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
    print(f"  Wrote {count} datasets to DuckDB")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        build_datasets_table(con)
    finally:
        con.close()
    print(f"\nDatabase written to {DB_PATH}")


if __name__ == "__main__":
    main()
