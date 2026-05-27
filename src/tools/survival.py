"""Survival analysis tool."""

import logging

from . import register
from .db_query import _safe_query

logger = logging.getLogger(__name__)


@register(
    name="survival_analysis",
    description="Query survival data and statistics for a specific disease. Returns survival records, median survival time, event counts, and cohort summary.",
    input_schema={
        "type": "object",
        "properties": {
            "disease_name": {
                "type": "string",
                "description": "Name of the disease to analyze survival data for",
            },
        },
        "required": ["disease_name"],
    },
)
def survival_analysis(disease_name: str) -> dict:
    """Query survival data for a disease."""
    sql = """
        SELECT sv.survival_id, sv.survival_time, sv.event, sv.stage, sv.treatment,
               s.sample_name
        FROM survival sv
        JOIN sample s ON sv.sample_id = s.sample_id
        JOIN disease d ON sv.disease_id = d.disease_id
        WHERE d.name LIKE %s
        ORDER BY sv.survival_time
        LIMIT 100
    """
    result = _safe_query(sql, (f"%{disease_name}%",))
    if "error" in result:
        return result

    rows = result.get("results", [])
    if not rows:
        return {
            "disease_query": disease_name,
            "message": "No survival data found for this disease.",
            "total_patients": 0,
        }

    events = sum(1 for r in rows if r["event"] == 1)
    censored = len(rows) - events

    times = sorted(r["survival_time"] for r in rows)
    median_idx = len(times) // 2
    median_survival = times[median_idx] if times else None

    # Group by stage
    stages = {}
    for r in rows:
        stage = r.get("stage") or "Unknown"
        stages[stage] = stages.get(stage, 0) + 1

    treatments = {}
    for r in rows:
        tx = r.get("treatment") or "Unknown"
        treatments[tx] = treatments.get(tx, 0) + 1

    return {
        "disease_query": disease_name,
        "total_patients": len(rows),
        "events": events,
        "censored": censored,
        "median_survival_days": median_survival,
        "by_stage": stages,
        "by_treatment": treatments,
        "survival_records": [
            {
                "sample": r["sample_name"],
                "time_days": r["survival_time"],
                "event": "Death" if r["event"] else "Censored",
                "stage": r.get("stage", "N/A"),
            }
            for r in rows
        ],
    }
