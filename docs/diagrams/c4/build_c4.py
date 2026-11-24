#!/usr/bin/env python3
"""Build the C4 diagrams for Customer Churn MLOps (context, containers, pipeline components).

    python docs/diagrams/c4/build_c4.py            # SVG + PNG (needs Chromium)
    python docs/diagrams/c4/build_c4.py --svg-only

Every element comes from the code at the commit it ships with: docker-compose.yml
(services, ports, volumes), deploiement_prefect.py (schedules), src/flows.py and
src/tasks.py (jobs and gates), src/tracking.py (MLflow), src/app.py (API).
Drawing kit: c4lib.py (shared with the DataOps Lakehouse diagrams).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from c4lib import MONO, Canvas, build

STACK = [
    "python",
    "scikitlearn",
    "prefect",
    "mlflow",
    "fastapi",
    "astro",
    "docker",
    "elasticsearch",
]
W = 2200


def context(theme: str) -> str:
    c = Canvas(W, 1180, theme)
    t = c.t
    c.header(
        "C4 MODEL  ·  LEVEL 1  ·  SYSTEM CONTEXT",
        "Customer Churn MLOps",
        "Who uses it, and what it depends on.",
        STACK,
    )
    c.person(
        80,
        330,
        380,
        150,
        "Analyst or reviewer",
        ["Scores one customer at a time", "and reads the model report"],
    )
    c.person(
        80,
        650,
        380,
        150,
        "ML engineer",
        ["Runs and schedules the pipeline,", "reads every run in MLflow"],
    )

    c.card(
        700,
        300,
        760,
        520,
        t["ana"],
        "SOFTWARE SYSTEM",
        "Customer Churn MLOps",
        "five Docker Compose services",
        [
            "A bank-churn RandomForest, retrained by three",
            "scheduled Prefect flows behind four code gates.",
            "",
            "Every training run is logged to MLflow.",
            "Predictions are served by FastAPI and an Astro",
            "desk; retrained models land in ./models.",
            "Optional ELK layer: requests, predictions and",
            "model quality in Kibana.",
            "",
            "Holdout: 85.55% accuracy, churner recall 0.42.",
        ],
        icons=("prefect", "mlflow", "fastapi"),
        title_size=30,
        line_size=17,
    )

    c.card(
        1620,
        240,
        500,
        170,
        t["ext"],
        "DATA · IN THE REPO",
        "Churn_Modelling.csv",
        "10,000 customers · 14 columns",
        ["Bank churn dataset (Kaggle);", "target: Exited"],
        icons=("csv",),
    )
    c.card(
        1620,
        480,
        500,
        170,
        t["ext"],
        "EXTERNAL SYSTEM",
        "GitHub",
        "source repository",
        ["fetch-source-code clones or", "pulls it before a full run"],
        icons=("github",),
    )
    c.card(
        1620,
        720,
        500,
        170,
        t["ext"],
        "EXTERNAL SYSTEM",
        "Docker Hub",
        "twelvy1400/churn-mlops-*",
        ["Prebuilt backend and frontend", "images, pulled by compose"],
        icons=("docker",),
    )

    c.arrow([(460, 405), (697, 405)], halo=True)
    c.label(578, 380, ["Scores customers"], tech="browser")
    c.arrow([(460, 725), (697, 725)], halo=True)
    c.label(578, 700, ["Runs flows, reads runs"], tech="Prefect · MLflow · Kibana")
    c.arrow([(1460, 325), (1617, 325)], halo=True)
    c.label(1538, 300, ["reads"])
    c.arrow([(1460, 565), (1617, 565)], halo=True)
    c.label(1538, 540, ["clone / pull"], tech="git")
    c.arrow([(1617, 805), (1460, 805)], halo=True)
    c.label(1538, 780, ["images"])

    c.legend(
        1120,
        "github.com/adriansalvadorekomo/customer-churn-mlops",
        kinds=("person", "external", "rel"),
    )
    return c.svg(
        "Customer Churn MLOps — C4 Level 1, system context",
        "An analyst scores customers and an ML engineer runs the pipeline. The system reads the "
        "Churn_Modelling.csv dataset, clones its source from GitHub and pulls prebuilt images from Docker Hub.",
    )


def container(theme: str) -> str:
    c = Canvas(W, 1960, theme)
    t = c.t
    c.header(
        "C4 MODEL  ·  LEVEL 2  ·  CONTAINER DIAGRAM",
        "Customer Churn MLOps — the compose stack",
        "One image, two roles: the same backend image serves predictions and runs the scheduled flows.",
        STACK,
    )
    c.person(250, 222, 340, 120, "Analyst or reviewer", ["Uses the desk in a browser"])
    c.person(1660, 222, 380, 120, "ML engineer", ["Watches flows and runs"])

    c.boundary(
        40,
        400,
        2120,
        1320,
        t["ops"],
        "DOCKER COMPOSE",
        "churn-mlops",
        icons=("docker",),
    )

    # row 1: what people and the browser talk to
    c.card(
        90,
        470,
        430,
        180,
        t["ops"],
        "CONTAINER · WEB APP",
        "Churn Desk",
        "Astro, static, served by nginx · :4321",
        ["Intake sheet → verdict, a local", "ledger, and the model report"],
        icons=("astro", "nginx"),
    )
    c.card(
        600,
        470,
        450,
        180,
        t["ops"],
        "CONTAINER · REST API",
        "Prediction API",
        "FastAPI · uvicorn · :8000",
        ["POST /predict · GET /health", "loads classifier.joblib at start"],
        icons=("fastapi", "python"),
    )
    c.card(
        1130,
        470,
        450,
        180,
        t["ana"],
        "CONTAINER · ORCHESTRATOR",
        "Prefect server",
        "prefecthq/prefect 3.8.8 · :4200",
        ["UI + API: deployments,", "schedules and run state"],
        icons=("prefect",),
    )
    c.card(
        1660,
        470,
        450,
        180,
        t["ana"],
        "CONTAINER · TRACKING",
        "MLflow server",
        "mlflow 3.17.1 · :5000",
        ["params, accuracy and the model", "of every run (SQLite + artifacts)"],
        icons=("mlflow",),
    )

    # row 2: the worker and the two stores
    c.card(
        1130,
        830,
        450,
        200,
        t["ana"],
        "CONTAINER · PIPELINE",
        "Worker",
        "backend image · deploiement_prefect.py",
        [
            "Serves the flows all / train / evaluat",
            "cron 02:00 · 04:00 · 06:00 UTC",
            "runs them in-process (no work pool)",
        ],
        icons=("prefect", "python"),
    )
    c.card(
        600,
        840,
        450,
        180,
        t["gold"],
        "DATA STORE · HOST VOLUME",
        "./models",
        "classifier.joblib · joblib",
        ["written by the worker; the API", "serves it after a restart"],
        shape="cylinder",
    )
    c.card(
        1660,
        840,
        450,
        180,
        t["gold"],
        "DATA STORE · READ-ONLY MOUNT",
        "notebooks/data",
        "Churn_Modelling.csv",
        ["10,000 rows → 80/20 split", "(seed 1) at prepare-data"],
        shape="cylinder",
    )

    # relationships
    c.arrow([(420, 342), (420, 467)], halo=True)
    c.label(430, 372, ["uses"], anchor="start", tech="browser")
    c.arrow([(520, 560), (597, 560)], halo=True)
    c.label(558, 520, ["POST /predict"], tech="JSON")
    c.arrow([(825, 837), (825, 653)], halo=True)
    c.label(835, 745, ["loads at start"], anchor="start", tech="joblib")
    c.arrow([(1127, 930), (1053, 930)], halo=True)
    c.label(1090, 905, ["writes"])
    c.arrow([(1355, 827), (1355, 653)], halo=True)
    c.label(
        1365,
        745,
        ["serves deployments,", "reports run state"],
        anchor="start",
        tech="Prefect API",
    )
    c.arrow([(1580, 860), (1700, 860), (1700, 653)], halo=True)
    c.label(1710, 760, ["logs every run"], anchor="start", tech="MLflow REST")
    c.arrow([(1580, 990), (1657, 990)], halo=True)
    c.label(1618, 1040, ["reads"])
    c.arrow([(1850, 342), (1850, 467)], halo=True)
    c.label(1860, 400, ["runs, schedules"], anchor="start")

    # monitoring profile (opt-in): stdout JSON events → Filebeat → Logstash → Elasticsearch → Kibana
    c.boundary(
        70,
        1250,
        2060,
        430,
        t["dlv"],
        "PROFILE · MONITORING",
        "docker compose --profile monitoring up",
        icons=("elastic",),
        tab="left",
    )
    c.card(
        1660,
        1330,
        450,
        190,
        t["dlv"],
        "CONTAINER · LOG SHIPPER",
        "Filebeat",
        "elastic/filebeat 9.5.5",
        ["reads the stdout of containers", "labelled churn.logs: backend, worker"],
        icons=("beats",),
    )
    c.card(
        1130,
        1330,
        450,
        190,
        t["dlv"],
        "CONTAINER · PIPELINE",
        "Logstash",
        "logstash 9.5.5 · beats :5044",
        ["JSON events → churn-events-*", "other lines → churn-logs-*"],
        icons=("logstash",),
    )
    c.card(
        600,
        1330,
        450,
        190,
        t["dlv"],
        "DATA STORE · SEARCH",
        "Elasticsearch",
        "9.5.5 · single node · :9200",
        ["typed by an index template", "(monitoring/kibana/setup.py)"],
        icons=("elasticsearch",),
        shape="cylinder",
    )
    c.card(
        90,
        1330,
        430,
        190,
        t["dlv"],
        "CONTAINER · DASHBOARD",
        "Kibana",
        "9.5.5 · :5601",
        ["Churn MLOps · monitoring:", "traffic, predictions, model quality"],
        icons=("kibana",),
    )
    c.arrow(
        [(1050, 620), (1090, 620), (1090, 1110), (1885, 1110), (1885, 1327)],
        dashed=True,
        halo=True,
    )
    c.arrow([(1355, 1033), (1355, 1110)], dashed=True, head=False)
    c.label(
        1500, 1110, ["stdout: one JSON event per line"], tech="src/observability.py"
    )
    c.arrow([(1657, 1425), (1583, 1425)], halo=True)
    c.label(1620, 1460, ["beats"])
    c.arrow([(1127, 1425), (1053, 1425)], halo=True)
    c.label(1090, 1460, ["index"])
    c.arrow([(597, 1425), (523, 1425)], halo=True)
    c.label(560, 1460, ["query"])
    c.text(
        110,
        1600,
        "Local only: Elastic security off, every monitoring port bound to 127.0.0.1.",
        14.5,
        400,
        t["muted"],
        MONO,
    )

    c.text(
        90,
        1770,
        "Retrained models land in ./models on the host; `docker compose restart backend` serves them.",
        15,
        400,
        t["muted"],
        MONO,
    )
    c.text(
        90,
        1802,
        "A tracking outage is a warning, never a pipeline failure (src/tracking.py).",
        15,
        400,
        t["muted"],
        MONO,
    )
    c.legend(1895, "docker-compose.yml · deploiement_prefect.py · monitoring/")
    return c.svg(
        "Customer Churn MLOps — C4 Level 2, containers",
        "In Docker Compose: the Churn Desk (Astro + nginx, port 4321) calls the FastAPI prediction API "
        "(port 8000), which loads classifier.joblib from the ./models volume. The worker, built from the same "
        "image, serves three Prefect deployments on cron 02:00, 04:00 and 06:00 UTC against the Prefect server "
        "(port 4200), reads Churn_Modelling.csv, writes the model to ./models and logs every run to MLflow (port 5000). "
        "In the opt-in monitoring profile, Filebeat ships the JSON events printed by the backend and worker to "
        "Logstash, which indexes them in Elasticsearch for the Kibana dashboard (port 5601).",
    )


def component(theme: str) -> str:
    c = Canvas(W, 1360, theme)
    t = c.t
    c.header(
        "C4 MODEL  ·  LEVEL 3  ·  COMPONENTS",
        "Inside the pipeline (src/)",
        "Pure logic in model_pipeline.py; tasks.py wraps each job as a Prefect task; flows.py chains them.",
        STACK,
    )
    c.boundary(
        40,
        270,
        2120,
        960,
        t["ana"],
        "CONTAINER",
        "Worker · src/ + deploiement_prefect.py",
        icons=("prefect",),
    )

    c.card(
        80,
        340,
        420,
        200,
        t["ana"],
        "COMPONENT",
        "Deployments",
        "deploiement_prefect.py · prefect.serve",
        [
            "all 02:00 · train 04:00 ·",
            "evaluat 06:00 (cron, UTC)",
            "--container skips fetch + install",
        ],
    )
    c.card(
        80,
        640,
        420,
        220,
        t["ana"],
        "COMPONENT",
        "Flows",
        "src/flows.py",
        [
            "all: fetch → install → gates →",
            "prepare → train → evaluate →",
            "save → load",
            "train / evaluat: subsets",
        ],
    )
    c.arrow([(290, 540), (290, 637)], halo=True)
    c.label(300, 590, ["triggers"], anchor="start")

    gx, gw, gap = 590, 360, 30
    gates = [
        ("format-code", "ruff format", "src tests main.py …"),
        ("lint-code", "ruff check", "any violation fails"),
        ("scan-security", "bandit -c pyproject.toml", "every severity fails"),
        ("run-unit-tests", "pytest", "15 tests"),
    ]
    for i, (name, tool, note) in enumerate(gates):
        x = gx + i * (gw + gap)
        c.card(
            x,
            340,
            gw,
            160,
            t["ok"],
            "GATE · BLOCKING",
            name,
            tool,
            [note],
            title_size=19,
        )
    c.text(
        gx,
        535,
        "Code gates run right after install, before anything trains: one failure stops the flow.",
        15,
        500,
        t["ok"],
        MONO,
    )

    jobs = [
        (
            "prepare-data",
            "model_pipeline.prepare_data",
            ["LabelEncode Gender, drop", "IDs + Geography, 80/20 split"],
        ),
        ("train-model", "RandomForestClassifier", ["100 trees, random_state 42"]),
        (
            "evaluate-model",
            "accuracy · report · matrix",
            ["85.55% on the 2,000-row", "holdout · recall 0.42"],
        ),
        ("save / load", "joblib", ["save, then reload and", "predict a demo customer"]),
    ]
    for i, (name, tech, lines) in enumerate(jobs):
        x = gx + i * (gw + gap)
        c.card(
            x,
            640,
            gw,
            180,
            t["ana"],
            "TASK · src/tasks.py",
            name,
            tech,
            lines,
            title_size=19,
        )
        if i:
            c.arrow([(x - gap - 2, 730), (x - 3, 730)])
    c.arrow([(500, 600), (gx - 40, 600), (gx - 40, 420), (gx - 3, 420)], halo=True)
    c.arrow([(500, 750), (gx - 3, 750)], halo=True)
    c.label(545, 790, ["then"], anchor="middle")

    c.card(
        gx,
        930,
        gw,
        180,
        t["ana"],
        "COMPONENT",
        "Tracking",
        "src/tracking.py",
        ["params, accuracy, sklearn model", "outage → warning, not failure"],
        icons=("mlflow",),
        title_size=19,
    )
    c.arrow(
        [
            (gx + gw + gap + gw / 2, 823),
            (gx + gw + gap + gw / 2, 880),
            (gx + gw / 2, 880),
            (gx + gw / 2, 927),
        ]
    )
    c.card(
        gx + 3 * (gw + gap),
        930,
        gw,
        180,
        t["gold"],
        "DATA STORE",
        "models/classifier.joblib",
        "host volume",
        ["read by the API at start"],
        shape="cylinder",
        title_size=19,
    )
    c.arrow([(gx + 3 * (gw + gap) + gw / 2, 823), (gx + 3 * (gw + gap) + gw / 2, 927)])
    c.card(
        gx + gw + gap,
        930,
        gw,
        180,
        t["ext"],
        "CONTAINER · OUTSIDE THIS ONE",
        "MLflow server",
        "experiment: customer-churn",
        ["one run per training:", "params, accuracy, model"],
        icons=("mlflow",),
        title_size=19,
    )
    ex = gx + 2 * (gw + gap)
    c.card(
        ex,
        930,
        gw,
        180,
        t["dlv"],
        "COMPONENT",
        "Events",
        "src/observability.py",
        ["training_run / evaluation_run:", "accuracy, recall, duration → stdout"],
        icons=("elastic",),
        title_size=19,
    )
    c.arrow([(ex + gw / 2, 823), (ex + gw / 2, 927)])
    c.arrow([(gx + gw, 1020), (gx + gw + gap - 3, 1020)])

    c.legend(
        1300,
        "src/flows.py · src/tasks.py · src/model_pipeline.py · src/tracking.py",
        kinds=("component", "store", "external", "boundary", "rel"),
    )
    return c.svg(
        "Customer Churn MLOps — C4 Level 3, pipeline components",
        "Three deployments trigger the flows. The full flow runs four blocking code gates (ruff format, ruff "
        "check, bandit, pytest), then prepare-data, train-model (RandomForest, 100 trees), evaluate-model "
        "(85.55% accuracy, recall 0.42) and save/load with joblib; tracking.py logs each training run to MLflow.",
    )


if __name__ == "__main__":
    build(
        HERE,
        (
            ("context", context, (W, 1180)),
            ("container", container, (W, 1960)),
            ("component", component, (W, 1360)),
        ),
    )
