"""Report orchestration helpers used by UI pages."""

from app.report.engine import build_report_snapshot


def summary_rows_for_payload(snapshot):
    rows = []
    for row in (snapshot or {}).get("rows", []):
        rows.append({
            "slot": row.get("slot"),
            "slot_label": row.get("slot_label"),
            "dummy_name": row.get("dummy_name"),
            "dummy_profile": row.get("dummy_profile"),
            "section_key": row.get("section_key"),
            "region": row.get("region"),
            "result_key": row.get("result_key"),
            "label": row.get("label"),
            "result_uid": row.get("result_uid"),
            "value": row.get("value"),
            "unit": row.get("unit"),
            "limit": row.get("limit"),
            "status": row.get("status"),
            "comparison": row.get("comparison"),
            "value_source": row.get("value_source"),
            "value_path": row.get("value_path"),
            "limit_source": row.get("limit_source"),
        })
    return rows


def build_summary_report_payload(snapshot, report_fields, regulation_name):
    snapshot = dict(snapshot or {})
    return {
        "report_type": "summary_report",
        "regulation": snapshot.get("regulation_name") or regulation_name,
        "report_fields": dict(report_fields or {}),
        "slots": list(snapshot.get("slots") or []),
        "rows": summary_rows_for_payload(snapshot),
        "excel_mapping": dict(snapshot.get("excel_mapping") or {}),
    }


def build_summary_report_payload_from_metadata(metadata, regulation_name, report_fields):
    snapshot = build_report_snapshot(metadata or {}, regulation_name)
    return build_summary_report_payload(snapshot, report_fields, regulation_name)


def update_summary_report_cache(metadata, regulation_name, report_fields, snapshot=None):
    metadata = dict(metadata or {})
    report_saved = dict(metadata.get("report_saved_results") or {})
    existing = dict(report_saved.get("summary_report") or {})
    existing["regulation"] = regulation_name
    existing["report_fields"] = dict(report_fields or {})
    if snapshot:
        existing["slots"] = list(snapshot.get("slots") or [])
        existing["rows"] = summary_rows_for_payload(snapshot)
        existing["excel_mapping"] = dict(snapshot.get("excel_mapping") or {})
        existing["report_type"] = "summary_report"
    report_saved["summary_report"] = existing
    metadata["report_saved_results"] = report_saved
    return metadata
