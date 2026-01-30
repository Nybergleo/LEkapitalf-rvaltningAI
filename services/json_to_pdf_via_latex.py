from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ----------------------------
#  LaTeX escaping (deterministic + safe)
# ----------------------------
_LATEX_REPL = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "%": r"\%",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

def latex_escape(s: str) -> str:
    # Deterministic escaping of all special chars.
    return "".join(_LATEX_REPL.get(ch, ch) for ch in s)


# ----------------------------
#  Schema validation
# ----------------------------
class SchemaError(ValueError):
    pass

def _require(obj: Dict[str, Any], key: str, typ: Union[type, Tuple[type, ...]]) -> Any:
    if key not in obj:
        raise SchemaError(f"Missing required key: {key}")
    val = obj[key]
    if not isinstance(val, typ):
        raise SchemaError(f"Key '{key}' must be {typ}, got {type(val)}")
    return val

def _optional(obj: Dict[str, Any], key: str, typ: Union[type, Tuple[type, ...]]) -> Any:
    if key not in obj:
        return None
    val = obj[key]
    if not isinstance(val, typ):
        raise SchemaError(f"Key '{key}' must be {typ}, got {type(val)}")
    return val

def validate_doc(doc: Dict[str, Any]) -> None:
    _require(doc, "meta", dict)
    _require(doc, "blocks", list)

    meta = doc["meta"]
    _require(meta, "title", str)
    _optional(meta, "author", str)
    _optional(meta, "date", str)

    for i, b in enumerate(doc["blocks"]):
        if not isinstance(b, dict):
            raise SchemaError(f"Block {i} must be an object")
        btype = _require(b, "type", str)

        if btype in ("h1", "h2", "h3", "p"):
            _require(b, "text", str)
        elif btype in ("bullets", "numbered"):
            items = _require(b, "items", list)
            if not all(isinstance(x, str) for x in items):
                raise SchemaError(f"Block {i} items must be strings")
        elif btype == "table":
            _require(b, "columns", list)
            _require(b, "rows", list)
            cols = b["columns"]
            rows = b["rows"]
            if not all(isinstance(c, str) for c in cols):
                raise SchemaError(f"Block {i} columns must be strings")
            if not all(isinstance(r, list) for r in rows):
                raise SchemaError(f"Block {i} rows must be arrays")
            for r in rows:
                if not all(isinstance(cell, str) for cell in r):
                    raise SchemaError(f"Block {i} row cells must be strings")
                if len(r) != len(cols):
                    raise SchemaError(
                        f"Block {i} row length {len(r)} != columns length {len(cols)}"
                    )
            _optional(b, "caption", str)
        elif btype == "pagebreak":
            # no extra fields
            pass
        else:
            raise SchemaError(f"Unknown block type at {i}: {btype}")


