"""
Collects benchmarks data from a set of input CSVs and appends the data
to an output CSV.
"""

import argparse
import glob
import os
import pathlib

import polars as pl


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--input", "-i", required=True)
    arg_parser.add_argument("--output", "-o", required=True)
    args = arg_parser.parse_args()

    dfs = []

    output_path = pathlib.Path(args.output)
    if output_path.exists():
        dfs.append(pl.read_csv(output_path))
    else:
        os.makedirs(output_path.parent, exist_ok=True)

    for uncollected_file in glob.glob(f"{args.input.rstrip('/')}/*"):
        dfs.append(pl.read_csv(uncollected_file))

    df = pl.concat(dfs)
    df.write_csv(output_path)


if __name__ == "__main__":
    main()

