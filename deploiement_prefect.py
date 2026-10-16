"""Prefect deployments — run selected flows once per day (Étape 05).

Test the automation with 3 terminals::

    T1.  prefect server start
         # self-hosted API + UI on http://127.0.0.1:4200
    T2.  python deploiement_prefect.py [--flows all train]
         # builds the daily deployments and serves them (this process
         # both schedules AND executes runs — no separate worker needed)
    T3.  prefect deployment run "all/daily-all"
         # manual trigger to test immediately (or click Run in the UI)

Daily schedules (cron, UTC — one run per day, staggered)::

    all     → 02:00   full pipeline (gates + prepare + train + evaluate + save + load)
    train   → 04:00   prepare + train + save
    evaluat → 06:00   load + evaluate

In Docker (``--container``) the scheduled runs skip the fetch and install
jobs: the container image already ships the code and the dependencies.

Offline test (no server needed)::

    python deploiement_prefect.py --dry-run
"""

import argparse

from prefect import serve

from src.flows import all_flow, evaluat_flow, train_flow

FLOWS = {"all": all_flow, "train": train_flow, "evaluat": evaluat_flow}

# One run per day, staggered so heavy jobs never overlap.
SCHEDULES = {
    "all": "0 2 * * *",
    "train": "0 4 * * *",
    "evaluat": "0 6 * * *",
}

# Docker deployments: the image ships code + dependencies, so scheduled runs
# skip the fetch/install steps. One entry per flow — only the flows that
# actually HAVE those steps get the override.
CONTAINER_OVERRIDES = {
    "all": {"fetch_code": False, "run_install": False},
    "train": {"fetch_code": False},
    "evaluat": {"fetch_code": False},
}


def build_deployments(
    selected: tuple[str, ...] = ("all", "train", "evaluat"),
    overrides: dict[str, dict] | None = None,
):
    """Build deployment objects (local only — no server call).

    ``overrides`` maps a flow key to extra run parameters (docker sets
    fetch/install off; local serving passes nothing and uses the defaults).
    """
    deployments = []
    for key in selected:
        if key not in FLOWS:
            raise ValueError(f"Unknown flow: {key!r}. Choose from {sorted(FLOWS)}.")
        deployments.append(
            FLOWS[key].to_deployment(
                name=f"daily-{key}",
                cron=SCHEDULES[key],
                description=f"{key} flow, once per day ({SCHEDULES[key]} UTC).",
                parameters=(overrides or {}).get(key),
            )
        )
    return deployments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve daily Prefect deployments for the churn pipeline."
    )
    parser.add_argument(
        "--flows",
        nargs="+",
        default=["all", "train", "evaluat"],
        choices=sorted(FLOWS),
        help="Subset of flows to deploy (default: all three).",
    )
    parser.add_argument(
        "--container",
        action="store_true",
        help="Docker mode: scheduled runs skip fetch/install (image ships them).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build deployments and print the schedule, without serving.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overrides = CONTAINER_OVERRIDES if args.container else None
    deployments = build_deployments(tuple(args.flows), overrides=overrides)

    print("Planned daily deployments:")
    for key, dep in zip(args.flows, deployments):
        print(f"  - {dep.name}: flow={key!r}, cron={SCHEDULES[key]!r} (UTC)")
    if overrides:
        print(f"  container mode: scheduled runs override {overrides}")

    if args.dry_run:
        print("Dry run: deployments built OK, not serving (no server needed).")
        return

    print("Serving… start `prefect server start` in another terminal, then")
    print('trigger manually with e.g. `prefect deployment run "all/daily-all"`.')
    serve(*deployments)


if __name__ == "__main__":
    main()
