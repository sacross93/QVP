import json
import argparse
import sys
import os

def save_as_markdown(json_file_path: str):
    """
    Reads a strategic report JSON file and saves its contents
    as a single, well-formatted Markdown file.
    """
    # 1. 파일 존재 여부 확인
    if not os.path.exists(json_file_path):
        print(f"🚨 ERROR: File not found at '{json_file_path}'")
        sys.exit(1)

    # 2. 출력 파일 경로 설정
    output_directory = os.path.dirname(json_file_path)
    base_name = os.path.splitext(os.path.basename(json_file_path))[0]
    output_md_path = os.path.join(output_directory, f"{base_name}.md")

    # 3. JSON 파일 로드
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"🚨 ERROR: Failed to read or parse JSON file: {e}")
        sys.exit(1)

    # 4. 데이터 추출
    identifier = data.get("source_identifier", "N/A")
    briefing_notes = data.get("briefing_notes_markdown", "Briefing notes not found.")
    strategic_report = data.get("strategic_report_markdown", "Strategic report not found.")

    # 5. 전체 마크다운 콘텐츠 생성
    full_markdown_content = f"""# 📈 Strategic Report: {identifier}

---

## 📄 1. 분석 브리핑 노트 (Briefing Notes)

{briefing_notes}

---

## 🚀 2. 최종 전략 보고서 (Strategic Report)

{strategic_report}
"""

    # 6. 마크다운 파일로 저장
    try:
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(full_markdown_content)
        print(f"✅ Successfully converted report to Markdown.")
        print(f"   - Saved to: {output_md_path}")
    except Exception as e:
        print(f"🚨 ERROR: Failed to save Markdown file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a strategic report JSON file to a Markdown file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "report_file",
        type=str,
        help="Path to the strategic_report_...json file to convert."
    )

    args = parser.parse_args()
    save_as_markdown(args.report_file) 