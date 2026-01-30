from __future__ import annotations

from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

client = OpenAI()

# Project root is one level above /services
BASE_DIR = Path(__file__).resolve().parents[1]  # /app
PROMPTS_DIR = BASE_DIR / "prompts"


def load_prompt(prompt_filename: str) -> str:
    prompt_path = PROMPTS_DIR / prompt_filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def upload_pdfs(pdf_paths):
    pdf_paths = [Path(p) for p in pdf_paths]
    if not pdf_paths:
        raise FileNotFoundError("No PDFs provided.")

    missing = [p for p in pdf_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"These PDFs do not exist: {missing}")

    file_ids = []
    for pdf in tqdm(pdf_paths, desc="Uploading PDFs"):
        with open(pdf, "rb") as f:
            created = client.files.create(file=f, purpose="user_data")
        file_ids.append(created.id)
    return file_ids


def run_prompt_over_reports(
    prompt_filename: str,
    status: str,
    pdf_paths,  # passed in by caller
    user_input: str | None = None,
):
    prompt_text = load_prompt(prompt_filename)
    file_ids = upload_pdfs(pdf_paths)

    if user_input:
        prompt_text = user_input.rstrip() + "\n\n" + prompt_text.lstrip()

    content = [{"type": "input_file", "file_id": fid} for fid in file_ids]
    content.append({"type": "input_text", "text": prompt_text})

    print(status)

    system_text = """
ABSOLUTE RULES:
- Output MUST be valid JSON only. No markdown. No extra text.
- Output MUST contain only plain ASCII characters. Do not use Unicode (no “ ” ’ … – — • ₂ etc).
Use replacements: "quotes", 'apostrophe', "...", "-", "CO2".
- JSON MUST follow the schema exactly:
{ "meta": { "title": str, "author": str, "date": str }, "blocks": [ ... ] }
- Allowed block types: h1, h2, h3, p, bullets, numbered, table, pagebreak.
- For bullets/numbered blocks: always include "items": [string, ...]. Never use "text" for these.
- For h1/h2/h3/p blocks: always include "text": string.
- For table blocks: always include "columns": [string,...] and "rows": [[string,...],...].
- If unsure how to format something, use a "p" block (never invent new block types).
""".strip()

    response = client.responses.create(
        model="gpt-5",
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": system_text}]},
            {"role": "user", "content": content},
        ],
    )
    return response.output_text


# Convenience wrappers now REQUIRE pdf_paths
def compare_reports(pdf_paths):
    return run_prompt_over_reports("CompareReports.txt", "Comparing reports...", pdf_paths)


def keyword_analysis(pdf_paths, user_input: str):
    return run_prompt_over_reports(
        "KeyWordAnalysis.txt", "Running keyword analysis...", pdf_paths, user_input
    )


def individual_analysis(pdf_paths):
    return run_prompt_over_reports("IndividualAnalysis.txt", "Running individual analyses...", pdf_paths)
