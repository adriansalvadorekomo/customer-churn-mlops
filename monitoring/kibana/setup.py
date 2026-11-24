"""Provision Elasticsearch and Kibana for the churn events (idempotent, stdlib only).

1. An index template for churn-events-*: explicit types, so accuracy is a number even
   when the first event of the day has none.
2. A Kibana data view on churn-events-*.
3. The "Churn MLOps · monitoring" dashboard (Lens panels), imported with overwrite.

Runs as the one-shot ``monitoring-setup`` compose service; by hand:
    ES_URL=http://localhost:9200 KIBANA_URL=http://localhost:5601 python monitoring/kibana/setup.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

ES = os.getenv("ES_URL", "http://elasticsearch:9200")
KIBANA = os.getenv("KIBANA_URL", "http://kibana:5601")
DATA_VIEW = "churn-events"


def call(
    method: str, url: str, body: bytes | None = None, headers: dict | None = None
) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:  # nosec B310
            return res.status, res.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()


def wait(url: str, ok=lambda s, b: s == 200, label: str = "") -> None:
    for _ in range(90):
        try:
            if ok(*call("GET", url)):
                print(f"{label} ready")
                return
        except OSError:
            pass
        time.sleep(2)
    sys.exit(f"{label} not reachable at {url}")


def index_template() -> None:
    body = {
        "index_patterns": ["churn-events-*"],
        "template": {
            "settings": {"number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "container_name": {"type": "keyword"},
                    "churn": {
                        "properties": {
                            "event": {"type": "keyword"},
                            "service": {"type": "keyword"},
                            "level": {"type": "keyword"},
                            "method": {"type": "keyword"},
                            "path": {"type": "keyword"},
                            "status": {"type": "integer"},
                            "duration_ms": {"type": "float"},
                            "exited": {"type": "integer"},
                            "flow": {"type": "keyword"},
                            "accuracy": {"type": "float"},
                            "recall_churn": {"type": "float"},
                            "n_estimators": {"type": "integer"},
                            "duration_s": {"type": "float"},
                        }
                    },
                }
            },
        },
    }
    status, text = call(
        "PUT",
        f"{ES}/_index_template/churn-events",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    print("index template:", status)
    if status >= 300:
        sys.exit(text)


def data_view() -> None:
    headers = {"Content-Type": "application/json", "kbn-xsrf": "true"}
    status, _ = call(
        "GET", f"{KIBANA}/api/data_views/data_view/{DATA_VIEW}", headers=headers
    )
    if status == 200:
        print("data view: exists")
        return
    body = {
        "data_view": {
            "id": DATA_VIEW,
            "title": "churn-events-*",
            "name": "churn events",
            "timeFieldName": "@timestamp",
        }
    }
    status, text = call(
        "POST", f"{KIBANA}/api/data_views/data_view", json.dumps(body).encode(), headers
    )
    print("data view:", status)
    if status >= 300:
        sys.exit(text)


# ── Lens panels ──────────────────────────────────────────────────────────────
def col_count(label: str) -> dict:
    return {
        "label": label,
        "dataType": "number",
        "operationType": "count",
        "isBucketed": False,
        "scale": "ratio",
        "sourceField": "___records___",
        "customLabel": True,
    }


def col_metric(
    op: str, field: str, label: str, params: dict | None = None, fmt: dict | None = None
) -> dict:
    c = {
        "label": label,
        "dataType": "number",
        "operationType": op,
        "sourceField": field,
        "isBucketed": False,
        "scale": "ratio",
        "customLabel": True,
    }
    if params or fmt:
        c["params"] = {**(params or {}), **({"format": fmt} if fmt else {})}
    return c


PCT = {"id": "percent", "params": {"decimals": 1}}
PCT2 = {"id": "percent", "params": {"decimals": 2}}
MS = {"id": "number", "params": {"decimals": 1, "suffix": " ms"}}


def col_time() -> dict:
    return {
        "label": "@timestamp",
        "dataType": "date",
        "operationType": "date_histogram",
        "sourceField": "@timestamp",
        "isBucketed": True,
        "scale": "interval",
        "params": {"interval": "auto"},
    }


def col_terms(field: str, label: str, order_by: str, size: int = 5) -> dict:
    return {
        "label": label,
        "dataType": "string",
        "operationType": "terms",
        "sourceField": field,
        "isBucketed": True,
        "scale": "ordinal",
        "customLabel": True,
        "params": {
            "size": size,
            "orderBy": {"type": "column", "columnId": order_by},
            "orderDirection": "desc",
        },
    }


def lens(
    lid: str, title: str, vis_type: str, columns: dict, visualization: dict, kql: str
) -> dict:
    return {
        "type": "lens",
        "id": lid,
        "attributes": {
            "title": title,
            "visualizationType": vis_type,
            "state": {
                "datasourceStates": {
                    "formBased": {
                        "layers": {
                            "l1": {
                                "columns": columns,
                                "columnOrder": list(columns),
                                "incompleteColumns": {},
                            }
                        }
                    }
                },
                "visualization": visualization,
                "query": {"query": kql, "language": "kuery"},
                "filters": [],
            },
        },
        "references": [
            {
                "type": "index-pattern",
                "id": DATA_VIEW,
                "name": "indexpattern-datasource-layer-l1",
            }
        ],
    }


def metric(lid, title, column, kql):
    return lens(
        lid,
        title,
        "lnsMetric",
        {"m": column},
        {"layerId": "l1", "layerType": "data", "metricAccessor": "m"},
        kql,
    )


def xy(lid, title, columns, accessors, kql, series="line", y_title=""):
    return lens(
        lid,
        title,
        "lnsXY",
        columns,
        {
            "legend": {"isVisible": True, "position": "bottom"},
            "yTitle": y_title,
            "xTitle": "",
            "preferredSeriesType": series,
            "valueLabels": "hide",
            "layers": [
                {
                    "layerId": "l1",
                    "layerType": "data",
                    "seriesType": series,
                    "xAccessor": "t",
                    "accessors": accessors,
                }
            ],
        },
        kql,
    )


def table(lid, title, columns, kql):
    return lens(
        lid,
        title,
        "lnsDatatable",
        columns,
        {
            "layerId": "l1",
            "layerType": "data",
            "columns": [{"columnId": c} for c in columns],
        },
        kql,
    )


def panels() -> list[dict]:
    pred = 'churn.event : "prediction"'
    req = 'churn.event : "http_request" and churn.path : "/predict"'
    runs = 'churn.event : ("training_run" or "evaluation_run")'
    return [
        metric("churn-predictions", "Predictions", col_count("Predictions"), pred),
        metric(
            "churn-leave-share",
            "Share predicted to leave",
            col_metric("average", "churn.exited", "Share predicted to leave", fmt=PCT),
            pred,
        ),
        metric(
            "churn-p95",
            "POST /predict · p95 latency",
            col_metric(
                "percentile",
                "churn.duration_ms",
                "POST /predict · p95 latency",
                {"percentile": 95},
                MS,
            ),
            req,
        ),
        metric(
            "churn-last-accuracy",
            "Last run accuracy",
            col_metric(
                "last_value",
                "churn.accuracy",
                "Last run accuracy",
                {"sortField": "@timestamp"},
                PCT2,
            ),
            runs,
        ),
        xy(
            "churn-quality-over-time",
            "Accuracy and churner recall per run",
            {
                "t": col_time(),
                "a": col_metric("max", "churn.accuracy", "Accuracy", fmt=PCT),
                "r": col_metric("max", "churn.recall_churn", "Churner recall", fmt=PCT),
            },
            ["a", "r"],
            runs,
            y_title="holdout score",
        ),
        xy(
            "churn-predictions-over-time",
            "Predictions over time (stays vs leaves)",
            {
                "t": col_time(),
                "s": col_metric("sum", "churn.exited", "Predicted to leave"),
                "n": col_count("All predictions"),
            },
            ["n", "s"],
            pred,
            series="bar",
            y_title="predictions",
        ),
        xy(
            "churn-latency-over-time",
            "POST /predict latency",
            {
                "t": col_time(),
                "p50": col_metric("median", "churn.duration_ms", "median", fmt=MS),
                "p95": col_metric(
                    "percentile", "churn.duration_ms", "p95", {"percentile": 95}, MS
                ),
            },
            ["p50", "p95"],
            req,
            y_title="ms",
        ),
        table(
            "churn-requests",
            "Requests by path and status",
            {
                "p": col_terms("churn.path", "Path", "c"),
                "s": col_terms("churn.status", "Status", "c"),
                "c": col_count("Requests"),
            },
            'churn.event : "http_request"',
        ),
    ]


def dashboard(ps: list[dict]) -> dict:
    layout = [
        (0, 0, 12, 7),
        (12, 0, 12, 7),
        (24, 0, 12, 7),
        (36, 0, 12, 7),
        (0, 7, 24, 14),
        (24, 7, 24, 14),
        (0, 21, 24, 14),
        (24, 21, 24, 14),
    ]
    grid, refs = [], []
    for i, (p, (x, y, w, h)) in enumerate(zip(ps, layout, strict=True)):
        pid = f"p{i}"
        # Metric tiles carry their own label; a panel title would repeat it.
        cfg = (
            {"hidePanelTitles": True}
            if p["attributes"]["visualizationType"] == "lnsMetric"
            else {}
        )
        grid.append(
            {
                "type": "lens",
                "panelIndex": pid,
                "panelRefName": f"panel_{pid}",
                "gridData": {"x": x, "y": y, "w": w, "h": h, "i": pid},
                "embeddableConfig": cfg,
            }
        )
        refs.append({"type": "lens", "id": p["id"], "name": f"panel_{pid}"})
    return {
        "type": "dashboard",
        "id": "churn-monitoring",
        "attributes": {
            "title": "Churn MLOps · monitoring",
            "description": "API traffic, predictions and model quality from the structured events (src/observability.py).",
            "panelsJSON": json.dumps(grid),
            "optionsJSON": json.dumps(
                {"useMargins": True, "syncColors": False, "hidePanelTitles": False}
            ),
            "timeRestore": True,
            "timeFrom": "now-24h",
            "timeTo": "now",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps(
                    {"query": {"query": "", "language": "kuery"}, "filter": []}
                )
            },
        },
        "references": refs,
    }


def import_objects() -> None:
    ps = panels()
    objects = [*ps, dashboard(ps)]
    # Without a version Kibana treats objects as 7.x and runs the old Lens migrations,
    # which expect the pre-8.6 state shape. These objects already use the 8.x shape.
    for o in objects:
        o["coreMigrationVersion"] = "8.8.0"
        o["typeMigrationVersion"] = "8.9.0"
    ndjson = "\n".join(json.dumps(o) for o in objects) + "\n"
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="churn.ndjson"\r\n'
        f"Content-Type: application/ndjson\r\n\r\n{ndjson}\r\n--{boundary}--\r\n"
    ).encode()
    status, text = call(
        "POST",
        f"{KIBANA}/api/saved_objects/_import?overwrite=true",
        body,
        {
            "kbn-xsrf": "true",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    result = json.loads(text) if text.startswith("{") else {}
    print(
        "dashboard import:", status, "success" if result.get("success") else text[:500]
    )
    if status >= 300 or not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    wait(f"{ES}/_cluster/health", label="elasticsearch")
    wait(
        f"{KIBANA}/api/status",
        ok=lambda s, b: s == 200 and '"level":"available"' in b.replace(" ", ""),
        label="kibana",
    )
    index_template()
    data_view()
    import_objects()
    print(
        f"open {os.getenv('KIBANA_PUBLIC_URL', 'http://localhost:5601')}/app/dashboards#/view/churn-monitoring"
    )
