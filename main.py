from __future__ import annotations

from pathlib import Path
from AI_test import compare_reports, keyword_analysis, individual_analysis
from json_to_pdf_via_latex import  write_pdf_from_json_text


OUT_DIR = Path("./out")



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


def home_menu() -> None:
    tasks = ["Compare reports.", "Analyze key-words.", "Individual Analysis."]
    print(f"Welcome to the AI analyzer prototype!\nPlease choose a task 1-{len(tasks)}.")
    for i, task in enumerate(tasks):
        print(f"{i+1}) {task}")

    chosen_task = input("> ").strip()

    if chosen_task == "1":
        json_text = compare_reports()
        print("Response recived. Creating PDF.")
        pdf = write_pdf_from_json_text(json_text, basename="compare_reports")
        print(f"[OK] Wrote PDF: {pdf}")

    elif chosen_task == "2":
        user_input = keywords_inputformatting()
        json_text = keyword_analysis(user_input)
        print("Response recived. Creating PDF.")
        pdf = write_pdf_from_json_text(json_text, basename="keyword_analysis")
        print(f"[OK] Wrote PDF: {pdf}")

    elif chosen_task == "3":
        json_text = individual_analysis()
        print("Response recived. Creating PDF.")
        pdf = write_pdf_from_json_text(json_text, basename="individual_analysis")
        print(f"[OK] Wrote PDF: {pdf}")

    else:
        print("[ERROR] Invalid selection.")


def main() -> None:
    home_menu()


if __name__ == "__main__":
    main()