# ----------------------------
#  LaTeX rendering
# ----------------------------
LATEX_PREAMBLE = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[a4paper,margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{tabularx}
\usepackage{adjustbox}
\usepackage{xltabular}

\renewcommand{\arraystretch}{1.10}
\setlength{\tabcolsep}{4pt}

\setlist[itemize]{noitemsep, topsep=4pt}
\setlist[enumerate]{noitemsep, topsep=4pt}

\begin{document}
"""

def render_block(b: Dict[str, Any]) -> str:
    t = b["type"]

    if t == "h1":
        return f"\\section*{{{latex_escape(b['text'])}}}\n"
    if t == "h2":
        return f"\\subsection*{{{latex_escape(b['text'])}}}\n"
    if t == "h3":
        return f"\\subsubsection*{{{latex_escape(b['text'])}}}\n"
    if t == "p":
        # blank line after paragraph for LaTeX separation
        return f"{latex_escape(b['text'])}\n\n"

    if t == "bullets":
        items = b["items"]
        body = "\n".join(f"  \\item {latex_escape(x)}" for x in items)
        return "\\begin{itemize}\n" + body + "\n\\end{itemize}\n\n"

    if t == "numbered":
        items = b["items"]
        body = "\n".join(f"  \\item {latex_escape(x)}" for x in items)
        return "\\begin{enumerate}\n" + body + "\n\\end{enumerate}\n\n"

    if t == "table":
        cols: List[str] = b["columns"]
        rows: List[List[str]] = b["rows"]
        caption: Optional[str] = b.get("caption")

        n = len(cols)

        header = " & ".join(latex_escape(c) for c in cols) + r" \\"
        body = "\n".join(
            " & ".join(latex_escape(cell) for cell in r) + r" \\"
            for r in rows
        )

        # Column spec:
        # - first column is left-aligned and can wrap a bit
        # - remaining columns are X (auto-width + wrap)
        if n == 1:
            colspec = r">{\raggedright\arraybackslash}p{\textwidth}"
        else:
            colspec = r">{\raggedright\arraybackslash}p{0.18\textwidth} " + " ".join(
                [r">{\raggedright\arraybackslash}X" for _ in range(n - 1)]
            )

        table_tex = "\n".join([
            r"\begingroup\small",
            r"\setlength{\LTpre}{0pt}",
            r"\setlength{\LTpost}{0pt}",
            r"\begin{xltabular}{\textwidth}{" + colspec + r"}",
            r"\toprule",
            header,
            r"\midrule",
            r"\endfirsthead",
            r"\toprule",
            header,
            r"\midrule",
            r"\endhead",
            r"\midrule",
            r"\multicolumn{" + str(n) + r"}{c}{\small \textbf{Continued on next page}} \\",
            r"\midrule",
            r"\endfoot",
            r"\bottomrule",
            r"\endlastfoot",
            body,
            r"\end{xltabular}",
            r"\endgroup",
            "",
        ])



        if caption:
            return f"\\textbf{{{latex_escape(caption)}}}\n\n{table_tex}\n"
        return table_tex + "\n"


    if t == "pagebreak":
        return "\\clearpage\n"

    # validate_doc prevents reaching here
    raise SchemaError(f"Unhandled block type: {t}")


def render_document(doc: Dict[str, Any]) -> str:
    meta = doc["meta"]
    title = latex_escape(meta["title"])
    author = latex_escape(meta.get("author", ""))
    date = latex_escape(meta.get("date", ""))

    title_lines = [
        f"\\title{{{title}}}",
        f"\\author{{{author}}}" if author else "\\author{}",
        f"\\date{{{date}}}" if date else "\\date{}",
        "\\maketitle\n",
    ]

    blocks = "".join(render_block(b) for b in doc["blocks"])
    return LATEX_PREAMBLE + "\n".join(title_lines) + blocks + "\n\\end{document}\n"


# ----------------------------
#  Optional compilation
# ----------------------------
def compile_pdf(tex_path: Path, engine: str = "tectonic") -> Path:
    """
    engine: 'tectonic' (recommended) or 'pdflatex'
    """
    tex_path = tex_path.resolve()
    out_dir = tex_path.parent

    if engine == "tectonic":
        exe = shutil.which("tectonic")
        if not exe:
            raise RuntimeError(
                "tectonic not found on PATH. Install it or use engine='pdflatex'."
            )
        # Tectonic writes PDF alongside input by default when using -o dir
        cmd = [exe, str(tex_path), "--outdir", str(out_dir)]
    elif engine == "pdflatex":
        exe = shutil.which("pdflatex")
        if not exe:
            raise RuntimeError(
                "pdflatex not found on PATH. Install TeX Live/MiKTeX or use engine='tectonic'."
            )
        cmd = [exe, "-interaction=nonstopmode", "-halt-on-error", str(tex_path)]
    else:
        raise ValueError("engine must be 'tectonic' or 'pdflatex'")

    proc = subprocess.run(cmd, cwd=str(out_dir), capture_output=True, text=True)
    if proc.returncode != 0:
        log = proc.stdout + "\n" + proc.stderr
        raise RuntimeError(f"LaTeX compilation failed.\n\nCommand: {cmd}\n\n{log}")

    pdf_path = tex_path.with_suffix(".pdf")
    if not pdf_path.exists():
        raise RuntimeError("Compilation succeeded but PDF was not produced.")
    return pdf_path



def write_pdf_from_json_text(
    json_text: str,
    basename: str,
    out_root: Path = Path("./out"),
    engine: str = "pdflatex",
) -> Path:
    out_dir = out_root / basename
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Parse JSON
    try:
        doc = json.loads(json_text)
    except json.JSONDecodeError as e:
        raw_path = out_dir / f"{basename}.raw.txt"
        raw_path.write_text(json_text, encoding="utf-8")
        raise RuntimeError(
            f"Model output was not valid JSON. Saved raw output to: {raw_path}\n{e}"
        )

    if not isinstance(doc, dict):
        raise SchemaError("Top-level JSON must be an object")

    # 2) Validate schema
    validate_doc(doc)

    # 3) Save JSON (repro/debug)
    json_path = out_dir / f"{basename}.json"
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4) Render LaTeX + write .tex
    tex = render_document(doc)
    tex_path = out_dir / f"{basename}.tex"
    tex_path.write_text(tex, encoding="utf-8")

    # 5) Compile to PDF
    pdf_path = compile_pdf(tex_path, engine=engine)
    return pdf_path



def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Deterministically render JSON into LaTeX (and optionally PDF)."
    )
    ap.add_argument("json_file", type=Path, nargs="?", default=Path("./out/test.json"))
    ap.add_argument("--tex-out", type=Path, default=None)
    ap.add_argument("--pdf", action="store_true", help="Compile to PDF")
    ap.add_argument("--engine", choices=["tectonic", "pdflatex"], default="tectonic")
    args = ap.parse_args()

    json_path: Path = args.json_file
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path.resolve()}")

    doc = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SchemaError("Top-level JSON must be an object")

    validate_doc(doc)

    tex = render_document(doc)

    tex_out = args.tex_out or json_path.with_suffix(".tex")
    tex_out.parent.mkdir(parents=True, exist_ok=True)
    tex_out.write_text(tex, encoding="utf-8")

    print(f"Wrote LaTeX: {tex_out}")

    
    pdf_path = compile_pdf(tex_out, "pdflatex")
    print(f"Wrote PDF: {pdf_path}")


if __name__ == "__main__":
    main()
