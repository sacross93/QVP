import json
import markdown
import argparse
import os

def convert_json_to_html(json_path: str):
    """
    마크다운 콘텐츠가 포함된 JSON 파일을 읽어, 스타일이 적용된 HTML 보고서로 변환 후 저장합니다.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다 - {json_path}")
        return
    except json.JSONDecodeError:
        print(f"오류: JSON 형식이 올바르지 않습니다 - {json_path}")
        return

    briefing_notes_md = data.get("briefing_notes_markdown", "")
    strategic_report_md = data.get("strategic_report_markdown", "")

    # 마크다운 필드를 HTML로 변환
    # 확장 기능으로 테이블, 각주 등을 지원하도록 설정
    extensions = ['extra', 'nl2br', 'sane_lists', 'fenced_code', 'tables']
    briefing_notes_html = markdown.markdown(briefing_notes_md, extensions=extensions) if briefing_notes_md else ""
    strategic_report_html = markdown.markdown(strategic_report_md, extensions=extensions) if strategic_report_md else ""

    css_style = """
    body {
        font-family: 'Malgun Gothic', '맑은 고딕', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        line-height: 1.7;
        color: #343a40;
        background-color: #f8f9fa;
        margin: 0;
        padding: 2rem;
    }
    .container {
        max-width: 960px;
        margin: 0 auto;
        background: #ffffff;
        padding: 2rem 3rem;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600;
        color: #2c3e50;
        margin-top: 2.5rem;
        margin-bottom: 1.5rem;
    }
    h1 {
        font-size: 2.5rem;
        text-align: center;
        color: #1a5276;
        border-bottom: none;
        margin-bottom: 2rem;
    }
    h2 {
        font-size: 2rem;
        border-bottom: 2px solid #eaecee;
        padding-bottom: 0.5rem;
    }
    h3 {
        font-size: 1.6rem;
        color: #34495e;
    }
    p {
        margin-bottom: 1rem;
    }
    strong {
        color: #2980b9;
        font-weight: 600;
    }
    hr {
        border: none;
        height: 1px;
        background-color: #d6dbdf;
        margin: 3rem 0;
    }
    ul {
        list-style: none;
        padding-left: 0;
    }
    li {
        position: relative;
        padding-left: 25px;
        margin-bottom: 10px;
    }
    li::before {
        content: '■';
        position: absolute;
        left: 0;
        color: #2980b9;
        font-weight: bold;
    }
    ul ul {
        margin-top: 10px;
        padding-left: 20px;
    }
    ul ul li::before {
        content: '□';
        color: #7f8c8d;
    }
    """

    # 전체 HTML 구조 생성
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>전략 분석 보고서</title>
    <style>
        {css_style}
    </style>
</head>
<body>
    <div class="container">
        {briefing_notes_html}
        {strategic_report_html}
    </div>
</body>
</html>
"""

    # 출력 파일 이름 결정 및 저장
    output_filename = os.path.splitext(os.path.basename(json_path))[0] + ".html"
    output_path = os.path.join(os.path.dirname(json_path), output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML 보고서가 성공적으로 생성되었습니다: {output_path}")

if __name__ == "__main__":
    # 변환할 JSON 파일의 경로를 여기에 직접 지정합니다.
    json_file_path = "bm_result/strategic_report_ROBOS_20250611_163629.json"

    if not os.path.isfile(json_file_path):
        print(f"오류: 파일을 찾을 수 없습니다 - {json_file_path}")
    else:
        convert_json_to_html(json_file_path) 