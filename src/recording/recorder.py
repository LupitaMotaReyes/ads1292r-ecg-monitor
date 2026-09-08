"""CSV + JSON-metadata recording of acquired ECG/respiration data."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.config import AppConfig

CSV_COLUMNS = [
    "timestamp",
    "sample_index",
    "ecg_raw",
    "ecg_filtered",
    "resp_raw",
    "heart_rate",
    "signal_quality",
]

DEFAULT_RECORDINGS_DIR = Path("data/recordings")


def build_metadata(config: AppConfig) -> dict:
    """Builds the metadata dict written alongside a recording's CSV.

    Hardware fields describe the CWXS kit this project targets, not a measurement of
    the specific unit in use; ADC parameters reflect whatever the user configured in
    Settings and are only as accurate as that configuration.
    """
    from src.config import APP_VERSION

    return {
        "hardware": "CWXS ADS1292R-Arduino Wireless Transmission Kit",
        "pcb": "CWXS Arduino Nano wireless carrier PCB",
        "adc": "Texas Instruments ADS1292R",
        "data_source": config.data_source.value,
        "sample_rate_hz": config.connection.sample_rate_hz,
        "baud_rate": config.connection.baud_rate,
        "com_port": config.connection.com_port,
        "ads1292r": asdict(config.ads1292r),
        "filters": asdict(config.filters),
        "software_version": APP_VERSION,
    }


class Recorder:
    """Writes one CSV + one metadata JSON file per recording session."""

    def __init__(self, output_dir: Path | str = DEFAULT_RECORDINGS_DIR) -> None:
        self._output_dir = Path(output_dir)
        self._csv_file = None
        self._csv_writer = None
        self._metadata_path: Path | None = None
        self._metadata: dict = {}
        self._start_monotonic = 0.0
        self._sample_count = 0

    @property
    def is_recording(self) -> bool:
        return self._csv_file is not None

    @property
    def sample_count(self) -> int:
        return self._sample_count

    def start(self, metadata: dict) -> Path:
        if self.is_recording:
            raise RuntimeError("a recording is already in progress")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_name = f"ECG_{stamp}"
        csv_path = self._output_dir / f"{base_name}.csv"
        self._metadata_path = self._output_dir / f"{base_name}_metadata.json"

        self._csv_file = open(csv_path, "w", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(CSV_COLUMNS)

        self._metadata = dict(metadata)
        self._metadata["recording_started_iso"] = datetime.now().isoformat()
        self._start_monotonic = time.monotonic()
        self._sample_count = 0
        return csv_path

    def write_sample(
        self,
        timestamp,
        ecg_raw,
        ecg_filtered,
        resp_raw,
        heart_rate,
        signal_quality: str,
    ) -> None:
        if self._csv_writer is None:
            return
        self._csv_writer.writerow(
            [
                timestamp,
                self._sample_count,
                ecg_raw,
                ecg_filtered,
                resp_raw if resp_raw is not None else "",
                heart_rate if heart_rate is not None else "",
                signal_quality,
            ]
        )
        self._sample_count += 1

    def stop(self) -> Path | None:
        if self._csv_file is None:
            return None
        self._csv_file.close()
        self._csv_file = None
        self._csv_writer = None

        self._metadata["duration_s"] = time.monotonic() - self._start_monotonic
        self._metadata["sample_count"] = self._sample_count
        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2)
        return self._metadata_path
