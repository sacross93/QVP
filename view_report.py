import json
import argparse
import sys
import os
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

def display_report(file_path: str):
    """
    Reads a strategic report JSON file and prints its contents
    in a nicely formatted way to the terminal.
    """
    console = Console()

    # 1. 파일 존재 여부 확인
    if not os.path.exists(file_path):
        console.print(f"[bold red]🚨 ERROR: File not found at '{file_path}'[/bold red]")
        sys.exit(1)

    # 2. JSON 파일 로드
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        console.print(f"[bold red]🚨 ERROR: Could not decode JSON from '{file_path}'. The file might be corrupted.[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]🚨 ERROR: An unexpected error occurred while reading the file: {e}[/bold red]")
        sys.exit(1)

    # 3. 데이터 추출
    identifier = data.get("source_identifier", "N/A")
    briefing_notes = data.get("briefing_notes_markdown", "Briefing notes not found.")
    strategic_report = data.get("strategic_report_markdown", "Strategic report not found.")

    # 4. 보고서 출력
    console.print(Panel(f"[bold cyan]Strategic Report for: {identifier}[/bold cyan]", title="QVP Analysis Report", expand=False, border_style="blue"))

    console.print("\n\n" + "="*80, style="bold green")
    console.print("📄 1. 분석 브리핑 노트 (Briefing Notes)", style="bold green")
    console.print("="*80 + "\n", style="bold green")
    console.print(Markdown(briefing_notes))

    console.print("\n\n" + "="*80, style="bold blue")
    console.print("📈 2. 최종 전략 보고서 (Strategic Report)", style="bold blue")
    console.print("="*80 + "\n", style="bold blue")
    console.print(Markdown(strategic_report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="View a strategic report JSON file in a formatted way.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "report_file",
        type=str,
        help="Path to the strategic_report_...json file."
    )

    args = parser.parse_args()
    display_report(args.report_file) 