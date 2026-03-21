<!-- v0.0.1 · 2026-03-16 — Bump this version when adding predicates, fixing queries, or changing patterns. -->
# ODISSEI Knowledge Graph — Skill Reference

## Endpoint

```
https://api.kg.odissei.nl/datasets/odissei/odissei-kg/services/odissei-virtuoso/sparql
```

## Prefixes

```sparql
prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
prefix schema:  <http://schema.org/>
prefix dct:     <http://purl.org/dc/terms/>
prefix skos:    <http://www.w3.org/2004/02/skos/core#>
prefix owl:     <http://www.w3.org/2002/07/owl#>
prefix citation: <https://dataverse.org/schema/citation/>
prefix vi:      <https://portal.odissei.nl/schema/variableInformation#>
prefix ss:      <https://portal.odissei.nl/schema/socialscience#>
prefix enrich:  <https://portal.odissei.nl/schema/enrichments#>
```

## Graph structure (known so far)

The schema is not fully documented. Use the exploration queries below to discover
new predicates and classes. What we know:

### Datasets
- Type: `schema:Dataset`
- `dct:title` — full title (e.g. "Kenmerken van adoptiekinderen")
- `dct:alternative` — short name (e.g. "ADOPTIEKINDEREN")
- `schema:name` — dataset name
- `dct:subject` — subject classification
- `dct:creator` — links to a creator node with `citation:authorName`
- `citation:dsDescription` — dataset description
- `ss:frequencyOfDataCollection` — e.g. "Jaar", "Maand", "Stand", "Kalenderjaar"
- `citation:keyword` — links to keyword nodes with `citation:keywordValue`
- `enrich:enrichedElsstClassification` — links to ELSST concept nodes (type `skos:Concept`)
- `vi:odisseiVariable` — links to variable nodes
- `CBSMetadata#GeldigVanaf` / `CBSMetadata#GeldigTot` — validity period

### Variables
Two levels of properties exist on variable nodes:

**Variable level** (concrete, dataset-specific):
- `vi:odisseiVariableName` — column name in the dataset (e.g. "ADODatumV")
- `vi:odisseiVariableLabel` — human-readable label (e.g. "Datum van adoptie/vestiging")
- `vi:odisseiVariableDefinition` — description of the variable
- `vi:odisseiVariableDataType` — e.g. "Integer", "String"
- `vi:odisseiVariableVolgnummer` — ordering number
- `vi:odisseiVariableVocabularyURI` — links to a SKOS concept with `skos:prefLabel`

**Concept level** (abstract, shared across datasets — same node, flat properties):
- `vi:odisseiConceptVariableName` — human-readable concept name
- `vi:odisseiConceptVariableDefinition` — concept description
- `vi:odisseiConceptVariableID` — concept identifier
- `vi:odisseiConceptVariableGroeppad` — group path
- `vi:odisseiConceptVariableObjecttype` — object type
- `vi:odisseiConceptVariableValidFrom` — date (e.g. "1995-01-01")

Both levels are flat properties on the same variable node. For example, a single
variable node for ADOPTIEKINDEREN has both `vi:odisseiVariableName "ADODatumV"`
and `vi:odisseiConceptVariableDefinition "Als deze datum leeg is dan bet..."`.

### ELSST enrichment nodes
- Type: `skos:Concept`
- `dct:identifier` — URN identifier
- `dct:modified` — last modification date
- `owl:priorVersion` — link to previous ELSST version

### Known vocabulary URIs
- Person identifier: `<https://w3id.org/odissei/cv/cbs/variableThesaurus/c650ad27af3f9e2b081c2b2f3698ae9eeb2a502f919b2f220d9f5b29afd6f337e>`

### CBS-provided keywords
- They are richer than the ELSST ones
- From a `dataset` node, they can be reached as follows:
    ```sqarql
    ?dataset citation:topicClassification ?topicClassNode .
    ?topicClassNode citation:topicClassValue ?topicClass .
    ```
- If the user asks for the ELSST nodes, point them towards the CBS-provided keywords.

### Other enrichment nodes
- Frequency of use: 3 categories based on number of projects using them. As of 2026, not most up to date 
but still a good approximation.

