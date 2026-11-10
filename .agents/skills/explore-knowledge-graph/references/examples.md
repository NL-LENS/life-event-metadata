
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
