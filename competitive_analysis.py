import json
import re
import os
import time
import argparse # 인자 처리를 위해 추가
import sys
from glob import glob
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import Tool, create_react_agent, AgentExecutor
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

# --- 1. LLM 및 도구 설정 ---
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

search = DuckDuckGoSearchResults()

def search_with_delay(query: str) -> str:
    """사용량 제한을 피하기 위해 검색 전에 지연 시간을 추가하는 래퍼 함수입니다."""
    print(f"\n> [Executor] 2초 대기 후 검색 실행: {query}")
    time.sleep(2)
    return search.run(query)

search_tool = Tool(
    name="web_search",
    func=search_with_delay,
    description="A wrapper around DuckDuckGo Search. Useful for finding specific information about companies, markets, or technologies. Input should be a focused search query.",
)

# --- 2. 핵심 모듈 (Planner, Executor, Synthesizer) 생성 ---

def create_planner_chain(llm):
    """입력 보고서를 분석하여 상세한 조사 계획을 수립하는 체인을 생성합니다."""
    prompt_template = """
You are a strategic planning AI specializing in **startup strategy**. Your task is to read the provided company analysis report and create a detailed, actionable research plan to perform a competitive analysis and create a Lean Canvas.

**Input Report:**
{report_text}

---
Based on the report, identify the key competitors and any missing information needed to complete the tasks below. Then, generate a JSON list of research tasks.

**Analysis Goals:**
1.  **Competitive Analysis:** Identify 2-3 **startup competitors**. For each, find their Business Model, Pricing, Key Features, and Target Customers. If the initial report lists large corporations (e.g., Google, Tesla), you MUST create new tasks to find startup alternatives. For example, search for "startup competitors to [Large Competitor Name]" or "top startups in [market segment]".
2.  **Lean Canvas:** Gather information for the 9 blocks of the Lean Canvas for our company, from a startup's perspective.

**Task Generation Rules:**
- For each piece of information needed, create a distinct task object.
- Each task should be a specific, answerable question that can be researched with a web search.
- For competitors, create separate tasks for each piece of information (e.g., one task for "KUKA's Business Model", another for "KUKA's Pricing").
- If the report already contains sufficient information for a topic, note it in the task description and suggest a verification search.

**Output Format:**
Provide your answer as a single, valid JSON array of objects. Each object must have "task_id", "task_type" (e.g., "Competitor Research", "Lean Canvas: Problem", "Market Research"), and "query" (the specific search query to use).

**Example Output:**
```json
[
  {{
    "task_id": 1,
    "task_type": "Competitor Identification",
    "query": "Top startup competitors in the [specific market segment] market"
  }},
  {{
    "task_id": 2,
    "task_type": "Competitor Research",
    "query": "Business model of [Identified Competitor Name]"
  }},
  {{
    "task_id": 3,
    "task_type": "Lean Canvas: Problem",
    "query": "What are the key customer problems addressed by [Our Company's technology/product]?"
  }}
]
```
"""
    prompt = PromptTemplate.from_template(prompt_template)
    return prompt | llm | JsonOutputParser()

def create_executor_agent(llm, tools):
    """단일 조사 작업을 수행하고 결과를 반환하는 에이전트를 생성합니다."""
    prompt_template = """
You are a focused research agent. Your ONLY job is to execute the single task provided to you using the `web_search` tool and return a concise answer.

**Your Task:**
{task_query}

**Available Tools:**
{tools}

**Instructions:**
1. Use the `web_search` tool (one of [{tool_names}]) to find the answer to the task query.
2. Synthesize the search results into a brief, clear answer (2-3 sentences).
3. Provide the source URL for the most relevant piece of information.

{agent_scratchpad}

---
**CRITICAL: Your final output must be just the answer text and the source. Do not add any other commentary.**

Final Answer: [Your synthesized answer text. Source: (URL)]
"""
    prompt = PromptTemplate.from_template(prompt_template)
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )

def create_synthesizer_chain(llm):
    """모든 정보를 종합하여 최종 경쟁 분석 보고서를 작성하는 체인을 생성합니다."""
    prompt_template = """
You are a senior business analyst. Your task is to synthesize the initial company analysis and the new research findings into a single, comprehensive report. The report must be written in Korean.

**1. Initial Company Analysis:**
{initial_report}

**2. New Research Findings:**
{research_findings}

---
Based on ALL the information above, create a final report with the following structure. Be analytical and derive insights.

## 2. 경쟁 및 시장 분석 (Competitive & Market Landscape)

### 2.1. 경쟁사 분석 (Competitor Analysis)
(Create a markdown table comparing our company against 2-3 key competitors based on Business Model, Key Features, Target Customers, and Pricing.)

| 구분 | 자사 (Our Company) | [경쟁사 1 이름] | [경쟁사 2 이름] |
|---|---|---|---|
| **비즈니스 모델** | ... | ... | ... |
| **핵심 기능** | ... | ... | ... |
| **타겟 고객** | ... | ... | ... |
| **가격 정책** | ... | ... | ... |

### 2.2. 기회 요인 도출 (Opportunity Identification)
(Based on the comparison table, analyze our company's competitive advantages and identify specific opportunities.)
- **기회 1**: ...
- **기회 2**: ...

## 3. 린 캔버스 분석 (Lean Canvas Analysis)

(Fill out the 9 blocks of the Lean Canvas for our company based on all available information.)

- **1. Problem**: (고객 문제)
- **2. Customer Segments**: (고객군)
- **3. Unique Value Proposition**: (고유 가치 제안)
- **4. Solution**: (솔루션)
- **5. Channels**: (채널)
- **6. Revenue Streams**: (수익원)
- **7. Cost Structure**: (비용 구조)
- **8. Key Metrics**: (핵심 지표)
- **9. Unfair Advantage**: (경쟁 우위)

**Final Report:**
"""
    prompt = PromptTemplate.from_template(prompt_template)
    return prompt | llm | StrOutputParser()

