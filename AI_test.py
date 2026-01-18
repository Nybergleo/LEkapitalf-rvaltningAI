from pathlib import Path
from openai import OpenAI
from tqdm import tqdm

### Helpers ###

client = OpenAI()

def load_inputs(prompt_filename: str):
    base = Path(__file__).resolve().parent
    reports_dir = base / "reports"
    prompts_dir = base / "prompts"

    pdf_paths = sorted(reports_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found in: {reports_dir}")

    prompt_path = prompts_dir / prompt_filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    prompt_text = prompt_path.read_text(encoding="utf-8")
    return pdf_paths, prompt_text


def upload_pdfs(pdf_paths):
    file_ids = []
    for pdf in tqdm(pdf_paths, desc="Uploading PDFs"):
        with open(pdf, "rb") as f:
            created = client.files.create(file=f, purpose="user_data")
        file_ids.append(created.id)
    return file_ids

### Helpers end ###


# General prompting via pdfs and txt framework
def run_prompt_over_reports(prompt_filename: str, status: str, user_input: str | None = None):
    pdf_paths, prompt_text = load_inputs(prompt_filename)
    file_ids = upload_pdfs(pdf_paths)

    # Prepend user-provided text (e.g. keywords) before the prompt
    if user_input:
        prompt_text = user_input.rstrip() + "\n\n" + prompt_text.lstrip()

    content = [{"type": "input_file", "file_id": fid} for fid in file_ids]
    content.append({"type": "input_text", "text": prompt_text})

    print(status)

    #TODO: actually fix unicode characters.

    #This is a quickfix for unicode chars!

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
    """



    response = client.responses.create(
        model="gpt-5-mini",
        input=[{"role": "system", "content": [{"type": "input_text", "text": system_text.strip()}]},{"role": "user", "content": content}],
    )
    return response.output_text



#The different prompt functions
def compare_reports():
    return run_prompt_over_reports("CompareReports.txt", "Comparing reports...")


def keyword_analysis(user_input: str):
    return run_prompt_over_reports("KeywordAnalysis.txt", "Running keyword analysis...", user_input)


def individual_analysis():
    return run_prompt_over_reports("IndividualAnalysis.txt", "Running individual analyses...")


def main():
    print("Comparing reports")
    compare_reports()

    print("Key-words test")
    user_input = "KEYWORDS TO ANALYZE:\n- pricing\n- volume\n- operating margin\n- order intake\n- free cash flow\n- guidance\n"
    keyword_analysis(user_input)

    print("Running individual analysis")
    individual_analysis()






if __name__ == "__main__":
    main()