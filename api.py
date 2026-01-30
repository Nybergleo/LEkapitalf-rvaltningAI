from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
import time
import zipfile


from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from analysis_client import compare_reports, keyword_analysis, individual_analysis
from json_to_pdf_via_latex import write_pdf_from_json_text




app = FastAPI(title="LE Report Analyzer")

# Keep outputs in a folder so downloads work even after the request ends.
OUT_DIR = Path("./out_web")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Serve CSS/JS under /static
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")


def _save_uploads_to_temp(files: List[UploadFile]) -> List[Path]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    tmpdir = Path(tempfile.mkdtemp(prefix="uploads_"))
    paths: List[Path] = []

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Not a PDF: {f.filename}")

        dst = tmpdir / Path(f.filename).name
        with dst.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        paths.append(dst)

    return paths


def _keywords_to_user_input(keywords: str) -> str:
    # Your CLI used a specific “KEYWORDS TO ANALYZE:” preface
    # (same shape, just non-interactive).
    lines = [k.strip() for k in keywords.splitlines() if k.strip()]
    if not lines:
        return "KEYWORDS TO ANALYZE:\n- (none)\n"
    return "KEYWORDS TO ANALYZE:\n" + "\n".join(f"- {k}" for k in lines) + "\n"


@app.post("/run")
def run(
    mode: str = Form(...),                       # compare | keywords | individual
    engine: str = Form("tectonic"),              # tectonic | pdflatex
    keywords: str = Form(""),
    files: List[UploadFile] = File(...),
):
    # Basic validation
    if mode not in {"compare", "keywords", "individual"}:
        raise HTTPException(status_code=400, detail="Invalid mode.")
    if engine not in {"tectonic", "pdflatex"}:
        raise HTTPException(status_code=400, detail="Invalid engine.")
    if mode == "keywords" and not keywords.strip():
        raise HTTPException(status_code=400, detail="Provide keywords for keyword mode.")

    # Save PDFs to a temp folder
    pdf_paths = _save_uploads_to_temp(files)

    try:
        if mode == "compare":
            json_text =  compare_reports(pdf_paths)
            pdf_path = write_pdf_from_json_text(
                json_text,
                basename="compare_reports",
                out_root=OUT_DIR,
                engine=engine,
            )
            print(f"PDF generated to {pdf_path}")
            return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)

        if mode == "keywords":
            user_input = _keywords_to_user_input(keywords)
            json_text = keyword_analysis(pdf_paths, user_input)
            pdf_path = write_pdf_from_json_text(
                json_text,
                basename="keyword_analysis",
                out_root=OUT_DIR,
                engine=engine,
            )
            print(f"PDF generated")
            return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)

                # individual: produce one PDF per input and return a ZIP
        if mode == "individual":
            generated_pdfs: List[Path] = []

            for path in pdf_paths:
                json_text = individual_analysis([path])
                basename = f"individual_analysis_{path.stem}"
                pdf_path = write_pdf_from_json_text(
                    json_text,
                    basename=basename,
                    out_root=OUT_DIR,
                    engine=engine,
                )
                generated_pdfs.append(pdf_path)
                print(f"PDF generated")

            # If only one file, return it directly (nice UX)
            if len(generated_pdfs) == 1:
                pdf_path = generated_pdfs[0]
                return FileResponse(
                    pdf_path,
                    media_type="application/pdf",
                    filename=pdf_path.name,
                )

            # Otherwise zip them
            zip_name = f"individual_analysis_{int(time.time())}.zip"
            zip_path = OUT_DIR / zip_name

            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for pdf in generated_pdfs:
                    # arcname makes the file name inside the zip clean
                    zf.write(pdf, arcname=pdf.name)

            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename=zip_name,
            )

    finally:
        # Cleanup uploaded tempdir
        # (we keep outputs in OUT_DIR so downloads still work)
        tmpdir = pdf_paths[0].parent if pdf_paths else None
        if tmpdir and tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)

