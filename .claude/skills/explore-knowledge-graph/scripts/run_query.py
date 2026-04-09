import argparse
from life_event_metadata.utils import run_query
from life_event_metadata.utils import wide_print


def parse_args() -> argparse.Namespace:
    """Parse arguments."""
    parser = argparse.ArgumentParser(
        prog="run_query", description="Runs a query against the Odissei knowledge graph and prints the result."
    )
    parser.add_argument("query_string")
    parser.add_argument("--nrow", default=100, help="Number of rows to print. Use -1 for printing all rows.")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run_query(args.query_string)
    wide_print(result, n_rows=args.nrow)