## Example queries

### 1. Explore all predicates on a dataset node

Useful for discovering new properties on any dataset.

Replace `<DATASET_ALT_TITLE>` with the short name (e.g. "ADOPTIEKINDEREN").

```sparql
prefix dct: <http://purl.org/dc/terms/>

SELECT ?p ?o WHERE {
  ?dataset dct:alternative "<DATASET_ALT_TITLE>" .
  ?dataset ?p ?o .
}
LIMIT 200
```

### 2. Explore all predicates on variable nodes of a dataset

```sparql
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix dct: <http://purl.org/dc/terms/>

SELECT ?var ?p ?o WHERE {
  ?dataset dct:alternative "<DATASET_ALT_TITLE>" .
  ?dataset vi:odisseiVariable ?var .
  ?var ?p ?o .
}
LIMIT 200
```

### 3. List CBS datasets with title and frequency

```sparql
prefix schema: <http://schema.org/>
prefix dct: <http://purl.org/dc/terms/>
prefix citation: <https://dataverse.org/schema/citation/>
prefix ss: <https://portal.odissei.nl/schema/socialscience#>

SELECT DISTINCT ?altTitle ?datasetTitle ?frequency WHERE {
  VALUES ?authorName { 'Centraal Bureau voor Statistiek' 'Centraal Bureau voor de Statistiek (CBS)' }
  ?dataset dct:creator ?creator .
  ?creator citation:authorName ?authorName .
  ?dataset a schema:Dataset .
  ?dataset dct:alternative ?altTitle .
  ?dataset dct:title ?datasetTitle .
  ?dataset ss:frequencyOfDataCollection ?frequency .
}
ORDER BY ?altTitle
```

### 4. Find datasets with a person identifier and tijdstip variable (full detail)

```sparql
prefix schema: <http://schema.org/>
prefix dct: <http://purl.org/dc/terms/>
prefix citation: <https://dataverse.org/schema/citation/>
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?datasetTitle ?altTitle ?tijdstipColName ?tijdstipVarLabel ?tijdstipDescription WHERE {
  VALUES ?authorName { 'Centraal Bureau voor Statistiek' 'Centraal Bureau voor de Statistiek (CBS)' }
  ?dataset dct:creator ?creator .
  ?creator citation:authorName ?authorName .
  ?dataset a schema:Dataset .
  ?dataset dct:alternative ?altTitle .
  ?dataset dct:title ?datasetTitle .

  ?dataset vi:odisseiVariable ?var1 .
  ?var1 vi:odisseiVariableVocabularyURI ?var1VocabURI .
  FILTER(?var1VocabURI = <https://w3id.org/odissei/cv/cbs/variableThesaurus/c650ad27af3f9e2b081c2b2f3698ae9eeb2a502f919b2f220d9f5b29afd6f337e>)

  ?dataset vi:odisseiVariable ?tijdstipVar .
  ?tijdstipVar ?p ?varLabel .
  FILTER(isLiteral(?varLabel) && CONTAINS(LCASE(STR(?varLabel)), LCASE("Tijdstip")))
  ?tijdstipVar vi:odisseiVariableVocabularyURI ?tijdstipVocabURI .
  ?tijdstipVocabURI skos:prefLabel ?tijdstipVarLabel .
  ?tijdstipVar vi:odisseiVariableName ?tijdstipColName .
  ?tijdstipVar vi:odisseiVariableDefinition ?tijdstipDescription .
}
ORDER BY ?altTitle
```

### 5. Frequency distribution across CBS datasets

```sparql
prefix ss: <https://portal.odissei.nl/schema/socialscience#>
prefix dct: <http://purl.org/dc/terms/>
prefix citation: <https://dataverse.org/schema/citation/>

SELECT ?frequency (COUNT(DISTINCT ?dataset) AS ?count) WHERE {
  VALUES ?authorName { 'Centraal Bureau voor Statistiek' 'Centraal Bureau voor de Statistiek (CBS)' }
  ?dataset dct:creator ?creator .
  ?creator citation:authorName ?authorName .
  ?dataset ss:frequencyOfDataCollection ?frequency .
}
GROUP BY ?frequency
ORDER BY DESC(?count)
```

