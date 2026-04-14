"""Tests for the final DuckDB database schema and data integrity."""

import operator
from pathlib import Path
from typing import Any
from typing import Callable
import duckdb
import pytest
from life_event_metadata.constants import _FREQUENCY_DATASET_VALUES

DB_PATH = Path("data/event_datasets.duckdb")


@pytest.fixture(scope="session")
def con():
    """Provide read-only connection to built database."""
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


class TestDatasetsTable:
    """Test creation of datasets table."""

    def test_table_exists(self, con: duckdb.DuckDBPyConnection):
        """Test that table exists."""
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        assert "kg_datasets" in tables

    def test_required_columns(self, con: duckdb.DuckDBPyConnection):
        """Test that table has required columns."""
        cols = {r[0] for r in con.execute("DESCRIBE kg_datasets").fetchall()}
        expected = {
            "dataset_id",
            "title",
            "alt_title",
            "publication_date",
            "valid_from",
            "valid_until",
            "frequency",
            "keywords",
            "is_tijdstip_dataset",
            "is_frequency_dataset",
        }
        assert expected.issubset(cols), f"Missing columns: {expected - cols}"

    def test_dataset_id_is_primary_key(self, con: duckdb.DuckDBPyConnection):
        """Test that dataset_id is the primary key."""
        total = con.execute("SELECT COUNT(*) FROM kg_datasets").fetchone()[0]
        distinct = con.execute(
            "SELECT COUNT(DISTINCT dataset_id) FROM kg_datasets",
        ).fetchone()[0]
        assert total == distinct, "dataset_id must be unique"

    @pytest.mark.parametrize(
        ("filter_list", "op"),
        [
            (["dataset_id", "alt_title"], operator.eq),
            (["valid_from"], operator.eq),
            (["is_tijdstip_dataset", "is_frequency_dataset"], operator.eq),
        ],
        ids=[
            "dataset_and_title-not-null",
            "valid_from-not-null",
            "dataset-type-not-null",
        ],
    )
    def test_nulls(self, filter_list: list, op: Callable[[Any, Any], bool], con: duckdb.DuckDBPyConnection):
        """Test columns against NULL values."""
        where_clause = self._make_where_null(filter_list)
        # ruff: disable[S608]
        count = con.execute(
            f"SELECT COUNT(*) FROM kg_datasets WHERE {where_clause}",
        ).fetchone()[0]
        # ruff: enable[S608]
        assert op(count, 0)

    def _make_where_null(self, columns: list) -> str:
        """Make sql-injection safe 'where x is null' string."""
        clause = ""
        allowed_columns = ["dataset_id", "alt_title", "valid_from", "is_tijdstip_dataset", "is_frequency_dataset"]
        for i, col in enumerate(columns):
            if col not in allowed_columns:
                msg = "Invalid columns: %s", col
                raise ValueError(msg)
            if i == 0:
                clause += f" {col} IS NULL"
                continue
            clause += f" OR {col} IS NULL"
        return clause

    def test_frequency_values_when_flagged(self, con: duckdb.DuckDBPyConnection):
        """Frequency datasets must have a frequency in the expected set."""
        expected_freqs = _FREQUENCY_DATASET_VALUES
        rows = con.execute(
            "SELECT DISTINCT frequency FROM kg_datasets WHERE is_frequency_dataset",
        ).fetchall()
        actual = {r[0] for r in rows if r[0] is not None}
        assert actual.issubset(expected_freqs), (
            f"Unexpected frequency values in frequency datasets: {actual - expected_freqs}"
        )

    def test_every_dataset_is_in_at_least_one_category(self, con: duckdb.DuckDBPyConnection):
        """Every dataset must be an tijdstip dataset, a frequency dataset, or both."""
        orphans = con.execute(
            "SELECT COUNT(*) FROM kg_datasets WHERE NOT is_tijdstip_dataset AND NOT is_frequency_dataset",
        ).fetchone()[0]
        assert orphans == 0, f"{orphans} datasets belong to neither category"


