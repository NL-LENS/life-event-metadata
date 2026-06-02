"""Tool for querying the ODISSEI Knowledge Graph.

Wraps run_query with automatic prefix injection, URI compaction,
and LLM-friendly result formatting.
"""

from __future__ import annotations
import polars as pl
from tqdm import tqdm
from .constants import _CBS_PREFIXES
from .constants import _FREQUENCY_DATASET_VALUES
from .constants import _RINPERSOON_URI
from .constants import _URI_TO_PREFIX
from .constants import KG_PREFIXES
from .utils import run_query


def _inject_prefixes(sparql: str) -> str:
    """Prepend any missing prefix declarations to a SPARQL query."""
    lines = []
    declared = {
        line.split()[1].rstrip(":") for line in sparql.splitlines() if line.strip().lower().startswith("prefix ")
    }
    for name, uri in KG_PREFIXES.items():
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


def _datasets_base_metadata_query(extra_filter: str = "", require_frequency: bool = False) -> str:
    """Build a SELECT query for CBS+RINPERSOON datasets with an extra WHERE clause.

    Parameters
    ----------
    extra_filter : str
        Additional SPARQL patterns to include in the WHERE clause.
    require_frequency : bool
        If True, make ss:frequencyOfDataCollection a required pattern.
        If False (default), it remains OPTIONAL.
    """
    if require_frequency:
        freq_pattern = "?dataset ss:frequencyOfDataCollection ?frequency ."
    else:
        freq_pattern = "OPTIONAL { ?dataset ss:frequencyOfDataCollection ?frequency }"

    return _CBS_PREFIXES + _inject_prefixes(f"""
    SELECT DISTINCT ?dataset ?shortTitle ?title ?description ?publicationDate
                    ?validFrom ?validUntil ?frequency ?samplingProcedure
    WHERE {{
        VALUES ?authorName {{
            'Centraal Bureau voor Statistiek'
            'Centraal Bureau voor de Statistiek (CBS)'
        }}
        ?dataset dct:creator ?creator .
        ?creator citation:authorName ?authorName .
        ?dataset a schema:Dataset .
        ?dataset vi:odisseiVariable ?personVar .
        ?personVar vi:odisseiVariableVocabularyURI ?vocabURI .
        # Match any concept that is a narrower concept of the general Persoon-id
        ?vocabURI skos:broader* <{_RINPERSOON_URI}> .

        ?dataset dct:alternative ?shortTitle .
        ?dataset dct:title ?title .
        OPTIONAL {{
            ?dataset citation:dsDescription ?descNode .
            ?descNode citation:dsDescriptionValue ?description
        }}
        OPTIONAL {{ ?dataset dct:issued ?publicationDate }}
        OPTIONAL {{ ?dataset CBS:GeldigVanaf ?validFrom }}
        OPTIONAL {{ ?dataset CBS:GeldigTot ?validUntil }}
        {freq_pattern}
        OPTIONAL {{ ?dataset ss:samplingProcedure ?samplingProcedure }}

        {extra_filter}
    }}
    """)


def extract_datasets_metadata() -> pl.DataFrame:
    """Extract CBS datasets with RINPERSOON identifier from ODISSEI KG.

    Two queries define the result set:
    - tijdstip datasets: have at least one variable with "tijdstip" in the definition
    - frequency datasets: published at a qualifying frequency

    Every row in the returned DataFrame belongs to at least one category.
    Boolean flags (isTijdstipDataset, isFrequencyDataset) are set in Python based
    on which query returned each dataset.
    """
    freq_values = ", ".join(f'"{v}"' for v in _FREQUENCY_DATASET_VALUES)
    event_query = _datasets_base_metadata_query("""
        ?dataset vi:odisseiVariable ?tijdstipVar .
        ?tijdstipVar ?p ?varLabel .
        FILTER(isLiteral(?varLabel)
               && CONTAINS(
                   LCASE(STR(?varLabel)),
                   LCASE("Tijdstip")
                )
        )
        ?tijdstipVar vi:odisseiVariableVocabularyURI ?tijdstipVocabURI .
        ?tijdstipVocabURI skos:prefLabel ?tijdstipVarLabel .
    """)

    freq_query = _datasets_base_metadata_query(
        f"FILTER(?frequency IN ({freq_values}))",
        require_frequency=True,
    )

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
        ?personVar vi:odisseiVariableVocabularyURI ?vocabURI .
        # Match any concept that is a narrower concept of the general Persoon-id
        ?vocabURI skos:broader* <{_RINPERSOON_URI}> .
        ?dataset citation:topicClassification ?topicClassNode .
        ?topicClassNode citation:topicClassValue ?kw .
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

    result_df = pl.concat(frames).unique(subset=["dataset"], keep="first")

    result_df = result_df.with_columns(
        [
            pl.col("dataset").is_in(list(event_uris)).alias("isTijdstipDataset"),
            pl.col("dataset").is_in(list(freq_uris)).alias("isFrequencyDataset"),
        ],
    )

    if not kw_df.is_empty():
        result_df = result_df.join(kw_df, on="dataset", how="left")
        result_df = result_df.with_columns(pl.col("keywords").str.split(", ").alias("keywords"))
    else:
        result_df = result_df.with_columns(pl.lit(None).cast(pl.List(pl.Utf8)).alias("keywords"))

    return result_df


