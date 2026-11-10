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
- Do not overload the server. Queries with large result sets will fail.
- When querying for substrings, search for both Dutch and English components.