class TestVariablesTable:
    """Tests for the kg_variables table."""

    def test_table_exists(self, con: duckdb.DuckDBPyConnection):
        """Test that table exists."""
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        assert "kg_variables" in tables

    def test_required_columns(self, con: duckdb.DuckDBPyConnection):
        """Test that table has expected columns."""
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
            "valid_from",
            "vocab_label",
            "num_predicates",
            "tijdstip_predicates",
        }
        assert expected.issubset(cols), f"Missing columns: {expected - cols}"

    def test_variable_id_is_unique(self, con: duckdb.DuckDBPyConnection):
        """Test that the variable_id is unique."""
        total = con.execute("SELECT COUNT(*) FROM kg_variables").fetchone()[0]
        distinct = con.execute(
            "SELECT COUNT(DISTINCT variable_id) FROM kg_variables",
        ).fetchone()[0]
        assert total == distinct, "variable_id must be unique"

    def test_foreign_key_integrity(self, con: duckdb.DuckDBPyConnection):
        """Every variable must reference an existing dataset."""
        orphans = con.execute(
            "SELECT COUNT(*) FROM kg_variables v "
            "LEFT JOIN kg_datasets d ON v.dataset_id = d.dataset_id "
            "WHERE d.dataset_id IS NULL",
        ).fetchone()[0]
        assert orphans == 0, f"{orphans} variables reference non-existent datasets"

    def test_no_null_identifiers(self, con: duckdb.DuckDBPyConnection):
        """Test that all variable ids have a name and a dataset_id."""
        nulls = con.execute(
            "SELECT COUNT(*) FROM kg_variables "
            "WHERE variable_id IS NULL OR dataset_id IS NULL OR variable_name IS NULL",
        ).fetchone()[0]
        assert nulls == 0

    def test_tijdstip_datasets_have_tijdstip_variables(self, con: duckdb.DuckDBPyConnection):
        """Every tijdstip dataset must have at least one tijdstip variable."""
        missing = con.execute(
            "SELECT COUNT(*) FROM kg_datasets d "
            "WHERE d.is_tijdstip_dataset "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM kg_variables v "
            "  WHERE v.dataset_id = d.dataset_id AND v.is_tijdstip"
            ")",
        ).fetchone()[0]
        assert missing == 0, f"{missing} tijdstip datasets have no tijdstip variables"

    def test_tijdstip_variables_only_in_tijdstip_datasets(self, con: duckdb.DuckDBPyConnection):
        """Tijdstip variables should only appear in tijdstip datasets."""
        bad = con.execute(
            "SELECT COUNT(*) FROM kg_variables v "
            "JOIN kg_datasets d ON v.dataset_id = d.dataset_id "
            "WHERE v.is_tijdstip AND NOT d.is_tijdstip_dataset",
        ).fetchone()[0]
        assert bad == 0, f"{bad} tijdstip variables found in non-tijdstip datasets"

    def test_every_dataset_has_variables(self, con: duckdb.DuckDBPyConnection):
        """Every dataset in the DB should have at least one variable."""
        missing = con.execute(
            "SELECT COUNT(*) FROM kg_datasets d "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM kg_variables v WHERE v.dataset_id = d.dataset_id"
            ")",
        ).fetchone()[0]
        assert missing == 0, f"{missing} datasets have no variables"


class TestDataVolume:
    """Test volume against pre-existing expected volumes."""

    def test_reasonable_dataset_count(self, con: duckdb.DuckDBPyConnection):
        """Based on prior exploration, expect at least 200 datasets."""
        count = con.execute("SELECT COUNT(distinct alt_title) FROM kg_datasets").fetchone()[0]
        n_expected = 258
        assert count >= n_expected, f"Only {count} datasets — expected >={n_expected}"

    def test_reasonable_variable_count(self, con: duckdb.DuckDBPyConnection):
        """Each dataset has multiple variables, expect thousands total."""
        count = con.execute("SELECT COUNT(distinct variable_name) FROM kg_variables").fetchone()[0]
        n_expected = 1000
        assert count >= n_expected, f"Only {count} variables — expected >={n_expected}"

    def test_tijdstip_dataset_count_in_range(self, con: duckdb.DuckDBPyConnection):
        """Prior exploration found ~258 tijdstip datasets."""
        count = con.execute("SELECT COUNT(*) FROM kg_datasets WHERE is_tijdstip_dataset").fetchone()[0]
        n_high = 500
        n_low = 258
        assert n_low <= count <= n_high, f"tijdstip dataset count {count} outside expected range"

    def test_tijdstip_variable_count(self, con: duckdb.DuckDBPyConnection):
        """Prior exploration found 516 tijdstip variables."""
        count = con.execute(
            "SELECT COUNT(distinct label_) FROM kg_variables WHERE is_tijdstip",
        ).fetchone()[0]
        n_expected = 516
        assert count >= n_expected, f"Only {count} tijdstip variables — expected {n_expected}"
