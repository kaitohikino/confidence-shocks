"""Project configuration: one YAML file in, one frozen dataclass out."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    name: str
    competitions: list[dict[str, str]]
    window_minutes: float = 15.0
    controls: str = "on_target"
    method: str = "ancova"  # ancova (adjust for the before-shot level) | change (after - before)
    max_smd: float = 0.1  # balance gate: largest allowed standardised difference before the shot
    n_boot: int = 2000
    seed: int = 0
    data_dir: Path = ROOT / "data"
    reports_dir: Path = ROOT / "reports"

    # Tidy per-match tables are shared between configs (a match is a match).
    @property
    def events_dir(self) -> Path:
        return self.data_dir / "interim" / "events"

    @property
    def spans_dir(self) -> Path:
        return self.data_dir / "interim" / "spans"

    # Everything downstream is kept separate per config so runs never overwrite each other.
    @property
    def matches_path(self) -> Path:
        return self.data_dir / "processed" / self.name / "matches.parquet"

    @property
    def shocks_path(self) -> Path:
        return self.data_dir / "processed" / self.name / "shocks.parquet"

    @property
    def out_dir(self) -> Path:
        return self.reports_dir / self.name


def load_config(path: str | Path = ROOT / "configs" / "default.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    for key in ("data_dir", "reports_dir"):
        if key in raw:
            raw[key] = Path(raw[key])
    return Config(**raw)
