KG_ENDPOINT = "https://api.kg.odissei.nl/datasets/odissei/odissei-kg/services/odissei-virtuoso/sparql"

KG_PREFIXES = {
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
_URI_TO_PREFIX = {uri: f"{name}:" for name, uri in KG_PREFIXES.items()}

_CBS_PREFIXES = """
prefix CBS: <https://portal.odissei.nl/schema/CBSMetadata#>
"""

# General concept URI for "Persoon-id" (Person ID) - top-level concept
# Using skos:broader* with this URI captures all narrower concepts including
# various RINPERSOON variants (RINPERSOON, RINPERSOONHKW, RINPERSOONSHKW, etc.)
_RINPERSOON_URI = "https://w3id.org/odissei/cv/cbs/variableThesaurus/v0b01e41080202085"

_FREQUENCY_DATASET_VALUES = ("Jaar", "Kalenderjaar", "Niet eenduidig", "Stand", "Maand", "Studiejaar", "Schooljaar")
