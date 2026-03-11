# ODISSEI Knowledge Graph: exploration notes

## SPARQL endpoint

```
https://api.kg.odissei.nl/datasets/odissei/odissei-kg/services/odissei-virtuoso/sparql
```

## Variable node structure

Each dataset (`vi:odisseiVariable`) points to variable nodes that have **two levels** of properties:

### Variable level (specific to a dataset version)
| Predicate | Example value | Description |
|---|---|---|
| `vi:odisseiVariableName` | `ADODatumV` | Actual column name in the dataset |
| `vi:odisseiVariableLabel` | `Datum van adoptie/vestiging` | Human-readable label |
| `vi:odisseiVariableDefinition` | `Als deze datum leeg is dan...` | Variable-level description |
| `vi:odisseiVariableDataType` | `Integer`, `String` | Data type |
| `vi:odisseiVariableVolgnummer` | `6` | Ordering number |
| `vi:odisseiVariableVocabularyURI` | `https://w3id.org/odissei/cv/cbs/...` | Link to vocabulary concept |

### Concept level (abstract, shared across datasets)
| Predicate | Example value | Description |
|---|---|---|
| `vi:odisseiConceptVariableName` | `Tijdstip van vestiging van adoptiekind` | Concept name (human-readable, not a column name) |
| `vi:odisseiConceptVariableDefinition` | `Het tijdstip van vestiging van...` | Concept-level description |
| `vi:odisseiConceptVariableID` | (identifier) | Concept identifier |
| `vi:odisseiConceptVariableGroeppad` | (path) | Group path |
| `vi:odisseiConceptVariableObjecttype` | (type) | Object type |
| `vi:odisseiConceptVariableValidFrom` | `1995-01-01` | Valid-from date |

## Dataset node properties (selected)

| Predicate | Description |
|---|---|
| `dct:alternative` | Short dataset name, e.g. `ADOPTIEKINDEREN` (258 unique values = one per data design) |
| `dct:title` | Full human-readable title, e.g. `Kenmerken van adoptiekinderen` |
| `schema:name` | Dataset name |
| `dct:subject` | Subject classification |
| `citation:dsDescription` | Dataset description |
| `CBSMetadata#GeldigVanaf` / `GeldigTot` | Validity period |

## Key takeaway for extending the query

To get the column name and description of the tijdstip variable, use:
- `vi:odisseiVariableName` for the **actual column name** (e.g., `ADODatumV`)
- `vi:odisseiVariableDefinition` for the **description**
- `dct:title` for the **full dataset name**

These are **variable-level** properties, not concept-level.
