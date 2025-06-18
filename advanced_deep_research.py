import json
import re
import os
import time # 시간 지연을 위해 time 모듈 추가
import argparse # 인자 처리를 위해 추가
from glob import glob

def remove_think_tags(text: str) -> str:
    """<think> 태그를 제거합니다."""
    think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
    return think_pattern.sub("", text).strip()
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import Tool, create_react_agent, AgentExecutor
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
import sys

# --- 1. LLM 및 도구 설정 ---
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

search = DuckDuckGoSearchResults()

def search_with_delay(query: str) -> str:
    """사용량 제한을 피하기 위해 검색 전에 지연 시간을 추가하는 래퍼 함수입니다."""
    print(f"\n> [Rate Limit] 2초 대기 후 검색 실행: {query}")
    time.sleep(2)
    return search.run(query)

# 리서처 에이전트가 사용할 도구
research_tools = [
    Tool(
        name="web_search",
        func=search_with_delay,
        description="A wrapper around DuckDuckGo Search. Useful for finding information about companies, products, and markets. Input should be a search query.",
    )
]

# --- 2. 핵심 모듈 (체인 및 에이전트) 생성 ---

def create_researcher_agent(llm, tools):
    """SWOT 분석을 기반으로 자사, 경쟁사, 시장에 대한 심층 정보를 수집하는 ReAct 에이전트를 생성합니다."""
    prompt_template = """
You are a top-tier market research analyst agent. Your goal is to gather comprehensive data for a deep market analysis, focusing on a **startup** company identified from the SWOT analysis. You must follow the instructions PERFECTLY.

**Analysis Context:** The company being analyzed is a startup. Frame all your research from this perspective. Avoid focusing on large, incumbent corporations.

**Your Task & Thought Process:**

1.  **Identify the Company:** First, carefully read the provided SWOT analysis (`{input}`) to identify the name of "Our Company".
2.  **Initial Company Research:** Your **first action MUST** be to perform a web search to understand what this company does. Use a query like "What is [Company Name]?", "[Company Name] business overview", or "[Company Name] products and services". This step is critical for establishing context.
3.  **Deep Dive Research:** With the context from your initial research and the SWOT analysis, execute search queries using the `web_search` tool to gather information for ALL the categories below:
    - **Our Company (Lean Canvas Focus):**
        - **Company Overview:** What is this company? What are its main products, services, and mission? Use the findings from your initial company research for this.
        - **Problem:** What specific customer problems does the company's product/service solve?
        - **Solution:** What are the key features of the solution?
        - **Key Metrics:** What metrics measure success (e.g., user growth, revenue goals)?
        - **Cost Structure:** What are the major business costs (e.g., R&D, marketing)?
    - **Competitors:**
        - Identify Competitors: Identify 2-3 key **startup** competitors. Use specific queries like "[Our Company's product/technology] startups" or "venture funded [market segment] companies".
        - Competitor Analysis: For each competitor, find their Business Model, Key Features, and Target Customers.
    - **Market:**
        - Market Size & Growth: What is the current size and projected growth rate of the target market?
        - Market Trends: What are the key trends shaping this market?
4.  **Aggregate & Finalize:** After completing all searches, aggregate the collected data. Format the aggregated data into a single JSON array string as the `Final Answer`.


**Available Tools:**
{tools}

**Initial SWOT Analysis:**
{input}

{agent_scratchpad}

---
**CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:**

1.  You MUST use the format: `Thought:`, `Action:`, `Action Input:`, `Observation:`.
2.  `Action` must be one of [{tool_names}].
3.  `Action Input` MUST be ONLY the search query string.
4.  The `Observation` is the result from the tool. You do not write it. The system provides it.
5.  When you have enough information for ALL categories, you MUST output the final answer using the `Final Answer:` keyword.
6.  The `Final Answer` MUST be a single, valid JSON array of objects. Each object must have "category", "snippet", and "source" keys.
    - The `source` value MUST be a valid URL starting with `http://` or `https://` from the `Observation`.
    - DO NOT use your own search query as the `source` value. It MUST be a URL from a search result.
7.  Start the JSON with `[` and end with `]`.

**Example of a correct final step:**
Thought: I have now gathered enough information from my searches and can compile the final report.
Final Answer: [{{ "category": "Company Overview", "snippet": "A brief, factual summary of what the company does, its main products, and its mission.", "source": "https://www.company-website.com/about" }}, {{ "category": "Problem", "snippet": "A specific problem that the company's customers face, supported by evidence from a reliable source.", "source": "https://www.industry-report.com/problem-analysis" }}, {{ "category": "Competitor: StartupName", "snippet": "A brief overview of a direct startup competitor, including their business focus or funding status.", "source": "https://www.competitor-startup.com/" }}, {{ "category": "Market Size & Growth", "snippet": "Specific data on the market size, such as 'The market was valued at $X billion in YYYY and is expected to grow at a Z% CAGR.'", "source": "https://www.marketresearchfirm.com/report-link" }}]
"""
    prompt = PromptTemplate.from_template(prompt_template)
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=25 # 더 많은 정보 수집을 위해 반복 횟수 증가
    )

