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
    c = Canvas(W, 1000, theme)
    t = c.t
    c.header(
        "C4 MODEL  ·  LEVEL 1  ·  SYSTEM CONTEXT",
        "Customer Churn MLOps",
        "Who uses it, and what it depends on.",
        STACK,
    )
    c.person(
        80,
        340,
        400,
        140,
        "Analyst",
        ["Scores one customer at a time", "and reads the model report"],
    )
    c.person(
        80,
        610,
        400,
        140,
        "ML engineer",
        ["Runs and schedules the pipeline;", "reads MLflow and Kibana"],
    )

    c.card(
        700,
        300,
        760,
        470,
        t["ana"],
        "SOFTWARE SYSTEM",
        "Customer Churn MLOps",
        "Docker Compose · 5 services + monitoring profile",
        [
            "A bank-churn RandomForest made repeatable:",
            "four code gates, three scheduled Prefect",
            "flows, every training run tracked in MLflow.",
            "",
            "FastAPI and a browser desk serve it; an opt-in",
            "ELK profile shows traffic, predictions and",
            "model quality.",
            "",
            "Holdout: 85.55% accuracy, churner recall 0.42.",
        ],
        icons=("prefect", "mlflow", "fastapi"),
        title_size=30,
        line_size=17,
    )

    c.card(
        1640,
        290,
        480,
        150,
        t["ext"],
        "DATA · IN THE REPOSITORY",
        "Churn_Modelling.csv",
        "10,000 customers · 14 columns",
        ["Bank churn dataset (Kaggle);", "target: Exited"],
        icons=("csv",),
    )
    c.card(
        1640,
        470,
        480,
        150,
        t["ext"],
        "EXTERNAL SYSTEM",
        "GitHub",
        "source repository",
        ["fetch-source-code clones or", "pulls it before a full run"],
        icons=("github",),
    )
    c.card(
        1640,
        650,
        480,
        150,
        t["ext"],
        "EXTERNAL SYSTEM",
        "Docker Hub",
        "twelvy1400/churn-mlops-*",
        ["Prebuilt backend and frontend", "images for docker compose"],
        icons=("docker",),
    )

    c.arrow([(480, 420), (697, 420)], halo=True)
    c.label(588, 420, ["Scores customers"], tech="browser")
    c.arrow([(480, 690), (697, 690)], halo=True)
    c.label(588, 690, ["Runs flows,", "reads runs"], tech="Prefect · MLflow · Kibana")
    c.arrow([(1460, 365), (1637, 365)], halo=True)
    c.label(1548, 365, ["Reads"])
    c.arrow([(1460, 545), (1637, 545)], halo=True)
    c.label(1548, 545, ["Clones, pulls"], tech="git")
    c.arrow([(1460, 725), (1637, 725)], halo=True)
    c.label(1548, 725, ["Pulls images"])

    c.legend(
        935,
        "github.com/adriansalvadorekomo/customer-churn-mlops",
        items=[
            ("person", "person", "Person"),
            ("card", "ana", "Software system"),
            ("card", "ext", "External system or data"),
            ("rel", "line", "Uses"),
        ],
    )
    return c.svg(
        "Customer Churn MLOps — C4 Level 1, system context",
        "An analyst scores customers and an ML engineer runs the pipeline and reads MLflow and Kibana. The "
        "system reads the Churn_Modelling.csv dataset, clones or pulls its source from GitHub and pulls "
        "prebuilt images from Docker Hub.",
    )


