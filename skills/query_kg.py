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


_CBS_PREFIXES = """
prefix CBS: <https://portal.odissei.nl/schema/CBSMetadata#>
"""

_RINPERSOON_URI = (
    "https://w3id.org/odissei/cv/cbs/variableThesaurus/"
    "c650ad27af3f9e2b081c2b2f3698ae9eeb2a502f919b2f220d9f5b29afd6f337e"
)

_FREQUENCY_DATASET_VALUES = ("Jaar", "Kalenderjaar", "Niet eenduidig", "Stand", "Maand")


def _datasets_base_metadata_query(extra_filter: str) -> str:
    """Build a SELECT query for CBS+RINPERSOON datasets with an extra WHERE clause."""
    return _CBS_PREFIXES + _inject_prefixes(f"""
    SELECT DISTINCT ?dataset ?shortTitle ?title ?publicationDate
                    ?validFrom ?validUntil ?frequency ?doi ?samplingProcedure
    WHERE {{
        VALUES ?authorName {{
            'Centraal Bureau voor Statistiek'
            'Centraal Bureau voor de Statistiek (CBS)'
        }}
        ?dataset dct:creator ?creator .
        ?creator citation:authorName ?authorName .
        ?dataset a schema:Dataset .
        ?dataset vi:odisseiVariable ?personVar .
        ?personVar vi:odisseiVariableVocabularyURI <{_RINPERSOON_URI}> .

        ?dataset dct:alternative ?shortTitle .
        ?dataset dct:title ?title .
        OPTIONAL {{ ?dataset dct:issued ?publicationDate }}
        OPTIONAL {{ ?dataset CBS:GeldigVanaf ?validFrom }}
        OPTIONAL {{ ?dataset CBS:GeldigTot ?validUntil }}
        OPTIONAL {{ ?dataset ss:frequencyOfDataCollection ?frequency }}
        OPTIONAL {{ ?dataset citation:datasetPersistentId ?doi }}
        OPTIONAL {{ ?dataset ss:samplingProcedure ?samplingProcedure }}

        {extra_filter}
    }}
    """)


def extract_datasets_metadata() -> pl.DataFrame:
    """Extract CBS datasets with RINPERSOON identifier from ODISSEI KG.

    Two queries define the result set:
    - event datasets: have at least one variable with "tijdstip" in the definition
    - frequency datasets: published at a qualifying frequency

    Every row in the returned DataFrame belongs to at least one category.
    Boolean flags (isEventDataset, isFrequencyDataset) are set in Python based
    on which query returned each dataset.
    """
    freq_values = ", ".join(f'"{v}"' for v in _FREQUENCY_DATASET_VALUES)

    event_query = _datasets_base_metadata_query(f"""
        ?dataset vi:odisseiVariable ?tijdstipVar .
        {{ ?tijdstipVar vi:odisseiVariableName ?_val }}
        UNION
        {{ ?tijdstipVar vi:odisseiVariableLabel ?_val }}
        UNION
        {{ ?tijdstipVar vi:odisseiVariableDefinition ?_val }}
        FILTER(CONTAINS(LCASE(STR(?_val)), "tijdstip"))
    """)

    freq_query = _datasets_base_metadata_query(f"""
        ?dataset ss:frequencyOfDataCollection ?frequency .
        FILTER(?frequency IN ({freq_values}))
    """)

    keywords_query = _CBS_PREFIXES + _inject_prefixes(f"""
    SELECT ?dataset (GROUP_CONCAT(DISTINCT ?kw; separator=", ") AS ?keywords)
    WHERE {{
        VALUES ?authorName {{
            'Centraal Bureau voor Statistiek'
            'Centraal Bureau voor de Statistiek (CBS)'
        }}
        ?dataset dct:creator ?creator .
        ?creator citation:authorName ?authorName .
        ?dataset a schema:Dataset .
        ?dataset vi:odisseiVariable ?personVar .
        ?personVar vi:odisseiVariableVocabularyURI <{_RINPERSOON_URI}> .
        ?dataset citation:keyword ?kwNode .
        ?kwNode citation:keywordValue ?kw .
    }}
    GROUP BY ?dataset
    """)

    event_df = run_query(event_query)
    freq_df = run_query(freq_query)
    kw_df = run_query(keywords_query)

    event_uris: set[str] = set(event_df["dataset"].to_list()) if not event_df.is_empty() else set()
    freq_uris: set[str] = set(freq_df["dataset"].to_list()) if not freq_df.is_empty() else set()

    # Union of both result sets; metadata columns are identical so concat + deduplicate
    frames = []
    if not event_df.is_empty():
        frames.append(event_df)
    if not freq_df.is_empty():
        frames.append(freq_df)

    df = pl.concat(frames).unique(subset=["dataset"], keep="first")

    df = df.with_columns([
        pl.col("dataset").is_in(list(event_uris)).alias("isEventDataset"),
        pl.col("dataset").is_in(list(freq_uris)).alias("isFrequencyDataset"),
    ])

    if not kw_df.is_empty():
        df = df.join(kw_df, on="dataset", how="left")
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias("keywords"))

    return df


def extract_variables_metadata(dataset_uris: list[str], chunk_size: int = 50) -> pl.DataFrame:
    """Extract variable metadata for the given dataset URIs from the ODISSEI KG.

    Queries are chunked to avoid oversized SPARQL requests.
    Returns a DataFrame with one row per variable, including is_tijdstip flag.
    """
    chunks = [
        dataset_uris[i : i + chunk_size]
        for i in range(0, len(dataset_uris), chunk_size)
    ]

    frames: list[pl.DataFrame] = []
    for chunk in chunks:
        values = " ".join(f"<{uri}>" for uri in chunk)
        query = _inject_prefixes(f"""
        SELECT ?dataset ?var ?name ?label ?description ?dataType ?definition ?validFrom
        WHERE {{
            VALUES ?dataset {{ {values} }}
            ?dataset vi:odisseiVariable ?var .
            ?var vi:odisseiVariableName ?name .
            OPTIONAL {{ ?var vi:odisseiVariableLabel ?label }}
            OPTIONAL {{ ?var vi:odisseiVariableDefinition ?description }}
            OPTIONAL {{ ?var vi:odisseiVariableDataType ?dataType }}
            OPTIONAL {{ ?var vi:odisseiConceptVariableDefinition ?definition }}
            OPTIONAL {{ ?var vi:odisseiConceptVariableValidFrom ?validFrom }}
        }}
        """)
        chunk_df = run_query(query)
        if not chunk_df.is_empty():
            frames.append(chunk_df)

    if not frames:
        return pl.DataFrame()

    df = pl.concat(frames)

    # is_tijdstip: any text column contains "tijdstip" (case-insensitive)
    text_cols = ["name", "label", "description", "definition"]
    tijdstip_expr = pl.lit(False)
    for col in text_cols:
        tijdstip_expr = tijdstip_expr | (
            pl.col(col).str.to_lowercase().str.contains("tijdstip").fill_null(False)
        )
    df = df.with_columns(tijdstip_expr.alias("is_tijdstip"))
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
