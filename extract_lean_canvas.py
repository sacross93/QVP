import json
import re
import os
import argparse # 인자 처리를 위해 추가
from glob import glob
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. LLM 설정 ---
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

# --- 2. Lean Canvas 추출 체인 생성 ---

def create_extractor_chain(llm):
    """입력된 보고서 텍스트에서 Lean Canvas 9가지 요소를 추출하여 JSON으로 반환하는 체인을 생성합니다."""
    prompt_template = """
You are an expert business analyst AI specializing in **startups**. Your task is to read the provided final analysis report and extract the information for the 9 blocks of the Lean Canvas.
You must synthesize the information for each block into a concise summary and format the output as a single JSON object.

**Lean Canvas Components:**
1.  **Problem**: The top 1-3 problems your customers face.
2.  **Customer Segments**: Your target customers, especially early adopters.
3.  **Unique Value Proposition**: Your unique, compelling message that states why you are different and worth buying.
4.  **Solution**: The top 3 features of your product/service that solve the problems.
5.  **Channels**: Your path to customers (e.g., marketing, sales, partners).
6.  **Revenue Streams**: How you will make money (e.g., sales, subscription, ads).
7.  **Cost Structure**: Your major costs (e.g., customer acquisition, R&D, salaries).
8.  **Key Metrics**: The key activities you measure to track success.
9.  **Unfair Advantage**: Something that cannot be easily copied or bought by competitors.

**Input Report:**
---
{report_text}
---

**Instructions:**
Based on the report, fill in the values for each of the 9 Lean Canvas keys. The values should be strings containing a concise summary for that block, framed for a **startup context** (e.g., focus on early adopters, lean cost structures, and unique, defensible advantages).
Provide your answer as a single, valid JSON object. Do not include any other text or markdown formatting.
please write in korean.

**Example Output Format:**
```json
{{
  "problem": "A summary of the key customer problems.",
  "customer_segments": "A description of the target customer segments.",
  "unique_value_proposition": "A clear statement of the unique value.",
  "solution": "A summary of the top 3 solution features.",
  "channels": "A list of paths to reach customers.",
  "revenue_streams": "A description of the revenue model.",
  "cost_structure": "A summary of the main cost drivers.",
  "key_metrics": "A list of key metrics to track.",
  "unfair_advantage": "A description of the sustainable competitive advantage."
}}
```
"""
    prompt = PromptTemplate.from_template(prompt_template)
    # LLM의 출력을 문자열로 받기 위해 StrOutputParser 사용
    return prompt | llm | StrOutputParser()

def process_single_report(report_file):
    """단일 보고서 파일에서 Lean Canvas를 추출하는 메인 로직"""
    llm = ChatOllama(
        model="qwen3:32b",
        base_url="http://192.168.120.102:11434",
        temperature=0
    )
    extractor_chain = create_extractor_chain(llm)

    print(f"\n\n{'='*50}\nProcessing file: {report_file}\n{'='*50}")
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        report_text = report_data.get("final_competitive_report", "")
        if not report_text:
            print(f"Skipping {report_file} due to missing 'final_competitive_report' key.")
            return
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing {report_file}: {e}")
        return

    print("🤖 Starting Lean Canvas extraction...")
    try:
        raw_output = extractor_chain.invoke({"report_text": report_text})
        think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
        cleaned_output = think_pattern.sub("", raw_output).strip()
        json_match = re.search(r'\{.*\}', cleaned_output, re.DOTALL)
        if not json_match:
            raise json.JSONDecodeError("No JSON object found in the cleaned output", cleaned_output, 0)
        json_string = json_match.group(0)
        lean_canvas_json = json.loads(json_string)
        
        print("✅ Lean Canvas data extracted successfully.")

        base_name = os.path.basename(report_file)
        identifier = base_name.replace('competitive_analysis_report_', '').replace('.json', '')
        output_path = f'result/lean_canvas_{identifier}.json'

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(lean_canvas_json, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Lean Canvas JSON saved to: {output_path}")

    except Exception as e:
        print(f"🚨 An error occurred during the extraction process: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract a Lean Canvas from a single competitive analysis report.")
    parser.add_argument("report_file", type=str, help="The path to the input competitive_analysis_report JSON file.")
    args = parser.parse_args()
    
    if not os.path.exists(args.report_file):
        print(f"🚨 ERROR: Input file not found at '{args.report_file}'")
    else:
        process_single_report(args.report_file) 