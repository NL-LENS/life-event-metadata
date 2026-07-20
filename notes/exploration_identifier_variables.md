# Exploration: Identifier variables in the CBS variable thesaurus

**Date:** 2026-04-28
**Goal:** Find all "identifier" variables in the CBS variable thesaurus and determine whether there is a general way to discover relational (non-RINPERSOON) datasets that can be linked to person-level datasets.

---

## 1. Is there a single umbrella "identifier" concept?

**Query:** look for the ancestors of the existing `Persoon-id` URI to see whether there is a parent concept grouping all identifiers.

```sparql
prefix skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?concept ?label ?broader ?broaderLabel WHERE {
  <https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080202085> skos:broader* ?concept .
  OPTIONAL { ?concept skos:prefLabel ?label }
  OPTIONAL { ?concept skos:broader ?broader . ?broader skos:prefLabel ?broaderLabel }
}
```

**Finding:** `Persoon-id` has no `skos:broader` parent — it is already a top-level concept. There is **no umbrella "identifier" concept** in the thesaurus. Each domain-specific identifier (person, household, firm, dwelling, …) is its own independent top-level concept.

---

## 2. Catalogue of top-level identifier concepts

**Query:** find all top-level concepts (no `skos:broader`) that also have `skos:narrower` children and whose label ends in `-id`, contains `nummer`, or matches `identificat`.

```sparql
prefix skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?concept ?label (COUNT(DISTINCT ?narrower) AS ?narrowerCount) WHERE {
  ?concept skos:inScheme <https://w3id.org/odissei/cv/cbs/variableThesaurus/> .
  ?concept skos:prefLabel ?label .
  ?concept skos:narrower ?narrower .
  FILTER NOT EXISTS { ?concept skos:broader ?x }
  FILTER(
    REGEX(STR(?label), '-id$', 'i') ||
    REGEX(STR(?label), '^rin', 'i') ||
    CONTAINS(LCASE(STR(?label)), 'identificat') ||
    CONTAINS(LCASE(STR(?label)), 'koppelsleutel') ||
    CONTAINS(LCASE(STR(?label)), 'sleutelwaarde')
  )
}
GROUP BY ?concept ?label
ORDER BY ?label
```

**Selected findings** (116 concepts total; key ones for relational analysis):

| Label | URI | Narrower count |
|---|---|---|
| `Persoon-id` | `v0b01e41080202085` | 140 |
| `Gemeentecode` | `v0b01e41080043d86` | 18 |
| `Huishouden-id` | `v0b01e41080302f7528` | 14 |
| `Verblijfplaats-id` | `v0b01e410803b1956` | 12 |
| `Baan-id` | `v0b01e41080216926` | 4 |
| `Woningeigenaar-id` | `v0b01e41080806a64` | 4 |
| `Pand-id` | `v0b01e41080516ffb` | 3 |
| `Eigenaar-id verblijfsobject` | `v0b01e41080311cf2` | 5 |
| `Bedrijfs-id` | `v0b01e4108033304e` | 2 |
| `Woning-id` | `v0b01e41080422afb` | 2 |
| `Verblijfsobject-id` | `v0b01e41080806a62` | 2 |
| `KVK-nummer` | `v0b01e410807fe52a` | 1 |

There is no single `skos:broader*` traversal that captures all identifiers. The `REGEX '-id$'` label pattern is a practical heuristic but misses `Gemeentecode`, `KVK-nummer`, etc.

---

## 3. Finding relational datasets via bridge identifiers

### Motivation

Datasets in the KG that carry `Persoon-id` (RINPERSOON) may also carry a second identifier (e.g. `RINOBJECTNUMMER`). That second identifier can link to other datasets that hold the same identifier but have **no** RINPERSOON. These are "object-level" datasets (housing, firms, geography) that become reachable once a person is linked to an object.

### Step 1 — Inspect a source dataset

Example: find all variables and their thesaurus concepts for EIGENDOMTAB.

```sparql
prefix skos: <http://www.w3.org/2004/02/skos/core#>
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix dct: <http://purl.org/dc/terms/>
SELECT ?varName ?vocabURI ?vocabLabel WHERE {
  ?dataset dct:alternative 'EIGENDOMTAB' .
  ?dataset vi:odisseiVariable ?var .
  ?var vi:odisseiVariableName ?varName .
  OPTIONAL {
    ?var vi:odisseiVariableVocabularyURI ?vocabURI .
    ?vocabURI skos:prefLabel ?vocabLabel .
  }
}
ORDER BY ?varName
```

EIGENDOMTAB contains `RINOBJECTNUMMER` mapped to vocab concept *Rinobjectnummer*. Tracing its ancestors:

```sparql
prefix skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?ancestor ?label WHERE {
  <https://w3id.org/odissei/cv/cbs/variableThesaurus/c308b5d617132a6dac1c89f5d3b2a55b0d927ae5d2a5729307f9eb7b6cf2dcc98>
    skos:broader* ?ancestor .
  OPTIONAL { ?ancestor skos:prefLabel ?label }
}
```

Result: `Rinobjectnummer` rolls up to **`Verblijfplaats-id`** (`v0b01e410803b1956`).

### Step 2 — Find non-RINPERSOON identifier concepts in selected source datasets

