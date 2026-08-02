# Resume Builder

Generate a polished PDF resume from a **LaTeX template** and a structured
**YAML/JSON** data file. Keep your content (data) separate from your design
(template) — swap templates without touching your content.

## How it works

1. You provide a LaTeX template with Jinja2 placeholders.
2. You keep your resume content in a YAML (or JSON) file.
3. `build.py` renders the template with your data and compiles it to a PDF.

## Setup

```bash
cd ~/Desktop/resume-builder
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

To produce PDFs you also need a LaTeX engine (any one of these):

```bash
# macOS
brew install tectonic            # lightweight, recommended
# or the full distribution:
brew install --cask mactex-no-gui

# Linux
sudo apt-get install texlive-xetex
```

## Usage

```bash
python build.py --data data/example.yaml --template templates/modern.tex
```

Output goes to `output/` as both `.tex` and `.pdf`.

Useful flags:

- `--no-pdf` — only render the `.tex` (no LaTeX engine required)
- `--output DIR` — change the output directory
- `--no-escape` — disable automatic escaping of LaTeX special characters

## Using your own template

Templates are ordinary `.tex` files with LaTeX-safe Jinja2 delimiters so they
never clash with LaTeX braces:

| Purpose   | Syntax                                   |
| --------- | ---------------------------------------- |
| Variable  | `\VAR{ name }`                           |
| Block     | `\BLOCK{ for job in experience } ... \BLOCK{ endfor }` |
| Comment   | `\#{ ... }`                              |

Any key in your data file is available in the template. Add your `.tex` file to
`templates/` and point `--template` at it.

## Project layout

```
resume-builder/
├── build.py            # CLI: render template + data -> PDF
├── requirements.txt
├── templates/
│   └── modern.tex      # example template (edit or add your own)
├── data/
│   └── example.yaml    # your resume content
└── output/             # generated .tex and .pdf
```