def create_summarizer_chain(llm):
    """제공된 프롬프트를 사용하여 텍스트를 밀도 높게 요약하는 체인을 생성합니다."""
    prompt_template = """
Article:
{article_text}

---
You will generate increasingly concise, entity-dense summaries of the above Article.
Repeat the following 2 steps 5 times.

Step 1. Identify 1-3 informative Entities (";" delimited) from the Article which are missing from the previously generated summary.
Step 2. Write a new, denser summary of identical length which covers every entity and detail from the previous summary plus the Missing Entities.

A Missing Entity is:
- Relevant: to the main story.
- Specific: descriptive yet concise (5 words or fewer).
- Novel: not in the previous summary.
- Faithful: present in the Article.
- Anywhere: located anywhere in the Article.

Guidelines:
- The first summary should be long (4-5 sentences, ~80 words) yet highly non-specific, containing little information beyond the entities marked as missing. Use overly verbose language and fillers (e.g., "this article discusses") to reach ~80 words.
- Make every word count: re-write the previous summary to improve flow and make space for additional entities.
- Make space with fusion, compression, and removal of uninformative phrases like "the article discusses".
- The summaries should become highly dense and concise yet self-contained, e.g., easily understood without the Article.
- Missing entities can appear anywhere in the new summary.
- Never drop entities from the previous summary. If space cannot be made, add fewer new entities.
- Remember, use the exact same number of words for each summary.

Answer in JSON. The JSON should be a list (length 5) of dictionaries whose keys are "Missing_Entities" and "Denser_Summary"/no_think.
"""
    prompt = PromptTemplate.from_template(prompt_template)
    return prompt | llm | JsonOutputParser()

def create_validator_chain(llm):
    """주어진 리서치 결과물의 품질을 검증하고 유효한 항목만 필터링하는 체인을 생성합니다."""
    prompt_template = """
You are a meticulous data validation AI. Your task is to review a list of research findings and filter out any low-quality or invalid entries. A high-quality entry must have a real, specific snippet and a valid, non-placeholder source URL.

**Input Data (JSON list of research findings):**
{research_findings}

---
**Validation Criteria:**

1.  **Snippet Quality:**
    - The 'snippet' must be specific and contain concrete information (e.g., names, numbers, facts, statistics).
    - It must NOT be generic placeholder text like "A snippet about..." or overly vague descriptions.
    - For categories like 'Market Size & Growth' or 'Key Metrics', the snippet MUST contain quantitative data (e.g., "$10 billion", "CAGR of 15%", "50,000 users").

2.  **Source URL Validity:**
    - The 'source' URL must be a real, complete, and public URL starting with `http://` or `https://`.
    - It must NOT be a placeholder domain like "example.com", "your-source.com", "competitor.com", etc.

**Your Task:**
Review each JSON object in the input list. Only keep the objects that meet BOTH validation criteria. Return a new, filtered JSON list containing only the valid findings. If an entry is invalid, discard it. Your output must be a valid JSON list. If no findings are valid, return an empty list `[]`.

**CRITICAL: Your output MUST be ONLY the filtered, valid JSON list. Do not add any other text or explanation.**

**Filtered JSON Output:**
"""
    prompt = PromptTemplate.from_template(prompt_template)
    return prompt | llm | JsonOutputParser()

