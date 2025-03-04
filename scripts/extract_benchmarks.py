import argparse
import datetime
import json
import os
import pathlib

import polars as pl


def _parse_datetime(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s).astimezone(datetime.UTC)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--input", "-i", required=True)
    arg_parser.add_argument("--output", "-o", required=True)
    arg_parser.add_argument("--testbed", "-t", required=True)
    args = arg_parser.parse_args()

    with open(args.input) as f:
        benchmarks_json = json.load(f)

    timestamp = _parse_datetime(benchmarks_json["datetime"])
    commit_sha = benchmarks_json["commit_info"]["id"]
    commit_branch = benchmarks_json["commit_info"]["branch"]
    commit_timestamp = _parse_datetime(benchmarks_json["commit_info"]["time"])
    commit_author_timestamp = _parse_datetime(
        benchmarks_json["commit_info"]["author_time"]
    )
    python_version = benchmarks_json["machine_info"]["python_version"]

    rows = []
    for benchmark in benchmarks_json["benchmarks"]:
        rows.append(
            {
                "testbed": args.testbed,
                "timestamp": timestamp.isoformat(),
                "commit_sha": commit_sha,
                "commit_branch": commit_branch,
                "commit_timestamp": commit_timestamp.isoformat(),
                "commit_author_timestamp": commit_author_timestamp.isoformat(),
                "python_version": python_version,
                "benchmark_name": benchmark["name"],
                "benchmark_fullname": benchmark["fullname"],
                "benchmark_mean_s": round(benchmark["stats"]["mean"], 9),
                "benchmark_stddev_s": round(benchmark["stats"]["stddev"], 9),
                "benchmark_median_s": round(benchmark["stats"]["median"], 9),
                "benchmark_iqr_s": round(benchmark["stats"]["iqr"], 9),
                "benchmark_rounds": benchmark["stats"]["rounds"],
                "benchmark_iterations": benchmark["stats"]["iterations"],
            }
        )

    df = pl.DataFrame(data=rows, orient="row")

    output_path = pathlib.Path(args.output)
    os.makedirs(output_path.parent, exist_ok=True)
    df.write_csv(output_path)


if __name__ == "__main__":
    main()