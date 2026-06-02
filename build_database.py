"""Build the DuckDB database from the ODISSEI Knowledge Graph.

Run from the repository root:
    python build_database.py --data-dir /path/to/data
"""

import argparse
import logging
from pathlib import Path
import duckdb
from life_event_metadata.queries import extract_datasets_metadata
from life_event_metadata.queries import extract_variables_metadata

logger = logging.getLogger(__name__)

DB_NAME = "event_datasets.duckdb"


def build_datasets_table(con: duckdb.DuckDBPyConnection) -> None:
    """Query the knowledge graph for datasets metadata."""
    logger.info("Querying datasets metadata from ODISSEI KG...")
    dataset_df = extract_datasets_metadata()
    logger.info("--Retrieved %s rows", len(dataset_df))

    dataset_df = dataset_df.rename(
        {
            "dataset": "dataset_id",
            "shortTitle": "alt_title",
            "title": "title",
            "description": "description",
            "publicationDate": "publication_date",
            "validFrom": "valid_from",
            "validUntil": "valid_until",
            "frequency": "frequency",
            "samplingProcedure": "sampling_procedure",
            "keywords": "keywords",
            "isTijdstipDataset": "is_tijdstip_dataset",
            "isFrequencyDataset": "is_frequency_dataset",
        },
    )

    # Deduplicate on dataset_id (keep first occurrence)
    dataset_df = dataset_df.unique(subset=["dataset_id"], keep="first")

    con.execute("DROP TABLE IF EXISTS kg_datasets")
    con.register("_datasets_staging", dataset_df.to_arrow())
    con.execute("""
        CREATE TABLE kg_datasets AS
        SELECT
            dataset_id,
            title,
            alt_title,
            description,
            TRY_CAST(publication_date AS DATE) AS publication_date,
            TRY_CAST(valid_from AS DATE) AS valid_from,
            TRY_CAST(valid_until AS DATE) AS valid_until,
            frequency,
            keywords,
            sampling_procedure,
            is_tijdstip_dataset,
            is_frequency_dataset
        FROM _datasets_staging
    """)
    con.unregister("_datasets_staging")

    count = con.execute("SELECT COUNT(*) FROM kg_datasets").fetchone()[0]
    logger.info("--Wrote %s datasets to database", count)


def build_variables_table(con: duckdb.DuckDBPyConnection) -> None:
    """Build the variables table."""
    dataset_uris = [r[0] for r in con.execute("SELECT dataset_id FROM kg_datasets").fetchall()]
    logger.info("Querying variables for %s datasets", len(dataset_uris))

    variables_df = extract_variables_metadata(dataset_uris)
    logger.info("--Retrieved %s rows", len(variables_df))

    variables_df = variables_df.rename(
        {
            "var": "variable_id",
            "dataset": "dataset_id",
            "name": "variable_name",
            "label": "label_",
            "description": "description",
            "dataType": "data_type",
            "definition": "definition",
            "validFrom": "valid_from",
            "vocabLabel": "vocab_label",
            "numPredicates": "num_predicates",
            "tijdstipPredicates": "tijdstip_predicates",
            "isTijdstip": "is_tijdstip",
            "isPersonIdentifier": "is_person_identifier",
        },
    )

    con.execute("DROP TABLE IF EXISTS kg_variables")
    con.register("_variables_staging", variables_df.to_arrow())
    con.execute("""
        CREATE TABLE kg_variables AS
        SELECT
            variable_id,
            dataset_id,
            variable_name,
            label_,
            vocab_label,
            description,
            data_type,
            definition,
            num_predicates,
            tijdstip_predicates,
            TRY_CAST(valid_from AS DATE) AS valid_from,
            is_tijdstip,
            is_person_identifier
        FROM _variables_staging
    """)
    con.unregister("_variables_staging")

    count = con.execute("SELECT COUNT(*) FROM kg_variables").fetchone()[0]
    logger.info("--Wrote %s variables to database.", count)


def main() -> None:
    """Build the db."""
    parser = argparse.ArgumentParser(description="Build the DuckDB database from the ODISSEI Knowledge Graph.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default="data/",
        help="Directory where the database will be stored (default: ./data)",
    )
    args = parser.parse_args()

    db_path = args.data_dir / DB_NAME
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        build_datasets_table(con)
        build_variables_table(con)
    logger.info("Database written to %s", db_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