```sparql
prefix skos: <http://www.w3.org/2004/02/skos/core#>
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix dct: <http://purl.org/dc/terms/>
prefix schema: <http://schema.org/>
prefix citation: <https://dataverse.org/schema/citation/>

SELECT DISTINCT ?altTitle ?otherTopConcept ?otherTopLabel WHERE {
  VALUES ?altTitle { 'EIGENDOMTAB' 'BAANKENMERKENBUS' 'GBAADRESOBJECTBUS' 'SPOLIS' }
  ?dataset dct:alternative ?altTitle .
  ?dataset a schema:Dataset .

  ?dataset vi:odisseiVariable ?otherVar .
  ?otherVar vi:odisseiVariableVocabularyURI ?otherVocabURI .
  ?otherVocabURI skos:broader* ?otherTopConcept .
  FILTER NOT EXISTS { ?otherTopConcept skos:broader ?x }
  ?otherTopConcept skos:prefLabel ?otherTopLabel .

  FILTER NOT EXISTS {
    ?otherTopConcept skos:broader*
      <https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080202085>
  }
  FILTER (
    REGEX(STR(?otherTopLabel), '-id$', 'i') ||
    REGEX(STR(?otherTopLabel), 'nummer$', 'i') ||
    REGEX(STR(?otherTopLabel), '^.*code$', 'i')
  )
}
ORDER BY ?altTitle ?otherTopLabel
```

| Source dataset | Bridge concept | Bridge concept URI |
|---|---|---|
| EIGENDOMTAB | `Verblijfplaats-id` | `v0b01e410803b1956` |
| BAANKENMERKENBUS | `Baan-id` | `v0b01e41080216926` |
| BAANKENMERKENBUS | `Loonheffingennummer` | `v0b01e41080221ca7` |
| GBAADRESOBJECTBUS | `Verblijfplaats-id` | `v0b01e410803b1956` |

### Step 3 — Find datasets reachable via each bridge (without RINPERSOON)

```sparql
prefix skos: <http://www.w3.org/2004/02/skos/core#>
prefix vi: <https://portal.odissei.nl/schema/variableInformation#>
prefix dct: <http://purl.org/dc/terms/>
prefix schema: <http://schema.org/>
prefix citation: <https://dataverse.org/schema/citation/>

SELECT DISTINCT ?bridgeConceptLabel ?linkedAltTitle WHERE {
  VALUES (?bridgeConcept ?bridgeConceptLabel) {
    (<https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e410803b1956>  'Verblijfplaats-id')
    (<https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080216926>  'Baan-id')
    (<https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080302f7528> 'Huishouden-id')
    (<https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e4108033304e>  'Bedrijfs-id')
    (<https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080311cf2>  'Eigenaar-id verblijfsobject')
    (<https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080043d86>  'Gemeentecode')
  }

  VALUES ?authorName {
    'Centraal Bureau voor Statistiek'
    'Centraal Bureau voor de Statistiek (CBS)'
  }
  ?linked dct:creator ?creator .
  ?creator citation:authorName ?authorName .
  ?linked a schema:Dataset .
  ?linked dct:alternative ?linkedAltTitle .

  ?linked vi:odisseiVariable ?bridgeVar .
  ?bridgeVar vi:odisseiVariableVocabularyURI ?bridgeVocabURI .
  ?bridgeVocabURI skos:broader* ?bridgeConcept .

  FILTER NOT EXISTS {
    ?linked vi:odisseiVariable ?personVar .
    ?personVar vi:odisseiVariableVocabularyURI ?personVocabURI .
    ?personVocabURI skos:broader*
      <https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080202085> .
  }
}
ORDER BY ?bridgeConceptLabel ?linkedAltTitle
```

---

## 4. Results

| Bridge concept | Datasets reachable (no RINPERSOON) | Count |
|---|---|---|
| `Verblijfplaats-id` | BAGWOZTAB, EIGENDOMTAB, EIGENDOMWOZBAGTAB, EIGENDOMWOZTAB, ENERGIEVERBRUIKTAB, ENERGIEVERBRUIKMAANDTAB, LEEGSTANDMONITOR, NABIJHEID* suite (8), OBJECTWONINGTAB, TRANSACTIES_KOOPWONINGEN, VSL* suite (6), WOONBASE* suite (2), … | 42 |
| `Gemeentecode` | ABR, BIBLIOTHEKEN, BOUWVERG, GIA, GIR, LOCATUS, POLSJONG, VT_* suite (7), WOZ, … | 42 |
| `Bedrijfs-id` | B2110C_OPH, WVNEDVRACHT | 2 |
| `Eigenaar-id verblijfsobject` | EIGENAARTAB, EIGENDOMTAB | 2 |
| `Baan-id` | *(none)* | 0 |
| `Huishouden-id` | *(none)* | 0 |

### Observations

- **`Verblijfplaats-id` is the richest bridge** — 42 housing/spatial/energy datasets are reachable from any RINPERSOON dataset that carries `RINOBJECTNUMMER`. EIGENDOMWOZBAGTAB is confirmed in this set.
- **`Gemeentecode` links to aggregate/area datasets** (municipality statistics, youth care, fire service, etc.). These are geographic joins rather than individual-level record links.
- **`Baan-id` and `Huishouden-id` are person-centric** — every CBS dataset in the KG that carries these identifiers also carries RINPERSOON, so no purely object-level employment or household datasets exist in the KG.
- **EIGENDOMTAB itself has no RINPERSOON in the KG** — it is object-centric (owner ID + object ID). The expected linkage chain is: RINPERSOON dataset → EIGENDOMTAB (via `Eigenaar-id verblijfsobject`) → EIGENDOMWOZBAGTAB (via `Verblijfplaats-id`).
- A `REGEX '-id$'` label filter is a practical but incomplete heuristic for finding identifier concepts; `Gemeentecode` and `KVK-nummer` are notable misses.
