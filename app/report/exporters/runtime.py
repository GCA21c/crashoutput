import os
import platform
import subprocess
import sys
from pathlib import Path

from app.report.templates import get_report_template_spec


def sanitize_filename_part(text):
    safe = "".join("_" if char in '\\/:*?"<>|' or ord(char) < 32 else char for char in str(text or "").strip())
    safe = safe.strip(" .")
    return safe or "NO_TEST_ID"


def default_export_filename(test_id, template_spec=None):
    spec = dict(template_spec or get_report_template_spec())
    safe_test_id = sanitize_filename_part(str(test_id or "").strip() or "NO_TEST_ID")
    template_path = Path(spec.get("template_path"))
    stem = template_path.stem
    if stem.lower().endswith("_temp"):
        stem = stem[:-5]
    return f"{stem}_{safe_test_id}{template_path.suffix}"


def folder_is_writable(folder):
    folder = Path(folder)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".crashoutput_write_test"
        with probe.open("w", encoding="utf-8") as handle:
            handle.write("")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def execution_folder(source_file=None):
    if getattr(sys, "frozen", False):
        folder = Path(sys.executable).resolve().parent
    elif source_file:
        folder = Path(source_file).resolve().parents[3]
    else:
        folder = Path.cwd()

    if folder_is_writable(folder):
        return folder

    documents = Path.home() / "Documents"
    if documents.exists() and folder_is_writable(documents):
        return documents
    return folder


def unique_export_path(test_id, source_file=None, template_spec=None):
    folder = execution_folder(source_file=source_file)
    candidate = folder / default_export_filename(test_id, template_spec=template_spec)
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(1, 1000):
        numbered = folder / f"{stem}_{index:02d}{suffix}"
        if not numbered.exists():
            return numbered
    return candidate


def open_export_file(path):
    path = Path(path)
    system_name = platform.system().lower()
    if system_name == "windows":
        os.startfile(str(path))
    elif system_name == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
