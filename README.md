# Google Trends Scraper

A command-line Python tool that collects Google Trends interest-over-time data for keywords listed in a CSV file and saves the results to another CSV. It is designed for repeatable small-scale research, with configurable collection settings, resumable output, and automated tests.

## Why this project exists

This project started as a script for collecting search-interest data for terms relevant to Puerto Rico. I wanted a repeatable way to collect multiple keywords, keep the results in a format that can be analyzed with pandas or a spreadsheet, and resume a collection without requesting terms that are already in the output file.

## Features

- Reads keywords from a user-selected CSV column.
- Removes blank values and duplicate keywords from the input.
- Configures region, date range, batch size, request pause, and retry count through command-line arguments.
- Saves results as a date-indexed CSV, with one column per keyword.
- Saves after each successful batch so completed batches remain available if a later request fails.
- Can resume by skipping keywords that already have columns in the output file.
- Includes automated tests and a GitHub Actions workflow.

## Requirements

- Python 3.11 or 3.12
- Internet access for live data collection
- Google Trends access from your network

The project uses [`pytrends`](https://github.com/GeneralMills/pytrends), an unofficial interface to Google Trends, and pandas for data handling.

## Installation

Clone the repository and enter its directory:

```bash
git clone https://github.com/YOUR-USERNAME/google-trends-scraper.git
cd google-trends-scraper
```

Create and activate a virtual environment.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

To run the test suite as well, install the development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

## Input format

The input must be a CSV file with a header row. The column containing search terms is selected with `--column`.

Example: `examples/keywords.csv`

```csv
Keyword
Puerto Rico
San Juan
beach tourism
hurricane season
```

Use keywords that you have permission to research and avoid putting private or sensitive information in public example files.

## Usage

Run the example collection with an explicit date range and output path:

```bash
python google_trends_scraper.py \
  --input examples/keywords.csv \
  --column Keyword \
  --output trends_data.csv \
  --geo PR \
  --start-date 2025-10-01 \
  --end-date 2026-10-01
```

The default region is `PR` (Puerto Rico). The start and end dates are required intentionally: every run should state its collection period explicitly, making results easier to reproduce and interpret. Dates must use `YYYY-MM-DD` format.

### Arguments

| Argument | Required | Default | Description |
|---|---:|---|---|
| `--input`, `-i` | Yes | — | Path to input CSV |
| `--column`, `-c` | Yes | — | CSV column containing keywords |
| `--output`, `-o` | Yes | — | Path to output CSV |
| `--geo` | No | `PR` | Google Trends region code; use an empty string for worldwide data if supported by the interface |
| `--start-date` | Yes | — | Start date, inclusive |
| `--end-date` | Yes | — | End date |
| `--batch-size` | No | `5` | Keywords per request, from 1 to 5 |
| `--pause` | No | `5.0` | Seconds between requests and before retrying |
| `--language` | No | `en-US` | Google Trends interface language |
| `--retries` | No | `2` | Additional attempts after a failed request |
| `--log-level` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

See every available option with:

```bash
python google_trends_scraper.py --help
```

## Output

The output CSV has a `date` column and one column per keyword. Dates are sorted in ascending order. Google Trends chooses the data granularity based on the selected period and its own data availability, so rows may represent weeks or another interval rather than individual days.

A simplified example of the shape is shown below. The values are illustrative, not live Google Trends data.

```csv
date,Purely illustrative keyword,Another keyword
2026-01-04,32,71
2026-01-11,41,65
```

The script writes after each successful batch using a temporary file and replacement, reducing the chance of leaving a partially written output file. If the output already exists, keywords with existing columns are skipped. If a collection fails, rerun the same command after the issue is resolved to continue with keywords that have not yet been collected.

## How batching affects interpretation

Google Trends reports normalized interest scores, not the number of searches. Scores are scaled relative to the terms and time range included in a request. Because this tool processes more than five keywords in separate requests, scores from different batches may not be directly comparable. The tool does not add a comparison keyword to attempt to normalize batches. If strict cross-keyword comparisons are important, design a documented calibration strategy and validate it separately before drawing conclusions.

The current resume behavior identifies completed keywords by their output columns. If you change the region or date range, use a new output file to avoid mixing collection settings in one dataset.

## Tests

Tests use mocked `pytrends` responses. They do not send requests to Google Trends, so they are faster and can run offline.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

The suite covers keyword cleanup, missing input columns, response cleanup, retry behavior, merging, batching, output creation, and resume behavior.

## GitHub Actions

The workflow in `.github/workflows/tests.yml` runs the tests on pushes, pull requests, and manual workflow dispatch. After pushing this repository to GitHub, the workflow appears in the **Actions** tab. A green check means the automated test job passed for the configured Python versions.

## Limitations and responsible use

- `pytrends` is unofficial and is not supported or guaranteed by Google. Google may change its behavior, throttle requests, or block collection.
- Retries and pauses reduce request pressure but do not guarantee that requests will succeed. Increase the pause or reduce the batch size if you encounter throttling.
- Google Trends values are normalized interest scores, not absolute search counts.
- Scores from separate keyword batches are not guaranteed to be comparable.
- Resume logic uses existing output column names to identify collected keywords. Use a fresh output file when changing collection parameters.
- This is a small research utility, not a high-availability data pipeline. Inspect results for missing values and unexpected changes before using them in analysis.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).

## Acknowledgments

- [pytrends](https://github.com/GeneralMills/pytrends) for the unofficial Google Trends interface.
- [pandas](https://pandas.pydata.org/) for CSV and tabular data processing.
