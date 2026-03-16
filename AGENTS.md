
### Query on the Odissei knowledge graph / Odissei portal

Goal: create a dictionary of events occurring in administrative datasets. 
The Odissei portal / knowledge graph has metadata about all datasets 
from CBS, the data provider. Below is a query that finds all "events" in 
dataset.

The following query creates the csv file in `data/designs-with-events_preflabel.csv`:

```sqarql
prefix schema: <http://schema.org/>
prefix dct: <http://purl.org/dc/terms/>
prefix citation: <https://dataverse.org/schema/citation/>
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?altTitle ?var1Label ?tijdstipVarLabel WHERE {
  ?creator citation:authorName 'Centraal Bureau voor Statistiek' .
  ?dataset dct:creator ?creator .
  ?dataset a schema:Dataset .
  ?dataset dct:alternative ?altTitle .
  ?dataset vi:odisseiVariable ?var1 .
  ?var1 vi:odisseiVariableVocabularyURI ?var1VocabURI .
  ?var1VocabURI skos:prefLabel ?var1Label .
  FILTER(?var1VocabURI = <https://w3id.org/odissei/cv/cbs/variableThesaurus/c650ad27af3f9e2b081c2b2f3698ae9eeb2a502f919b2f220d9f5b29afd6f337e>)
  ?dataset vi:odisseiVariable ?tijdstipVar .
  ?tijdstipVar ?p ?varLabel .
  FILTER(isLiteral(?varLabel) && CONTAINS(LCASE(STR(?varLabel)), LCASE("Tijdstip")))
  ?tijdstipVar vi:odisseiVariableVocabularyURI ?tijdstipVocabURI .
  ?tijdstipVocabURI skos:prefLabel ?tijdstipVarLabel .
}
ORDER BY ?altTitle
```

The following query creates the csv file in `data/data-designs-extended.csv`:

```sparql
prefix schema: <http://schema.org/>
prefix dct: <http://purl.org/dc/terms/>
prefix citation: <https://dataverse.org/schema/citation/>
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?datasetTitle ?altTitle ?tijdstipColName ?tijdstipVarLabel ?tijdstipDescription WHERE {
  ?creator citation:authorName 'Centraal Bureau voor Statistiek' .
  ?dataset dct:creator ?creator .
  ?dataset a schema:Dataset .
  ?dataset dct:alternative ?altTitle .
  ?dataset dct:title ?datasetTitle .

  # Person identifier variable
  ?dataset vi:odisseiVariable ?var1 .
  ?var1 vi:odisseiVariableVocabularyURI ?var1VocabURI .
  FILTER(?var1VocabURI = <https://w3id.org/odissei/cv/cbs/variableThesaurus/c650ad27af3f9e2b081c2b2f3698ae9eeb2a502f919b2f220d9f5b29afd6f337e>)

  # Tijdstip variable
  ?dataset vi:odisseiVariable ?tijdstipVar .
  ?tijdstipVar ?p ?varLabel .
  FILTER(isLiteral(?varLabel) && CONTAINS(LCASE(STR(?varLabel)), LCASE("Tijdstip")))
  ?tijdstipVar vi:odisseiVariableVocabularyURI ?tijdstipVocabURI .
  ?tijdstipVocabURI skos:prefLabel ?tijdstipVarLabel .

  # Column name (actual column in the dataset, e.g. ADODatumV)
  ?tijdstipVar vi:odisseiVariableName ?tijdstipColName .

  # Description of the tijdstip variable
  ?tijdstipVar vi:odisseiVariableDefinition ?tijdstipDescription .
}
ORDER BY ?altTitle
```



