"""Tests for the final DuckDB database schema and data integrity."""

import duckdb
import pytest
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "event_datasets.duckdb"


@pytest.fixture(scope="session")
def con():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


class TestDatasetsTable:
    def test_table_exists(self, con):
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        assert "kg_datasets" in tables

    def test_required_columns(self, con):
        cols = {r[0] for r in con.execute("DESCRIBE kg_datasets").fetchall()}
        expected = {
            "dataset_id",
            "title",
            "alt_title",
            "publication_date",
            "valid_from",
            "valid_until",
            "frequency",
            "doi",
            "keywords",
            "is_event_dataset",
            "is_frequency_dataset",
        }
        assert expected.issubset(cols), f"Missing columns: {expected - cols}"

    def test_dataset_id_is_primary_key(self, con):
        total = con.execute("SELECT COUNT(*) FROM kg_datasets").fetchone()[0]
        distinct = con.execute(
            "SELECT COUNT(DISTINCT dataset_id) FROM kg_datasets"
        ).fetchone()[0]
        assert total == distinct, "dataset_id must be unique"

    def test_no_null_identifiers(self, con):
        nulls = con.execute(
            "SELECT COUNT(*) FROM kg_datasets WHERE dataset_id IS NULL OR alt_title IS NULL"
        ).fetchone()[0]
        assert nulls == 0

    def test_valid_from_not_null(self, con):
        nulls = con.execute(
            "SELECT COUNT(*) FROM kg_datasets WHERE valid_from IS NULL"
        ).fetchone()[0]
        assert nulls == 0

    def test_boolean_flags_not_null(self, con):
        nulls = con.execute(
            "SELECT COUNT(*) FROM kg_datasets "
            "WHERE is_event_dataset IS NULL OR is_frequency_dataset IS NULL"
        ).fetchone()[0]
        assert nulls == 0

    def test_has_event_datasets(self, con):
        count = con.execute(
            "SELECT COUNT(*) FROM kg_datasets WHERE is_event_dataset"
        ).fetchone()[0]
        assert count > 0, "Expected at least some event datasets"

    def test_has_frequency_datasets(self, con):
        count = con.execute(
            "SELECT COUNT(*) FROM kg_datasets WHERE is_frequency_dataset"
        ).fetchone()[0]
        assert count > 0, "Expected at least some frequency datasets"

    def test_frequency_values_when_flagged(self, con):
        """Frequency datasets must have a frequency in the expected set."""
        expected_freqs = {"Jaar", "Kalenderjaar", "Niet eenduidig", "Stand", "Maand"}
        rows = con.execute(
            "SELECT DISTINCT frequency FROM kg_datasets WHERE is_frequency_dataset"
        ).fetchall()
        actual = {r[0] for r in rows if r[0] is not None}
        assert actual.issubset(expected_freqs), (
            f"Unexpected frequency values in frequency datasets: {actual - expected_freqs}"
        )

    def test_every_dataset_is_in_at_least_one_category(self, con):
        """Every dataset must be an event dataset, a frequency dataset, or both."""
        orphans = con.execute(
            "SELECT COUNT(*) FROM kg_datasets "
            "WHERE NOT is_event_dataset AND NOT is_frequency_dataset"
        ).fetchone()[0]
        assert orphans == 0, f"{orphans} datasets belong to neither category"


class TestVariablesTable:
    def test_table_exists(self, con):
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        assert "kg_variables" in tables

    def test_required_columns(self, con):
        cols = {r[0] for r in con.execute("DESCRIBE kg_variables").fetchall()}
        expected = {
            "variable_id",
            "dataset_id",
            "variable_name",
            "label_",
            "description",
            "data_type",
            "definition",
            "is_tijdstip",
        }
        assert expected.issubset(cols), f"Missing columns: {expected - cols}"

    def test_variable_id_is_unique(self, con):
        total = con.execute("SELECT COUNT(*) FROM kg_variables").fetchone()[0]
        distinct = con.execute(
            "SELECT COUNT(DISTINCT variable_id) FROM kg_variables"
        ).fetchone()[0]
        assert total == distinct, "variable_id must be unique"

    def test_foreign_key_integrity(self, con):
        """Every variable must reference an existing dataset."""
        orphans = con.execute(
            "SELECT COUNT(*) FROM kg_variables v "
            "LEFT JOIN kg_datasets d ON v.dataset_id = d.dataset_id "
            "WHERE d.dataset_id IS NULL"
        ).fetchone()[0]
        assert orphans == 0, f"{orphans} variables reference non-existent datasets"

    def test_no_null_identifiers(self, con):
        nulls = con.execute(
            "SELECT COUNT(*) FROM kg_variables "
            "WHERE variable_id IS NULL OR dataset_id IS NULL OR variable_name IS NULL"
        ).fetchone()[0]
        assert nulls == 0

    def test_event_datasets_have_tijdstip_variables(self, con):
        """Every event dataset must have at least one tijdstip variable."""
        missing = con.execute(
            "SELECT COUNT(*) FROM kg_datasets d "
            "WHERE d.is_event_dataset "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM kg_variables v "
            "  WHERE v.dataset_id = d.dataset_id AND v.is_tijdstip"
            ")"
        ).fetchone()[0]
        assert missing == 0, (
            f"{missing} event datasets have no tijdstip variables"
        )

    def test_tijdstip_variables_only_in_event_datasets(self, con):
        """Tijdstip variables should only appear in event datasets."""
        bad = con.execute(
            "SELECT COUNT(*) FROM kg_variables v "
            "JOIN kg_datasets d ON v.dataset_id = d.dataset_id "
            "WHERE v.is_tijdstip AND NOT d.is_event_dataset"
        ).fetchone()[0]
        assert bad == 0, (
            f"{bad} tijdstip variables found in non-event datasets"
        )

    def test_every_dataset_has_variables(self, con):
        """Every dataset in the DB should have at least one variable."""
        missing = con.execute(
            "SELECT COUNT(*) FROM kg_datasets d "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM kg_variables v WHERE v.dataset_id = d.dataset_id"
            ")"
        ).fetchone()[0]
        assert missing == 0, f"{missing} datasets have no variables"


class TestDataVolume:
    def test_reasonable_dataset_count(self, con):
        """Based on prior exploration, expect at least 200 datasets."""
        count = con.execute("SELECT COUNT(*) FROM kg_datasets").fetchone()[0]
        assert count >= 200, f"Only {count} datasets — expected ≥200"

    def test_reasonable_variable_count(self, con):
        """Each dataset has multiple variables, expect thousands total."""
        count = con.execute("SELECT COUNT(*) FROM kg_variables").fetchone()[0]
        assert count >= 1000, f"Only {count} variables — expected ≥1000"

    def test_event_dataset_count_in_range(self, con):
        """Prior exploration found ~258 event datasets."""
        count = con.execute(
            "SELECT COUNT(*) FROM kg_datasets WHERE is_event_dataset"
        ).fetchone()[0]
        assert 100 <= count <= 500, f"Event dataset count {count} outside expected range"

    def test_tijdstip_variable_count(self, con):
        """Prior exploration found ~818 tijdstip variables."""
        count = con.execute(
            "SELECT COUNT(*) FROM kg_variables WHERE is_tijdstip"
        ).fetchone()[0]
        assert count >= 500, f"Only {count} tijdstip variables — expected ≥500"
