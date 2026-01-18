from __future__ import annotations

from pathlib import Path

from tqdm import tqdm

from AI_test import compare_reports, keyword_analysis, individual_analysis
from json_to_pdf_via_latex import write_pdf_from_json_text

OUT_DIR = Path("./out")
REPORTS_DIR = Path("./reports")


def keywords_inputformatting() -> str:
    keywords_input = "KEYWORDS TO ANALYZE:\n"
    while True:
        keyword = input(
            "Write a keyword and press enter.\n"
            "If you are done, press enter with no input.\n> "
        ).strip()

        if keyword == "":
            break

        keywords_input += f"- {keyword}\n"
    return keywords_input


def _list_pdfs(reports_dir: Path) -> list[Path]:
    pdfs = sorted(reports_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in: {reports_dir.resolve()}")
    return pdfs


def choose_pdfs(reports_dir: Path = REPORTS_DIR) -> list[Path]:
    """
    Interactive PDF selection.

    Options:
      - Enter: use ALL PDFs
      - "1,3,5": choose specific indices
      - "2-4": choose a range
      - "1,2-4,7": mix
    """
    pdfs = _list_pdfs(reports_dir)

    print("\nAvailable PDFs:")
    for i, p in enumerate(pdfs, start=1):
        print(f"{i}) {p.name}")

    s = input(
        "\nSelect PDFs by number (e.g. 1,3,5 or 2-4). "
        "Press Enter for ALL.\n> "
    ).strip()

    if s == "":
        return pdfs

    selected: set[int] = set()

    parts = [x.strip() for x in s.split(",") if x.strip()]
    for part in parts:
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            if not a.isdigit() or not b.isdigit():
                raise ValueError(f"Invalid range: '{part}'")
            lo, hi = int(a), int(b)
            if lo > hi:
                lo, hi = hi, lo
            for idx in range(lo, hi + 1):
                selected.add(idx)
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid selection: '{part}'")
            selected.add(int(part))

    chosen: list[Path] = []
    for idx in sorted(selected):
        if idx < 1 or idx > len(pdfs):
            raise ValueError(f"Selection out of range: {idx} (valid: 1-{len(pdfs)})")
        chosen.append(pdfs[idx - 1])

    return chosen


def home_menu() -> None:
    tasks = ["Compare reports.", "Analyze key-words.", "Individual Analysis."]

    print(f"Welcome to the AI analyzer prototype!\nPlease choose a task 1-{len(tasks)}.")
    for i, task in enumerate(tasks):
        print(f"{i + 1}) {task}")

    chosen_task = input("> ").strip()

    if chosen_task not in {"1", "2", "3"}:
        print("Invalid selection.")
        return

    try:
        pdf_paths = choose_pdfs(REPORTS_DIR)
    except Exception as e:
        print(f"PDF selection failed: {e}")
        return

    if chosen_task == "1":
        json_text = compare_reports(pdf_paths)
        print("Response received. Creating PDF.")
        pdf = write_pdf_from_json_text(json_text, basename="compare_reports")
        print(f"Wrote PDF: {pdf}")

    elif chosen_task == "2":
        user_input = keywords_inputformatting()
        json_text = keyword_analysis(pdf_paths, user_input)
        print("Response received. Creating PDF.")
        pdf = write_pdf_from_json_text(json_text, basename="keyword_analysis")
        print(f"Wrote PDF: {pdf}")

    elif chosen_task == "3":
        for path in pdf_paths:
            json_text = individual_analysis([path])
            print("Response received. Creating PDF.")

            basename = f"individual_analysis_{path.stem}"
            pdf = write_pdf_from_json_text(json_text, basename=basename)

            print(f"Wrote PDF: {pdf}")


def main() -> None:
    home_menu()


if __name__ == "__main__":
    main()