def extract_variables_metadata(dataset_uris: list[str], chunk_size: int = 50) -> pl.DataFrame:
    """Extract variable metadata for the given dataset URIs from the ODISSEI KG.

    Queries are chunked to avoid oversized SPARQL requests.
    Returns a DataFrame with one row per variable, including isTijdstip flag,
    isPersonIdentifier flag, count of predicates, and list of tijdstip predicates.
    """
    chunks = [dataset_uris[i : i + chunk_size] for i in range(0, len(dataset_uris), chunk_size)]

    frames: list[pl.DataFrame] = []
    for chunk in tqdm(chunks):
        values = " ".join(f"<{uri}>" for uri in chunk)
        query = _inject_prefixes(f"""
        SELECT ?dataset ?var
               (SAMPLE(?name) AS ?name)
               (SAMPLE(?label) AS ?label)
               (SAMPLE(?description) AS ?description)
               (SAMPLE(?dataType) AS ?dataType)
               (SAMPLE(?definition) AS ?definition)
               (SAMPLE(?validFrom) AS ?validFrom)
               (SAMPLE(?vocabLabel) AS ?vocabLabel)
               (MAX(?isTijdstipRow) AS ?isTijdstip)
               (MAX(?isPersonIdentifierRow) AS ?isPersonIdentifier)
               (COUNT(DISTINCT ?p) AS ?numPredicates)
               (GROUP_CONCAT(DISTINCT IF(?isTijdstipRow = 1, STR(?p), ""); separator=", ")
                    AS ?tijdstipPredicates)
        WHERE {{
             VALUES ?dataset {{ {values} }}
             ?dataset vi:odisseiVariable ?var .
             ?var ?p ?o .
             OPTIONAL {{ ?var vi:odisseiVariableName ?name }}
             OPTIONAL {{ ?var vi:odisseiVariableLabel ?label }}
             OPTIONAL {{ ?var vi:odisseiVariableDefinition ?description }}
             OPTIONAL {{ ?var vi:odisseiVariableDataType ?dataType }}
             OPTIONAL {{ ?var vi:odisseiConceptVariableDefinition ?definition }}
             OPTIONAL {{ ?var vi:odisseiConceptVariableValidFrom ?validFrom }}
             OPTIONAL {{
                ?var vi:odisseiVariableVocabularyURI ?vocabURI .
                ?vocabURI skos:prefLabel ?vocabLabel .
              }}
             OPTIONAL {{
                ?var vi:odisseiVariableVocabularyURI ?pidVocabURI .
                ?pidVocabURI skos:broader <{_RINPERSOON_URI}> .
              }}
              BIND(IF(isLiteral(?o) && CONTAINS(LCASE(STR(?o)), "tijdstip")
                      && BOUND(?vocabLabel), 1, 0) AS ?isTijdstipRow)
              BIND(IF(BOUND(?pidVocabURI), 1, 0) AS ?isPersonIdentifierRow)
          }}
         GROUP BY ?dataset ?var""")
        chunk_df = run_query(query)
        if not chunk_df.is_empty():
            chunk_df = chunk_df.with_columns(
                (pl.col("isTijdstip").cast(pl.Int32) == 1).alias("isTijdstip"),
                (pl.col("isPersonIdentifier").cast(pl.Int32) == 1).alias("isPersonIdentifier"),
            )
            # Clean up tijdstipPredicates: remove empty strings, keep as list
            chunk_df = chunk_df.with_columns(
                pl.col("tijdstipPredicates")
                .str.split(", ")
                .list.eval(pl.element().filter(pl.element() != ""))
                .alias("tijdstipPredicates")
            )
            frames.append(chunk_df)

    if not frames:
        return pl.DataFrame()

    return pl.concat(frames)


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
    result_df = run_query(query)

    if result_df.is_empty():
        return "Query returned 0 rows."

    parts = [f"Shape: {result_df.shape[0]} rows x {result_df.shape[1]} cols"]

    if compact:
        result_df = _compact_uris(result_df)

    if result_df.shape[0] <= limit:
        parts.append(result_df.write_csv())
    else:
        parts.append(f"First {limit} of {result_df.shape[0]} rows:")
        parts.append(result_df.head(limit).write_csv())

    return "\n".join(parts)
