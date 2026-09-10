#!/usr/bin/env python3
"""Resume Builder web UI.

A small Flask app that lets you edit resume data in the browser, render it
through a LaTeX template, compile it to PDF, and save it — all from a UI.

Run:
    source .venv/bin/activate
    python app.py
Then open http://127.0.0.1:5001
"""

from __future__ import annotations

from pathlib import Path

import yaml
from flask import Flask, jsonify, request, send_from_directory, abort

# Reuse the rendering/compilation logic from the CLI builder.
from build import latex_escape, make_env, compile_pdf

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output" / "pdf"
WEB_DIR = ROOT / "web"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


# --- helpers ---------------------------------------------------------------
def _safe_name(name: str) -> str:
    """Prevent path traversal; keep only a bare filename stem."""
    stem = Path(name).stem
    if not stem or stem.startswith("."):
        abort(400, "Invalid name")
    return stem


def _list_yaml() -> list[str]:
    return sorted(p.stem for p in DATA_DIR.glob("*.y*ml"))


def _list_templates() -> list[str]:
    return sorted(p.name for p in TEMPLATE_DIR.glob("*.tex"))


def _data_path(name: str) -> Path:
    for ext in (".yaml", ".yml"):
        p = DATA_DIR / f"{name}{ext}"
        if p.exists():
            return p
    return DATA_DIR / f"{name}.yaml"


# --- static UI -------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/output/<path:filename>")
def output_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)


# --- API -------------------------------------------------------------------
@app.route("/api/resumes")
def api_resumes():
    return jsonify({"resumes": _list_yaml(), "templates": _list_templates()})


@app.route("/api/resume/<name>", methods=["GET"])
def api_get_resume(name):
    name = _safe_name(name)
    path = _data_path(name)
    if not path.exists():
        abort(404, "Resume not found")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return jsonify(data)


@app.route("/api/resume/<name>", methods=["POST"])
def api_save_resume(name):
    name = _safe_name(name)
    data = request.get_json(force=True) or {}
    path = _data_path(name)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )
    return jsonify({"ok": True, "saved": path.name})


@app.route("/api/render", methods=["POST"])
def api_render():
    body = request.get_json(force=True) or {}
    name = _safe_name(body.get("name", "resume"))
    template_name = body.get("template", "data-engineer.tex")
    data = body.get("data", {})

    # 1) Persist the edited data to YAML so nothing is lost.
    path = _data_path(name)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )

    # 2) Render the LaTeX template with escaped data.
    template_path = TEMPLATE_DIR / Path(template_name).name
    if not template_path.exists():
        return jsonify({"ok": False, "error": f"Template not found: {template_name}"}), 400

    env = make_env(TEMPLATE_DIR)
    try:
        template = env.get_template(template_path.name)
        rendered = template.render(**latex_escape(data))
    except Exception as exc:  # jinja/template errors
        return jsonify({"ok": False, "error": f"Template error: {exc}"}), 400

    tex_out = OUTPUT_DIR / f"{name}.tex"
    tex_out.write_text(rendered, encoding="utf-8")

    # 3) Compile to PDF.
    pdf = compile_pdf(tex_out, OUTPUT_DIR)
    if not pdf:
        return jsonify(
            {"ok": False, "error": "PDF compilation failed. Check LaTeX/template."}
        ), 500

    return jsonify({"ok": True, "pdf": f"/output/{pdf.name}", "saved": path.name})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
