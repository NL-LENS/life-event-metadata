---
name: explore-knowledge-graph
description: Explore the Odissei knowledge graph. Use when user asks
about content of the knowledge graph or is building queries on the knowledge graph.
---


# Explore knowledge graph

## Instructions

### Step 0: Activate the python virtual environment


### Step 1: Know your way

The endpoint is:

```
https://api.kg.odissei.nl/datasets/odissei/odissei-kg/services/odissei-virtuoso/sparql
```

Prefixes are:

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

### Step 2: Structure of the graph

The schema is not fully documented. Use the exploration queries below to discover
new predicates and classes. What we know:

#### Datasets
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

#### Variables
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

#### Known vocabulary URIs
- Person identifier: `<https://w3id.org/odissei/cv/cbs/variableThesaurus/c650ad27af3f9e2b081c2b2f3698ae9eeb2a502f919b2f220d9f5b29afd6f337e>`

#### CBS-provided keywords
- They are richer than the ELSST ones
- From a `dataset` node, they can be reached as follows:
    ```sqarql
    ?dataset citation:topicClassification ?topicClassNode .
    ?topicClassNode citation:topicClassValue ?topicClass .
    ```
- If the user asks for the ELSST nodes, point them towards the CBS-provided keywords.

#### Other enrichment nodes
- Frequency of use: 3 categories based on number of projects using them. As of 2026, not most up to date
but still a good approximation.

### Step 3: Run queries

Run `python scripts/run_query.py {query}` to query the KG. You need to build the
query string yourself; the examples in `references/examples.md` may help.

### Step 4: Iterate or return to the user

If you cannot answer the user's question, update the query and go back to step
3. Otherwise, continue on the task.

### Further reference

See references/examples.md for some query examples and references/tips.md for query
construction tips.
