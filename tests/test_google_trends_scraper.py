from argparse import Namespace
from pathlib import Path

import pandas as pd
import pytest

import google_trends_scraper as scraper


def make_args(tmp_path: Path, input_csv: Path, output_csv: Path, **overrides) -> Namespace:
    values = dict(
        input=input_csv,
        column="Keyword",
        output=output_csv,
        geo="PR",
        start_date="2025-01-01",
        end_date="2025-12-31",
        batch_size=2,
        pause=0,
        language="en-US",
        retries=0,
        log_level="ERROR",
    )
    values.update(overrides)
    return Namespace(**values)


class FakeTrends:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def build_payload(self, keywords, **kwargs):
        self.calls.append((list(keywords), kwargs))

    def interest_over_time(self):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def trends_frame(values):
    frame = pd.DataFrame(values)
    frame.index = pd.to_datetime(["2025-01-05", "2025-01-12"])
    frame.index.name = "date"
    frame["isPartial"] = False
    return frame


def test_load_keywords_strips_blanks_and_deduplicates(tmp_path):
    path = tmp_path / "keywords.csv"
    pd.DataFrame({"Keyword": [" cats ", "", None, "dogs", "cats"]}).to_csv(path, index=False)
    assert scraper.load_keywords(path, "Keyword") == ["cats", "dogs"]


def test_load_keywords_reports_missing_column(tmp_path):
    path = tmp_path / "keywords.csv"
    pd.DataFrame({"Other": ["cats"]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="was not found"):
        scraper.load_keywords(path, "Keyword")


def test_collect_batch_removes_partial_column_and_formats_dates():
    fake = FakeTrends([trends_frame({"cats": [12, 34]})])
    result = scraper.collect_batch(fake, ["cats"], "PR", "2025-01-01", "2025-12-31", pause=0)
    assert list(result.columns) == ["date", "cats"]
    assert result["date"].tolist() == ["2025-01-05", "2025-01-12"]
    assert fake.calls[0][0] == ["cats"]
    assert fake.calls[0][1]["geo"] == "PR"


def test_collect_batch_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda _: None)
    fake = FakeTrends([RuntimeError("temporary error"), trends_frame({"cats": [1, 2]})])
    result = scraper.collect_batch(fake, ["cats"], "PR", "2025-01-01", "2025-12-31", retries=1, pause=0)
    assert result["cats"].tolist() == [1, 2]
    assert len(fake.calls) == 2


def test_collect_batch_raises_after_retries():
    fake = FakeTrends([RuntimeError("service unavailable")])
    with pytest.raises(RuntimeError, match="Could not collect keywords"):
        scraper.collect_batch(fake, ["cats"], "PR", "2025-01-01", "2025-12-31", retries=0, pause=0)


def test_merge_batch_preserves_existing_values_and_adds_new_keyword():
    existing = pd.DataFrame({"date": ["2025-01-05"], "cats": [20]})
    batch = pd.DataFrame({"date": ["2025-01-05", "2025-01-12"], "dogs": [7, 9]})
    merged = scraper.merge_batch(existing, batch)
    assert list(merged.columns) == ["date", "cats", "dogs"]
    assert merged.loc[0, "cats"] == 20
    assert merged.loc[0, "dogs"] == 7
    assert len(merged) == 2


def test_run_batches_all_keywords_and_writes_output(tmp_path):
    input_csv = tmp_path / "keywords.csv"
    output_csv = tmp_path / "output" / "trends.csv"
    pd.DataFrame({"Keyword": ["cats", "dogs", "birds"]}).to_csv(input_csv, index=False)
    fake = FakeTrends([
        trends_frame({"cats": [10, 20], "dogs": [30, 40]}),
        trends_frame({"birds": [50, 60]}),
    ])
    args = make_args(tmp_path, input_csv, output_csv)
    count = scraper.run(args, client=fake)
    saved = pd.read_csv(output_csv)
    assert count == 3
    assert [call[0] for call in fake.calls] == [["cats", "dogs"], ["birds"]]
    assert set(saved.columns) == {"date", "cats", "dogs", "birds"}
    assert len(saved) == 2


def test_run_skips_keywords_already_in_output(tmp_path):
    input_csv = tmp_path / "keywords.csv"
    output_csv = tmp_path / "trends.csv"
    pd.DataFrame({"Keyword": ["cats", "dogs"]}).to_csv(input_csv, index=False)
    pd.DataFrame({"date": ["2025-01-05"], "cats": [10]}).to_csv(output_csv, index=False)
    fake = FakeTrends([trends_frame({"dogs": [30, 40]})])
    args = make_args(tmp_path, input_csv, output_csv, batch_size=1)
    assert scraper.run(args, client=fake) == 1
    assert [call[0] for call in fake.calls] == [["dogs"]]
    assert set(pd.read_csv(output_csv).columns) == {"date", "cats", "dogs"}
