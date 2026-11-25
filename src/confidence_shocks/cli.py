"""Command line entry point: `confshocks --config configs/default.yaml <step>`."""

from __future__ import annotations

import argparse
import logging

from confidence_shocks import pipeline
from confidence_shocks.config import ROOT, load_config

STEPS = {
    "audit": pipeline.audit,
    "ingest": pipeline.ingest,
    "shocks": pipeline.shocks,
    "estimate": pipeline.estimate,
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="confshocks", description=__doc__)
    parser.add_argument("--config", default=ROOT / "configs" / "default.yaml")
    parser.add_argument("step", choices=STEPS)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    result = STEPS[args.step](load_config(args.config))
    if args.step in ("audit", "estimate"):
        print(result.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
