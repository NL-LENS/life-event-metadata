"""Tool for querying the ODISSEI Knowledge Graph.

Wraps run_query with automatic prefix injection, URI compaction,
and LLM-friendly result formatting.
"""

import polars as pl
from utils import run_query

PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "schema": "http://schema.org/",
    "dct": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "citation": "https://dataverse.org/schema/citation/",
    "vi": "https://portal.odissei.nl/schema/variableInformation#",
    "ss": "https://portal.odissei.nl/schema/socialscience#",
    "enrich": "https://portal.odissei.nl/schema/enrichments#",
}

# Reverse mapping: full URI → prefix:
_URI_TO_PREFIX = {uri: f"{name}:" for name, uri in PREFIXES.items()}


def _inject_prefixes(sparql: str) -> str:
    """Prepend any missing prefix declarations to a SPARQL query."""
    lines = []
    declared = {line.split()[1].rstrip(":") for line in sparql.splitlines()
                if line.strip().lower().startswith("prefix ")}
    for name, uri in PREFIXES.items():
        if name not in declared and f"{name}:" in sparql:
            lines.append(f"prefix {name}: <{uri}>")
    if lines:
        return "\n".join(lines) + "\n" + sparql
    return sparql


def _compact_uris(df: pl.DataFrame) -> pl.DataFrame:
    """Replace full URIs with prefixed forms (e.g. dct:title)."""
    for col in df.columns:
        if df[col].dtype == pl.Utf8:
            for uri, short in _URI_TO_PREFIX.items():
                df = df.with_columns(pl.col(col).str.replace(uri, short, literal=True))
    return df


def query_kg(sparql: str, limit: int = 100, compact: bool = True) -> str:
    """Run a SPARQL query and return results formatted for an LLM.

    Parameters
    ----------
    sparql : str
        SPARQL query. Missing prefix declarations are auto-injected.
    limit : int
        Max rows to include in the output. The full count is always reported.
    compact : bool
        Replace full URIs with prefixed short forms.

    Returns
    -------
    str
        CSV with a header summarising shape and schema.
    """
    query = _inject_prefixes(sparql)
    df = run_query(query)

    if df.is_empty():
        return "Query returned 0 rows."

    parts = [f"Shape: {df.shape[0]} rows x {df.shape[1]} cols"]

    if compact:
        df = _compact_uris(df)

    if df.shape[0] <= limit:
        parts.append(df.write_csv())
    else:
        parts.append(f"First {limit} of {df.shape[0]} rows:")
        parts.append(df.head(limit).write_csv())

    return "\n".join(parts)
