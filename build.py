#!/usr/bin/env python3
r"""Resume Builder.

Render a LaTeX resume template with data from a YAML/JSON file and
compile it to a PDF.

Usage:
    python build.py --data data/example.yaml --template templates/modern.tex
    python build.py --data data/example.yaml --template templates/modern.tex --no-pdf

The template is a normal .tex file that uses Jinja2 placeholders with
LaTeX-friendly delimiters so they do not clash with LaTeX's own braces:

    variables:   \VAR{ name }
    blocks:      \BLOCK{ for job in experience } ... \BLOCK{ endfor }
    comments:    \#{ this is a comment }
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:  # pragma: no cover
    print("Missing dependency 'jinja2'. Run: pip install -r requirements.txt")
    sys.exit(1)


# LaTeX-safe Jinja2 environment. LaTeX uses { } heavily, so we swap the
# default Jinja delimiters for ones that never appear in normal LaTeX.
def make_env(template_dir: Path) -> Environment:
    return Environment(
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        line_statement_prefix="%%",
        line_comment_prefix="%#",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        undefined=StrictUndefined,
        loader=FileSystemLoader(str(template_dir)),
    )


# Characters that must be escaped so user data does not break the LaTeX build.
_LATEX_SPECIALS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}


def latex_escape(value):
    """Escape LaTeX special characters in strings, recursively for containers."""
    if isinstance(value, str):
        return "".join(_LATEX_SPECIALS.get(c, c) for c in value)
    if isinstance(value, list):
        return [latex_escape(v) for v in value]
    if isinstance(value, dict):
        return {k: latex_escape(v) for k, v in value.items()}
    return value


def load_data(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            print("Missing dependency 'pyyaml'. Run: pip install -r requirements.txt")
            sys.exit(1)
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    print(f"Unsupported data format: {path.suffix} (use .yaml, .yml or .json)")
    sys.exit(1)


def find_compiler() -> str | None:
    for candidate in ("tectonic", "xelatex", "pdflatex"):
        if shutil.which(candidate):
            return candidate
    return None


def compile_pdf(tex_path: Path, output_dir: Path) -> Path | None:
    compiler = find_compiler()
    if compiler is None:
        print(
            "No LaTeX compiler found (tectonic/xelatex/pdflatex).\n"
            "The rendered .tex was written; install one to produce a PDF:\n"
            "  macOS:  brew install --cask mactex-no-gui   (or: brew install tectonic)\n"
            "  Linux:  sudo apt-get install texlive-xetex"
        )
        return None

    if compiler == "tectonic":
        cmd = [compiler, "--outdir", str(output_dir), str(tex_path)]
    else:
        cmd = [
            compiler,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={output_dir}",
            str(tex_path),
        ]

    # pdflatex/xelatex need two passes to resolve references; tectonic handles it.
    passes = 1 if compiler == "tectonic" else 2
    for _ in range(passes):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{compiler} failed:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
            return None

    pdf_path = output_dir / (tex_path.stem + ".pdf")
    return pdf_path if pdf_path.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a resume from a LaTeX template.")
    parser.add_argument("--data", required=True, help="Path to YAML/JSON data file.")
    parser.add_argument("--template", required=True, help="Path to LaTeX template file.")
    parser.add_argument("--output", default="output", help="Output directory (default: output).")
    parser.add_argument(
        "--no-escape",
        action="store_true",
        help="Do not auto-escape LaTeX special characters in data.",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Only render the .tex file; skip PDF compilation.",
    )
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    template_path = Path(args.template).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        return 1
    if not template_path.exists():
        print(f"Template file not found: {template_path}")
        return 1

    data = load_data(data_path)
    if not args.no_escape:
        data = latex_escape(data)

    env = make_env(template_path.parent)
    template = env.get_template(template_path.name)
    rendered = template.render(**data)

    tex_out = output_dir / (data_path.stem + ".tex")
    tex_out.write_text(rendered, encoding="utf-8")
    print(f"Rendered LaTeX -> {tex_out}")

    if args.no_pdf:
        return 0

    pdf = compile_pdf(tex_out, output_dir)
    if pdf:
        print(f"Built PDF -> {pdf}")
        return 0
    return 0 if find_compiler() is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
