"""Shared utilities for the teamnl-events-dataset notebooks."""

import subprocess
from pathlib import Path

import polars as pl

ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    ).stdout.strip()
)


def wide_print(df, tbl_rows=None):
    """Print a Polars DataFrame with full column content."""
    cfg = {"fmt_str_lengths": 1000, "tbl_width_chars": 1000}
    if tbl_rows is not None:
        cfg["tbl_rows"] = tbl_rows
    with pl.Config(**cfg):
        print(df)


def run_query(query: str) -> pl.DataFrame:
    """Run a SPARQL query against the ODISSEI KG and return a Polars DataFrame."""
    from SPARQLWrapper import SPARQLWrapper, JSON

    endpoint = "https://api.kg.odissei.nl/datasets/odissei/odissei-kg/services/odissei-virtuoso/sparql"
    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    bindings = results["results"]["bindings"]
    if not bindings:
        return pl.DataFrame()
    cols = results["head"]["vars"]
    data = {c: [row.get(c, {}).get("value", None) for row in bindings] for c in cols}
    return pl.DataFrame(data)