### 6. Top keywords across CBS datasets

```sparql
prefix dct: <http://purl.org/dc/terms/>
prefix citation: <https://dataverse.org/schema/citation/>

SELECT ?keyword (COUNT(DISTINCT ?dataset) AS ?count) WHERE {
  VALUES ?authorName { 'Centraal Bureau voor Statistiek' 'Centraal Bureau voor de Statistiek (CBS)' }
  ?dataset dct:creator ?creator .
  ?creator citation:authorName ?authorName .
  ?dataset citation:keyword ?kwNode .
  ?kwNode citation:keywordValue ?keyword .
}
GROUP BY ?keyword
ORDER BY DESC(?count)
LIMIT 30
```

### 7. Explore ELSST enrichment concepts on a dataset

```sparql
prefix dct: <http://purl.org/dc/terms/>
prefix enrich: <https://portal.odissei.nl/schema/enrichments#>

SELECT DISTINCT ?p ?o WHERE {
  ?dataset dct:alternative "<DATASET_ALT_TITLE>" .
  ?dataset enrich:enrichedElsstClassification ?elsstNode .
  ?elsstNode ?p ?o .
}
LIMIT 50
```

### 8. List all variables of a dataset with name, label, and definition

```sparql
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix dct: <http://purl.org/dc/terms/>
prefix skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?varName ?varLabel ?varDefinition WHERE {
  ?dataset dct:alternative "<DATASET_ALT_TITLE>" .
  ?dataset vi:odisseiVariable ?var .
  ?var vi:odisseiVariableName ?varName .
  OPTIONAL { ?var vi:odisseiVariableDefinition ?varDefinition . }
  OPTIONAL {
    ?var vi:odisseiVariableVocabularyURI ?vocabURI .
    ?vocabURI skos:prefLabel ?varLabel .
  }
}
ORDER BY ?varName
```

### 9. Discover all distinct predicates used on dataset nodes (schema exploration)

```sparql
prefix schema: <http://schema.org/>

SELECT DISTINCT ?p WHERE {
  ?dataset a schema:Dataset .
  ?dataset ?p ?o .
}
ORDER BY ?p
```

### 10. Discover all distinct predicates used on variable nodes (schema exploration)

```sparql
prefix schema: <http://schema.org/>
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>

SELECT DISTINCT ?p WHERE {
  ?dataset a schema:Dataset .
  ?dataset vi:odisseiVariable ?var .
  ?var ?p ?o .
}
ORDER BY ?p
```

### 11. List all distinct authors/creators

```sparql
prefix dct: <http://purl.org/dc/terms/>
prefix citation: <https://dataverse.org/schema/citation/>

SELECT ?authorName (COUNT(DISTINCT ?dataset) AS ?count) WHERE {
  ?dataset dct:creator ?creator .
  ?creator citation:authorName ?authorName .
}
GROUP BY ?authorName
ORDER BY DESC(?count)
```

## Tips for query construction

- **Always use `DISTINCT`** -- the graph contains many duplicate triples.
- **Use `LIMIT`** when exploring -- unbounded queries can be slow.
- **Filter by creator** for CBS-only data — CBS has **two author names** in the graph:
  - `'Centraal Bureau voor Statistiek'` (2800 datasets)
  - `'Centraal Bureau voor de Statistiek (CBS)'` (256 datasets)
  To match both, use a `VALUES` clause or `FILTER(CONTAINS(...))`:
  ```sparql
  VALUES ?authorName { 'Centraal Bureau voor Statistiek' 'Centraal Bureau voor de Statistiek (CBS)' }
  ?dataset dct:creator ?creator .
  ?creator citation:authorName ?authorName .
  ```
  See query 11 for all authors.
- **Person identifier filter** restricts to datasets with person-level records (the vocabulary URI above).
- **`OPTIONAL`** is needed for properties that not all nodes have (e.g. variable definitions).
- The endpoint is Virtuoso-based, so full SPARQL 1.1 is supported including `VALUES`, `GROUP BY`, `HAVING`, sub-queries, and property paths.