def create_synthesis_chain(llm):
    """수집 및 요약된 정보를 바탕으로 확장된 최종 보고서를 작성하는 체인을 생성합니다."""
    prompt_template = """
You are a senior business analyst. Your task is to synthesize the provided research into a final, structured report.
The report should be written in Korean and follow the specified format, providing a foundation for a later competitive analysis.

**Initial SWOT Analysis:**
{swot_analysis}

**Summarized Research Findings (Our Company, Competitors, Market):**
{research_data}

---
Based on all the information above, create a comprehensive report that addresses the following key areas.
Structure your answer clearly with markdown headings.

## 1. 자사 분석 (Our Company Analysis)

### 1.1. 기업 개요 (Company Overview)
- (Summarize the company's identity, main products/services, and mission based on the 'Company Overview' research finding.)

### 1.2. 해결하려는 문제 (Problem)
- (Summarize findings about the core customer problems the company aims to solve.)

### 1.3. 솔루션 및 핵심 기술 (Solution & Core Technology)
- (Summarize findings about the company's products, services, and technology as a solution.)

### 1.4. 핵심 지표 (Key Metrics)
- (Summarize findings about the key metrics for success, like growth targets or user engagement goals.)

### 1.5. 비용 구조 (Cost Structure)
- (Summarize findings about the company's main cost drivers.)


## 2. 초기 시장 및 경쟁 환경 분석 (Initial Market & Competitive Landscape)

### 2.1. 시장 현황 및 트렌드 (Market Status & Trends)
- **시장 규모 및 성장률**: (Summarize findings on market size and growth.)
- **주요 트렌드**: (Summarize key market trends.)

### 2.2. 주요 경쟁사 기초 분석 (Initial Competitor Analysis)
- (For each identified competitor, briefly summarize their business model, key features, and target customers based on the gathered info.)
- **경쟁사 1: [경쟁사 이름]**
  - BM: ...
  - 핵심 기능: ...
  - 타겟 고객: ...
- **경쟁사 2: [경쟁사 이름]**
  - BM: ...
  - 핵심 기능: ...
  - 타겟 고객: ...

**Final Report:**
"""
    prompt = PromptTemplate.from_template(prompt_template)
    return prompt | llm | StrOutputParser()


