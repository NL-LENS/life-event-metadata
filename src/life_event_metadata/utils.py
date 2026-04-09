"""Shared utilities for the teamnl-events-dataset notebooks."""

from __future__ import annotations
import subprocess
from pathlib import Path
import polars as pl
from SPARQLWrapper import JSON
from SPARQLWrapper import SPARQLWrapper
from life_event_metadata.constants import KG_ENDPOINT


def get_root() -> Path:
    """Get directory root. For use in notebooks."""
    return Path(
        subprocess.run(
            ["/usr/bin/git", "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip(),
    )


def wide_print(df: pl.DataFrame, n_rows: int | None = None) -> None:
    """Print a Polars DataFrame with full column content."""
    cfg = {"fmt_str_lengths": 1000, "tbl_width_chars": 1000}
    if n_rows is not None:
        cfg["tbl_rows"] = n_rows
    with pl.Config(**cfg):
        print(df)  # noqa: T201


def run_query(query: str) -> pl.DataFrame:
    """Run a SPARQL query against the ODISSEI KG and return a Polars DataFrame."""
    sparql = SPARQLWrapper(KG_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    bindings = results["results"]["bindings"]
    if not bindings:
        return pl.DataFrame()
    cols = results["head"]["vars"]
    data = {c: [row.get(c, {}).get("value", None) for row in bindings] for c in cols}
    return pl.DataFrame(data)
