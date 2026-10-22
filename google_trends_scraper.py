"""Collect Google Trends interest-over-time data for keywords in a CSV file.

This tool uses pytrends, an unofficial Google Trends interface. Scores from
separate batches are normalized independently by Google Trends and should not
be treated as directly comparable across batches.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

LOGGER = logging.getLogger("google_trends_scraper")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect Google Trends interest-over-time data from a CSV of keywords."
    )
    parser.add_argument("--input", "-i", required=True, type=Path, help="Input CSV path.")
    parser.add_argument(
        "--column", "-c", required=True, help="Name of the CSV column containing keywords."
    )
    parser.add_argument("--output", "-o", required=True, type=Path, help="Output CSV path.")
    parser.add_argument(
        "--geo", default="PR", help="Google Trends geographic code (default: PR, Puerto Rico)."
    )
    parser.add_argument(
        "--start-date", required=True, help="Start date, YYYY-MM-DD (inclusive)."
    )
    parser.add_argument(
        "--end-date", required=True, help="End date, YYYY-MM-DD."
    )
    parser.add_argument(
        "--batch-size", type=int, default=5,
        help="Number of keywords per request, from 1 to 5 (default: 5)."
    )
    parser.add_argument(
        "--pause", type=float, default=5.0,
        help="Seconds to wait between requests; must be non-negative (default: 5)."
    )
    parser.add_argument(
        "--language", default="en-US", help="Google Trends interface language (default: en-US)."
    )
    parser.add_argument(
        "--retries", type=int, default=2,
        help="Additional attempts after a failed request (default: 2)."
    )
    parser.add_argument(
        "--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO",
        help="Logging verbosity (default: INFO)."
    )
    args = parser.parse_args(argv)

    if args.batch_size < 1 or args.batch_size > 5:
        parser.error("--batch-size must be between 1 and 5 because Google Trends accepts at most five terms per request.")
    if args.pause < 0:
        parser.error("--pause must be zero or greater.")
    if args.retries < 0:
        parser.error("--retries must be zero or greater.")
    try:
        start = pd.Timestamp(args.start_date)
        end = pd.Timestamp(args.end_date)
    except (TypeError, ValueError):
        parser.error("Dates must be valid dates in YYYY-MM-DD format.")
    if start > end:
        parser.error("--start-date must be on or before --end-date.")
    # Keep the CLI contract unambiguous and avoid accepting timestamps accidentally.
    if start.strftime("%Y-%m-%d") != args.start_date or end.strftime("%Y-%m-%d") != args.end_date:
        parser.error("Dates must use YYYY-MM-DD format.")
    return args


def load_keywords(input_path: Path, column: str) -> list[str]:
    """Load unique, non-empty keywords from the requested CSV column."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")
    try:
        table = pd.read_csv(input_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Input CSV is empty: {input_path}") from exc
    if column not in table.columns:
        available = ", ".join(map(str, table.columns)) or "(none)"
        raise ValueError(f"Column {column!r} was not found. Available columns: {available}")

    keywords: list[str] = []
    seen: set[str] = set()
    for value in table[column].dropna():
        keyword = str(value).strip()
        if keyword and keyword not in seen:
            keywords.append(keyword)
            seen.add(keyword)
    if not keywords:
        raise ValueError(f"No non-empty keywords found in column {column!r}.")
    return keywords


def collect_batch(
    client: Any,
    keywords: list[str],
    geo: str,
    start_date: str,
    end_date: str,
    retries: int = 2,
    pause: float = 5.0,
) -> pd.DataFrame:
    """Fetch one batch and return a DataFrame with a date column."""
    timeframe = f"{start_date} {end_date}"
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            client.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop="")
            result = client.interest_over_time()
            if result is None or result.empty:
                raise ValueError("Google Trends returned no data for this batch.")
            result = result.drop(columns=["isPartial"], errors="ignore").reset_index()
            if "date" not in result.columns:
                # pytrends normally returns a DatetimeIndex named 'date'.
                first_column = result.columns[0]
                result = result.rename(columns={first_column: "date"})
            missing = [keyword for keyword in keywords if keyword not in result.columns]
            if missing:
                raise ValueError(
                    "Google Trends response did not include expected keyword column(s): "
                    + ", ".join(repr(item) for item in missing)
                )
            result["date"] = pd.to_datetime(result["date"], errors="raise").dt.strftime("%Y-%m-%d")
            return result[["date", *keywords]]
        except Exception as exc:  # pytrends may raise several transport/API exception types
            last_error = exc
            if attempt < retries:
                LOGGER.warning(
                    "Request failed (%s/%s): %s. Retrying in %.1f seconds.",
                    attempt + 1, retries + 1, exc, pause,
                )
                if pause:
                    time.sleep(pause)
    raise RuntimeError(f"Could not collect keywords {keywords!r}: {last_error}") from last_error