# --- 3. 메인 실행 로직 ---
def process_single_file(swot_file):
    """단일 SWOT 파일을 처리하는 메인 로직"""
    llm = ChatOllama(
        model="qwen3:32b",
        base_url="http://192.168.120.102:11434",
        temperature=0
    )
    search = DuckDuckGoSearchResults()

    def search_with_delay(query: str) -> str:
        print(f"\n> [Rate Limit] 2초 대기 후 검색 실행: {query}")
        time.sleep(2)
        return search.run(query)

    research_tools = [
        Tool(
            name="web_search",
            func=search_with_delay,
            description="A wrapper around DuckDuckGo Search. Useful for finding information about companies, products, and markets. Input should be a search query.",
        )
    ]

    researcher_agent = create_researcher_agent(llm, research_tools)
    validator_chain = create_validator_chain(llm)
    summarizer_chain = create_summarizer_chain(llm)
    synthesis_chain = create_synthesis_chain(llm)

    print(f"\n{'='*30}\nProcessing file: {swot_file}\n{'='*30}")
    try:
        with open(swot_file, 'r', encoding='utf-8') as f:
            swot_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading {swot_file}: {e}")
        return

    swot_input_string = json.dumps(swot_data, ensure_ascii=False, indent=2)

    # --- 단계 1: 정보 수집 (검증 및 재시도 로직 추가) ---
    print("\n🤖 [Phase 1/4] Starting Researcher Agent to gather information...")
    
    max_retries = 3
    gathered_info = None

    for i in range(max_retries):
        try:
            research_result = researcher_agent.invoke({"input": swot_input_string})
            output_text = research_result.get('output', '')

            cleaned_output = remove_think_tags(output_text)

            json_match = re.search(r'\[.*\]', cleaned_output, re.DOTALL)
            if not json_match:
                raise ValueError(f"No JSON array found in the cleaned output: {cleaned_output}")
            
            potential_gathered_info = json.loads(json_match.group(0))

            # The simple check below is kept as a first-pass filter
            if not potential_gathered_info:
                print(f"🚨 Agent returned an empty list. Retrying... ({i + 1}/{max_retries})")
                continue # Retry if the list is empty

            gathered_info = potential_gathered_info
            break

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"🚨 Error during research phase: {e}. Retrying... ({i + 1}/{max_retries})")
            if 'research_result' in locals():
                print("Raw output:", research_result.get('output'))
    
    if gathered_info is None:
        print(f"🚨 Researcher agent failed to provide valid data for {swot_file} after {max_retries} retries. Skipping this file.")
        return
    
    print(f"✅ [Phase 1/4] Researcher Agent found {len(gathered_info)} pieces of information.")

    # --- 단계 2: 정보 검증 ---
    print("\n🤖 [Phase 2/4] Starting Validator to check data quality...")
    validated_info = []
    try:
        validator_result = validator_chain.invoke({"research_findings": json.dumps(gathered_info, ensure_ascii=False)})
        if isinstance(validator_result, str):
            # JSON 문자열인 경우 think 태그 제거 후 파싱
            cleaned_result = remove_think_tags(validator_result)
            validated_info = json.loads(cleaned_result)
        else:
            validated_info = validator_result
            
        if not isinstance(validated_info, list):
             print(f"⚠️ Validator did not return a list, using original data. Output: {validated_info}")
             validated_info = gathered_info

    except Exception as e:
        print(f"🚨 Error during validation phase: {e}. Skipping validation and using original data.")
        validated_info = gathered_info

    if len(validated_info) < len(gathered_info):
        print(f"⚠️  Validator filtered out {len(gathered_info) - len(validated_info)} low-quality items.")
    
    if not validated_info:
        print(f"🚨 Validator filtered out all items. Cannot proceed for {swot_file}.")
        return

    print(f"✅ [Phase 2/4] Validator approved {len(validated_info)} items.")

    # --- 단계 3: 정보 요약 ---
    print("\n🤖 [Phase 3/4] Starting Summarizer Chain to condense information...")
    summarized_findings = []
    for info in validated_info:
        if not info.get('snippet'):
            continue
        
        try:
            print(f"  - Summarizing snippet for category '{info.get('category')}'...")
            summary_result = summarizer_chain.invoke({"article_text": info['snippet']})
            
            # JSON 문자열인 경우 think 태그 제거 후 파싱
            if isinstance(summary_result, str):
                cleaned_summary = remove_think_tags(summary_result)
                summary_json = json.loads(cleaned_summary)
            else:
                summary_json = summary_result
            
            densest_summary = summary_json[-1]['Denser_Summary']
            
            summarized_findings.append({
                "category": info.get('category', 'General'),
                "summary": densest_summary,
                "source": info.get('source', 'N/A')
            })
        except Exception as e:
            print(f"🚨 Error during summarization: {e}")
            summarized_findings.append({
                "category": info.get('category', 'General'),
                "summary": info['snippet'],
                "source": info.get('source', 'N/A')
            })
    
    print(f"✅ [Phase 3/4] Summarizer Chain processed {len(summarized_findings)} items.")
    
    # --- 단계 4: 최종 보고서 종합 ---
    print("\n🤖 [Phase 4/4] Starting Synthesizer Chain to create final report...")
    
    research_data_str = ""
    for finding in summarized_findings:
        research_data_str += f"- Category: {finding['category']}\n"
        research_data_str += f"  Summary: {finding['summary']}\n"
        research_data_str += f"  Source: {finding['source']}\n\n"

    final_report_raw = synthesis_chain.invoke({
        "swot_analysis": swot_input_string,
        "research_data": research_data_str
    })
    
    final_report = remove_think_tags(final_report_raw)

    print("\n" + "="*30)
    print("✅ 최종 분석 보고서 (Advanced Deep Research)")
    print("="*30)
    print(final_report)

    # --- 4. 결과 저장 ---
    # bm_result 디렉토리 생성
    os.makedirs('bm_result', exist_ok=True)
    
    report_data = {
        "source_swot_file": swot_file,
        "gathered_information": gathered_info,
        "summarized_findings": summarized_findings,
        "final_report_korean": final_report
    }
    
    base_name = os.path.basename(swot_file)
    identifier = base_name.replace('_swot_analysis', '').replace('.json', '')
    output_path = f'bm_result/advanced_deep_research_report_{identifier}.json'

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 최종 보고서가 {output_path} 에 성공적으로 저장되었습니다.")
    except Exception as e:
        print(f"🚨 ERROR: Failed to save report to {output_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run advanced deep research on a single SWOT analysis file.")
    parser.add_argument("swot_file", type=str, help="The path to the input SWOT analysis JSON file.")
    args = parser.parse_args()
    
    if not os.path.exists(args.swot_file):
        print(f"🚨 ERROR: Input file not found at '{args.swot_file}'")
        sys.exit(1)
    else:
        try:
            process_single_file(args.swot_file)
        except Exception as e:
            print(f"🚨 ERROR: An unexpected error occurred: {e}")
            sys.exit(1) 