def process_single_report(report_file):
    """단일 보고서 파일을 처리하는 메인 로직"""
    llm = ChatOllama(
        model="qwen3:32b",
        base_url="http://192.168.120.102:11434",
        temperature=0
    )
    search = DuckDuckGoSearchResults()

    def search_with_delay(query: str) -> str:
        print(f"\n> [Executor] 2초 대기 후 검색 실행: {query}")
        time.sleep(2)
        return search.run(query)

    search_tool = Tool(
        name="web_search",
        func=search_with_delay,
        description="A wrapper around DuckDuckGo Search. Useful for finding specific information about companies, markets, or technologies. Input should be a focused search query.",
    )

    planner_chain = create_planner_chain(llm)
    executor_agent = create_executor_agent(llm, [search_tool])
    synthesizer_chain = create_synthesizer_chain(llm)
    
    print(f"\n\n{'='*50}\nProcessing file: {report_file}\n{'='*50}")
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        initial_report_text = report_data.get("final_report_korean", "")
        if not initial_report_text:
            print(f"Skipping {report_file} due to missing 'final_report_korean'.")
            return
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading {report_file}: {e}")
        return

    # --- 단계 1: 계획 수립 ---
    print("\n🤖 [Phase 1/4] Starting Planner to create research plan...")
    task_list = planner_chain.invoke({"report_text": initial_report_text})
    print("✅ [Phase 1/4] Research plan created:")
    print(json.dumps(task_list, indent=2, ensure_ascii=False))

    # --- 단계 2: 계획 실행 ---
    print("\n🤖 [Phase 2/4] Starting Executor to gather information...")
    execution_results = []
    for task in task_list:
        print(f"\n> Executing Task {task['task_id']}: {task['query']}")
        try:
            result = executor_agent.invoke({"task_query": task['query']})
            execution_results.append({
                "task": task,
                "result": result.get('output', 'No output from agent.')
            })
        except Exception as e:
            print(f"🚨 Error executing task {task['task_id']}: {e}")
            execution_results.append({
                "task": task,
                "result": f"Execution failed: {e}"
            })
    print("\n✅ [Phase 2/4] All tasks executed.")
    
    # --- 단계 3: 보고서 종합 ---
    print("\n🤖 [Phase 3/4] Starting Synthesizer to create final report...")
    research_findings_str = ""
    for res in execution_results:
        research_findings_str += f"- Task: {res['task']['query']}\n"
        research_findings_str += f"  Finding: {res['result']}\n\n"
    
    final_report_raw = synthesizer_chain.invoke({
        "initial_report": initial_report_text,
        "research_findings": research_findings_str
    })
    
    think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
    final_report = think_pattern.sub("", final_report_raw).strip()

    print("\n" + "="*30)
    print("✅ 최종 경쟁 분석 보고서")
    print("="*30)
    print(final_report)

    # --- 단계 4: 결과 저장 ---
    print("\n🤖 [Phase 4/4] Saving the final report...")
    
    # bm_result 디렉토리 생성
    os.makedirs('bm_result', exist_ok=True)
    
    final_data = {
        "source_report_file": report_file,
        "research_plan": task_list,
        "execution_results": execution_results,
        "final_competitive_report": final_report
    }

    base_name = os.path.basename(report_file)
    identifier = base_name.replace('advanced_deep_research_report_', '').replace('.json', '')
    output_path = f'bm_result/competitive_analysis_report_{identifier}.json'

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 최종 보고서가 {output_path} 에 성공적으로 저장되었습니다.")
    except Exception as e:
        print(f"🚨 ERROR: Failed to save report to {output_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run competitive analysis on a single report file.")
    parser.add_argument("report_file", type=str, help="The path to the input advanced_deep_research_report JSON file.")
    args = parser.parse_args()
    
    if not os.path.exists(args.report_file):
        print(f"🚨 ERROR: Input file not found at '{args.report_file}'")
        sys.exit(1)
    else:
        try:
            process_single_report(args.report_file)
        except Exception as e:
            print(f"🚨 ERROR: An unexpected error occurred: {e}")
            sys.exit(1) 