def merge_batch(existing: pd.DataFrame, batch: pd.DataFrame) -> pd.DataFrame:
    """Merge collected data by date, preserving existing values and columns."""
    if existing.empty:
        merged = batch.copy()
    else:
        merged = existing.merge(batch, on="date", how="outer", suffixes=("", "__new"))
        for column in batch.columns:
            if column == "date":
                continue
            new_column = f"{column}__new"
            if new_column in merged.columns:
                merged[column] = merged[column].combine_first(merged[new_column])
                merged = merged.drop(columns=[new_column])
    merged["date"] = pd.to_datetime(merged["date"], errors="raise")
    return merged.sort_values("date").assign(date=lambda frame: frame["date"].dt.strftime("%Y-%m-%d")).reset_index(drop=True)


def save_csv_atomically(data: pd.DataFrame, output_path: Path) -> None:
    """Write output to a temporary file before replacing the destination."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", suffix=".tmp",
            dir=output_path.parent, delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            data.to_csv(temp_file, index=False)
        os.replace(temp_name, output_path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def run(args: argparse.Namespace, client: TrendReq | None = None) -> int:
    """Run the collection workflow. Returns the number of newly collected keywords."""
    keywords = load_keywords(args.input, args.column)
    if args.output.exists():
        try:
            existing = pd.read_csv(args.output, dtype={"date": str})
        except pd.errors.EmptyDataError:
            existing = pd.DataFrame(columns=["date"])
        if "date" not in existing.columns:
            raise ValueError(f"Existing output file must contain a 'date' column: {args.output}")
        existing_keywords = [column for column in existing.columns if column != "date"]
    else:
        existing = pd.DataFrame(columns=["date"])
        existing_keywords = []

    pending = [keyword for keyword in keywords if keyword not in set(existing_keywords)]
    if not pending:
        LOGGER.info("All input keywords already exist in %s. Nothing to do.", args.output)
        return 0

    if client is None:
        try:
            from pytrends.request import TrendReq
        except ImportError as exc:
            raise RuntimeError(
                "pytrends is not installed. Install dependencies with: python -m pip install -r requirements.txt"
            ) from exc
        client = TrendReq(hl=args.language)
    collected = 0
    batches = [pending[index:index + args.batch_size] for index in range(0, len(pending), args.batch_size)]
    for index, batch_keywords in enumerate(batches, start=1):
        LOGGER.info("Collecting batch %s/%s (%s keyword(s))", index, len(batches), len(batch_keywords))
        batch = collect_batch(
            client=client,
            keywords=batch_keywords,
            geo=args.geo,
            start_date=args.start_date,
            end_date=args.end_date,
            retries=args.retries,
            pause=args.pause,
        )
        existing = merge_batch(existing, batch)
        save_csv_atomically(existing, args.output)
        collected += len(batch_keywords)
        LOGGER.info("Saved %s rows and %s keyword(s) to %s", len(existing), len(existing.columns) - 1, args.output)
        if index < len(batches) and args.pause:
            time.sleep(args.pause)
    return collected


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
    )
    try:
        count = run(args)
    except (FileNotFoundError, ValueError, RuntimeError, OSError, pd.errors.ParserError) as exc:
        LOGGER.error("%s", exc)
        return 1
    LOGGER.info("Finished. Newly collected keywords: %s", count)
    LOGGER.warning(
        "Google Trends scores are normalized per request. Scores from separate batches may not be directly comparable."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