def container(theme: str) -> str:
    WC = 2300
    c = Canvas(WC, 1960, theme)
    t = c.t
    c.header(
        "C4 MODEL  ·  LEVEL 2  ·  CONTAINER DIAGRAM",
        "Customer Churn MLOps — the compose stack",
        "One image, two roles: the backend image serves predictions and runs the scheduled flows.",
        STACK,
    )
    # grid: four columns, gutters sized for their relationship labels
    X = [90, 670, 1200, 1730]
    CW = [420, 430, 430, 420]
    cx = [x + w / 2 for x, w in zip(X, CW, strict=True)]
    RA, RB, RC = 500, 850, 1270

    c.person(270, 230, 340, 120, "Analyst", ["Scores customers in a browser"])
    c.person(
        1500,
        230,
        360,
        120,
        "ML engineer",
        ["Runs flows, reads runs and", "the monitoring dashboard"],
    )
    c.boundary(
        40,
        420,
        2160,
        1260,
        t["ops"],
        "DOCKER COMPOSE",
        "churn-mlops",
        icons=("docker",),
    )

    # row A: what people use
    c.card(
        X[0],
        RA,
        CW[0],
        190,
        t["ops"],
        "CONTAINER · WEB APP",
        "Churn Desk",
        "Astro · nginx · :4321",
        ["Intake sheet → verdict, a local", "ledger and the model report"],
        icons=("astro", "nginx"),
    )
    c.card(
        X[1],
        RA,
        CW[1],
        190,
        t["ops"],
        "CONTAINER · REST API",
        "Prediction API",
        "FastAPI · uvicorn · :8000",
        ["POST /predict · GET /health;", "loads classifier.joblib at start"],
        icons=("fastapi", "python"),
    )
    c.card(
        X[2],
        RA,
        CW[2],
        190,
        t["ana"],
        "CONTAINER · ORCHESTRATOR",
        "Prefect server",
        "prefect 3.8.8 · :4200",
        ["Deployments, schedules", "and run state (UI + API)"],
        icons=("prefect",),
    )
    c.card(
        X[3],
        RA,
        CW[3],
        190,
        t["ana"],
        "CONTAINER · TRACKING",
        "MLflow server",
        "mlflow 3.17.1 · :5000",
        ["Params, accuracy and model", "of every training run"],
        icons=("mlflow",),
    )
    # row B: the worker and its stores
    c.card(
        X[1],
        RB,
        CW[1],
        200,
        t["gold"],
        "DATA STORE · HOST VOLUME",
        "./models",
        "classifier.joblib",
        ["Written by the worker; the API", "serves it after a restart"],
        shape="cylinder",
    )
    c.card(
        X[2],
        RB,
        CW[2],
        200,
        t["ana"],
        "CONTAINER · PIPELINE",
        "Worker",
        "backend image · deploiement_prefect.py",
        [
            "Serves the flows all, train, evaluat",
            "cron 02:00 · 04:00 · 06:00 UTC",
            "and runs them in-process",
        ],
        icons=("prefect", "python"),
    )
    c.card(
        X[3],
        RB,
        CW[3],
        200,
        t["gold"],
        "DATA STORE · READ-ONLY MOUNT",
        "notebooks/data",
        "Churn_Modelling.csv",
        ["10,000 customers; 80/20", "split with seed 1"],
        shape="cylinder",
    )

    # people
    c.arrow([(440, 350), (440, 497)], halo=True)
    c.label(440, 455, ["Scores customers"], tech="browser · :4321")
    c.arrow([(1680, 350), (1680, 455)], head=False)
    c.arrow([(cx[2], 455), (cx[3], 455)], head=False)
    c.arrow([(cx[2], 455), (cx[2], 497)])
    c.arrow([(cx[3], 455), (cx[3], 497)])
    c.label(1680, 392, ["Triggers flows, reads runs"], tech="browser · :4200 · :5000")
    c.arrow([(1860, 290), (2245, 290), (2245, 1365), (2153, 1365)], halo=True)
    c.label(2245, 360, ["Reads"], tech=":5601")
    # serving
    c.arrow([(510, 595), (667, 595)], halo=True)
    c.label(588, 595, ["POST /predict"], tech="JSON")
    c.arrow([(cx[1], RA + 190), (cx[1], RB - 3)], halo=True)
    c.label(cx[1], 770, ["Loads at start"], tech="joblib")
    # pipeline
    c.arrow([(cx[2], RB - 3), (cx[2], RA + 193)], halo=True)
    c.label(
        cx[2], 770, ["Serves deployments,", "reports run state"], tech="Prefect API"
    )
    c.arrow([(1580, RB - 3), (1580, 800), (cx[3], 800), (cx[3], RA + 193)], halo=True)
    c.label(1800, 800, ["Logs every run"], tech="MLflow REST")
    c.arrow([(X[2] - 3, 950), (X[1] + CW[1] + 3, 950)], halo=True)
    c.label(1150, 950, ["Writes"])
    c.arrow([(X[2] + CW[2], 990), (X[3] - 3, 990)], halo=True)
    c.label(1680, 990, ["Reads"])

    # monitoring profile
    c.boundary(
        70,
        1190,
        2100,
        420,
        t["dlv"],
        "PROFILE · MONITORING",
        "docker compose --profile monitoring up -d",
        icons=("elastic",),
        tab="right",
    )
    c.card(
        X[0],
        RC,
        CW[0],
        200,
        t["dlv"],
        "CONTAINER · LOG SHIPPER",
        "Filebeat",
        "filebeat 9.5.5",
        ["Reads the Docker logs of the", "containers labelled churn_logs"],
        icons=("beats",),
    )
    c.card(
        X[1],
        RC,
        CW[1],
        200,
        t["dlv"],
        "CONTAINER · PIPELINE",
        "Logstash",
        "logstash 9.5.5 · beats :5044",
        ["JSON events → churn-events-*", "other lines → churn-logs-*"],
        icons=("logstash",),
    )
    c.card(
        X[2],
        RC,
        CW[2],
        200,
        t["dlv"],
        "DATA STORE · SEARCH",
        "Elasticsearch",
        "9.5.5 · single node · :9200",
        ["Typed by an index template", "(monitoring/kibana/setup.py)"],
        icons=("elasticsearch",),
        shape="cylinder",
    )
    c.card(
        X[3],
        RC,
        CW[3],
        200,
        t["dlv"],
        "CONTAINER · DASHBOARD",
        "Kibana",
        "kibana 9.5.5 · :5601",
        ["Churn MLOps · monitoring:", "traffic, predictions, quality"],
        icons=("kibana",),
    )
    # events: API and worker stdout → Filebeat
    c.arrow([(X[1] - 3, 650), (600, 650), (600, 1120)], dashed=True, head=False)
    c.arrow([(cx[2], RB + 203), (cx[2], 1120)], dashed=True, head=False)
    c.arrow([(cx[2], 1120), (300, 1120), (300, RC - 3)], dashed=True)
    c.label(980, 1120, ["JSON events on stdout"], tech="src/observability.py")
    c.arrow([(X[0] + CW[0], 1370), (X[1] - 3, 1370)], halo=True)
    c.label(590, 1370, ["Ships"], tech="beats")
    c.arrow([(X[1] + CW[1], 1370), (X[2] - 3, 1370)], halo=True)
    c.label(1150, 1370, ["Indexes"])
    c.arrow([(X[3], 1370), (X[2] + CW[2] + 3, 1370)], halo=True)
    c.label(1680, 1370, ["Queries"])
    c.text(
        100,
        1572,
        "Local only: Elastic security off; every monitoring port is bound to 127.0.0.1.",
        14,
        400,
        t["muted"],
        MONO,
    )

    c.text(
        60,
        1735,
        "A retrained model lands in ./models; `docker compose restart backend` serves it.",
        15,
        400,
        t["muted"],
        MONO,
    )
    c.text(
        60,
        1765,
        "A tracking outage is a warning, never a pipeline failure (src/tracking.py).",
        15,
        400,
        t["muted"],
        MONO,
    )
    c.legend(
        1895,
        "docker-compose.yml · deploiement_prefect.py · monitoring/",
        items=[
            ("person", "person", "Person"),
            ("card", "ops", "Serving"),
            ("card", "ana", "Orchestration and tracking"),
            ("card", "dlv", "Monitoring (opt-in)"),
            ("store", "gold", "Data store"),
            ("boundary", "ops", "Deployment boundary"),
            ("rel", "line", "Uses"),
            ("rel_dashed", "line", "Log events"),
        ],
    )
    return c.svg(
        "Customer Churn MLOps — C4 Level 2, containers",
        "In Docker Compose, an analyst uses the Churn Desk (Astro and nginx, port 4321), which calls the FastAPI "
        "prediction API (port 8000); the API loads classifier.joblib from the ./models volume. The worker, built from "
        "the same image, serves the three Prefect deployments against the Prefect server (port 4200), reads "
        "Churn_Modelling.csv, writes the model to ./models and logs every run to MLflow (port 5000). In the opt-in "
        "monitoring profile, the API and the worker print JSON events that Filebeat ships to Logstash, which indexes "
        "them in Elasticsearch for the Kibana dashboard (port 5601) read by the ML engineer.",
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
    c.arrow([(500, 680), (gx - 45, 680), (gx - 45, 420), (gx - 3, 420)], halo=True)
    c.label(gx - 45, 590, ["1 · gates"])
    c.arrow([(500, 770), (gx - 3, 770)], halo=True)
    c.label(gx - 45, 770, ["2 · jobs"])

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
        items=[
            ("card", "ana", "Component"),
            ("card", "ok", "Blocking code gate"),
            ("card", "dlv", "Monitoring events"),
            ("card", "ext", "Other container"),
            ("store", "gold", "Data store"),
            ("boundary", "ana", "Container boundary"),
            ("rel", "line", "Calls / data flow"),
        ],
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
            ("context", context, (W, 1000)),
            ("container", container, (2300, 1960)),
            ("component", component, (W, 1360)),
        ),
    )
