"""Entry point — run the full churn pipeline end to end.

Usage (uv):
    uv sync                        # install deps (uv way)
    uv run python main.py                      # install-check + train + evaluate + save
    uv run python main.py --no-train           # load existing model + evaluate
    uv run python main.py --skip-install       # skip the pip install step
    uv run python main.py --help               # all options

Usage (pip / venv classic):
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt            # same pins as pyproject.toml
    python main.py

Usage (Prefect flows — needs no server for local runs):
    uv run python main.py --flow train        # prepare + train via Prefect
    uv run python main.py --flow evaluat      # load + evaluate via Prefect
    uv run python main.py --flow all          # full pipeline via Prefect

Pipeline orchestration (each step = one function from src/model_pipeline.py):
    1. install_dependencies() → pip install -r requirements.txt (skip with --skip-install)
    2. prepare_data()  → load + clean + split
    3. train_model()   → fit RandomForest  (skipped with --no-train)
       load_model()    → alternative when --no-train is passed
    4. evaluate_model() → accuracy + report + confusion matrix
    5. save_model()    → persist to models/classifier.joblib (+ demo predict)
"""

import argparse
from pathlib import Path

import pandas as pd

from src.model_pipeline import (
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_REQUIREMENTS_PATH,
    FEATURE_COLS,
    evaluate_model,
    install_dependencies,
    load_model,
    prepare_data,
    save_model,
    train_model,
)

# Same manual sample as the notebook's demo predict:
# [CreditScore, Gender, Age, Tenure, Balance, NumOfProducts,
#  HasCrCard, IsActiveMember, EstimatedSalary]
# (Gender already encoded: Female=0, Male=1)
DEMO_SAMPLE = [[850, 0, 43, 2, 125510.82, 1, 1, 1, 79084.10]]


def parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Customer churn pipeline: install → prepare → train → evaluate → save."
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=DEFAULT_REQUIREMENTS_PATH,
        help=f"Requirements file for job 1 (default: {DEFAULT_REQUIREMENTS_PATH})",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip job 1 (install_dependencies). Useful with `uv sync` or CI caches.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Path to Churn_Modelling.csv (default: {DEFAULT_DATA_PATH})",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Where to save/load classifier.joblib (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split fraction (default: 0.2)",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=100,
        help="Number of RandomForest trees (default: 100)",
    )
    parser.add_argument(
        "--no-train",
        action="store_true",
        help="Skip training: load an already-saved model and only evaluate.",
    )
    parser.add_argument(
        "--flow",
        choices=["all", "train", "evaluat"],
        default=None,
        help="Run a Prefect flow instead of direct calls "
        "(all=train+evaluate+save+load, train=prepare+train, "
        "evaluat=load+evaluate). Default: direct calls, no orchestration.",
    )
    parser.add_argument(
        "--fetch-code",
        action="store_true",
        help="Only with --flow: clone/pull the GitHub repo first (Étape 06). "
        "Without it, flows run on the local checkout.",
    )
    return parser.parse_args()


def _run_flow(args: argparse.Namespace) -> None:
    """Dispatch to the requested Prefect flow."""
    from src.flows import all_flow, evaluat_flow, train_flow

    if args.flow == "all":
        result = all_flow(
            fetch_code=args.fetch_code,
            run_install=not args.skip_install,
            requirements=args.requirements,
            data=args.data,
            model_path=args.model,
            test_size=args.test_size,
            n_estimators=args.n_estimators,
        )
    elif args.flow == "train":
        result = train_flow(
            fetch_code=args.fetch_code,
            data=args.data,
            model_path=args.model,
            test_size=args.test_size,
            n_estimators=args.n_estimators,
        )
    else:
        result = evaluat_flow(
            fetch_code=args.fetch_code,
            data=args.data,
            model_path=args.model,
            test_size=args.test_size,
        )
    print(f"Flow '{args.flow}' finished → {result}")


def main() -> None:
    args = parse_args()

    if args.flow is not None:
        _run_flow(args)
        return

    # --- 1. Install ------------------------------------------------------
    if args.skip_install:
        print("[1/5] Skipping dependency install (--skip-install).")
    else:
        print(f"[1/5] Installing dependencies from {args.requirements} ...")
        install_dependencies(requirements=args.requirements)

    # --- 2. Prepare ------------------------------------------------------
    print(f"[2/5] Preparing data from {args.data} ...")
    X_train, X_test, y_train, y_test = prepare_data(
        csv_path=args.data, test_size=args.test_size
    )
    print(f"      train={X_train.shape}, test={X_test.shape}")

    # --- 3. Train (or load) ------------------------------------------------
    if args.no_train:
        print(f"[3/5] Loading model from {args.model} ...")
        model = load_model(args.model)
    else:
        print(f"[3/5] Training RandomForest (n_estimators={args.n_estimators}) ...")
        model = train_model(X_train, y_train, n_estimators=args.n_estimators)
        save_model(model, args.model)

    # --- 4. Evaluate -------------------------------------------------------
    print("[4/5] Evaluating ...")
    metrics = evaluate_model(model, X_test, y_test)

    # --- 5. Demo predict ---------------------------------------------------
    # Proves the (re)loaded model works on a single raw row, like the
    # notebook's rf.predict([[850, 0, 43, ...]]) cell.
    # Wrapped in a DataFrame with FEATURE_COLS to keep feature names
    # (avoids the sklearn "X does not have valid feature names" warning).
    demo_df = pd.DataFrame(DEMO_SAMPLE, columns=FEATURE_COLS)
    demo_pred = model.predict(demo_df)
    print(f"[5/5] Demo predict on sample customer → Exited={demo_pred[0]}")
    print(f"      (accuracy={metrics['accuracy'] * 100:.2f}%) Done.")


if __name__ == "__main__":
    main()
