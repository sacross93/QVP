from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict
from datetime import date
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import glob
import os
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor

class StartupInvestmentInfo(BaseModel):
    company_name: Optional[str] = Field(None, description="Official name of the startup")
    industry: Optional[str] = Field(None, description="Industry in which the startup operates (e.g., Fintech, BioTech)")
    funding_stage: Optional[str] = Field(None, description="Current funding stage (e.g., Seed, Series A, B, etc.)")
    last_funding_date: Optional[date] = Field(None, description="Date of the most recent funding round")
    funding_amount_billion: Optional[int] = Field(None, description="Total funding amount raised (in 100 million KRW units)")
    valuation_billion: Optional[int] = Field(None, description="Company valuation at the most recent round (in 100 million KRW)")

    contact_person: Optional[str] = Field(None, description="Name of the investment contact person")
    contact_phone: Optional[str] = Field(None, description="Phone number of the contact person")

    latest_revenue_million: Optional[int] = Field(None, description="Latest full-year revenue (in million KRW)")
    operating_profit_million: Optional[int] = Field(None, description="Latest operating profit (in million KRW)")
    annual_fixed_cost_million: Optional[int] = Field(None, description="Annual fixed operational cost (in million KRW)")
    cash_runway_months: Optional[int] = Field(None, description="Number of months the company can operate with current cash")
    breakeven_point: Optional[str] = Field(None, description="Estimated timeline to reach break-even point")

    debt_ratio_percent: Optional[int] = Field(None, description="Debt ratio of the company (%)")
    num_employees: Optional[int] = Field(None, description="Total number of employees")

    main_competitors: Optional[List[str]] = Field(None, description="List of primary competitors in the market")
    main_competitor_1: Optional[str] = Field(None, description="Key competitor 1 (mentioned by name)")
    main_competitor_2: Optional[str] = Field(None, description="Key competitor 2 or their market share")

    strengths: Optional[str] = Field(None, description="Main competitive strengths (e.g., technology, team, traction)")
    weaknesses: Optional[str] = Field(None, description="Identified internal or external weaknesses")
    opportunities: Optional[str] = Field(None, description="Market or product opportunities the company can leverage")
    threats: Optional[str] = Field(None, description="Risks or threats (legal, technical, or competitive)")

    num_patents: Optional[int] = Field(None, description="Number of registered patents")
    last_updated: Optional[date] = Field(None, description="Date this data was last updated")
    recent_quarter_revenue_million: Optional[int] = Field(None, description="Revenue in the most recent quarter (in million KRW)")
    annual_growth_percent: Optional[int] = Field(None, description="Year-over-year revenue growth (%)")

    main_operating_expenses: Optional[str] = Field(None, description="Breakdown of key operational expenses (e.g., HR 50%, Marketing 20%)")
    founder_background: Optional[str] = Field(None, description="Key professional experience of the founder(s)")
    key_personnel: Optional[str] = Field(None, description="Background or former employers of core personnel")
    board_members: Optional[List[str]] = Field(None, description="List of current board members")

    shareholding_structure: Optional[str] = Field(None, description="Current equity distribution among founders and investors")
    product_roadmap: Optional[str] = Field(None, description="Upcoming product or feature release plans")
    tech_stack: Optional[List[str]] = Field(None, description="Key technologies used in development (e.g., AWS, Python)")

    market_size_billion: Optional[int] = Field(None, description="Estimated size of the addressable market (in 100 million KRW)")
    market_growth_percent: Optional[int] = Field(None, description="Annual growth rate of the target market (%)")
    legal_issues: Optional[bool] = Field(None, description="Indicates whether there are any ongoing legal disputes")
    num_ip_rights: Optional[int] = Field(None, description="Number of registered intellectual property rights (e.g., trademarks, copyrights)")

    funding_round: Optional[str] = Field(None, description="Label for the specific funding round (e.g., Series A)")
    main_investors: Optional[List[str]] = Field(None, description="List of major investors (e.g., VC Alpha, VC Beta)")
    fund_usage_plan: Optional[str] = Field(None, description="Breakdown of how the funding will be allocated (e.g., R&D 40%, Marketing 30%)")

    exit_strategy: Optional[str] = Field(None, description="Exit strategy such as IPO, M&A, or acquisition")
    rnd_to_revenue_ratio: Optional[int] = Field(None, description="Ratio of R&D spending to revenue (%)")
    notes: Optional[str] = Field(None, description="Additional remarks or important notes to consider")

# 2. 두 개의 LLM 준비 (병렬 처리용)
llm1 = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.110.102:11434",
    temperature=0.1
)

llm2 = ChatOllama(
    model="qwen3:32b", 
    base_url="http://192.168.110.102:11434",
    temperature=0.1
)

def extract_with_llm(llm, md_content: str, fields: List[str], descriptions: List[str], analysis_feedback: str = "", llm_id: str = ""):
    """
    Extract fields using specific LLM instance
    """
    feedback_prompt = f"\nPrevious analysis feedback: {analysis_feedback}\n" if analysis_feedback else ""
    prompt = (
        "From the following md file, extract only the values for the given field names/descriptions as json. "
        "If not found, return null. Return only json, nothing else. Do not provide explanations.\n"
        f"Fields: {fields}\n"
        f"Descriptions: {descriptions}\n"
        f"{feedback_prompt}"
        f"md content:\n{md_content}\n"
        "IMPORTANT: Return ONLY a valid JSON object with the field names as keys. /no_think"
    )
    result = llm.invoke(prompt)
    result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
    print(f"  LLM{llm_id} processing {len(fields)} fields...")
    return result

# md에서 특정 필드만 추출하는 tool 정의 (단일 LLM용)
@tool
def extract_fields_from_md(md_content: str, fields: List[str], descriptions: List[str], analysis_feedback: str = "") -> dict:
    """
    Extract only the values corresponding to the given field names/descriptions from the md file as json. If not found, return null.
    """
    return extract_with_llm(llm1, md_content, fields, descriptions, analysis_feedback, "1")

@tool  
def analyze_extraction_failure(md_content: str, failed_fields: List[str], descriptions: List[str]) -> str:
    """
    Analyze why certain fields could not be extracted and provide suggestions for improvement.
    """
    prompt = (
        "Analyze the following MD file and explain why the specified fields could not be extracted. "
        "Provide specific suggestions on how to find or infer these values from the available content. "
        "Look for alternative terms, synonyms, or indirect references that might contain the information.\n"
        f"Failed fields: {failed_fields}\n"
        f"Field descriptions: {descriptions}\n"
        f"MD content:\n{md_content}\n"
        "Provide analysis and suggestions in plain text. /no_think"
    )
    result = llm1.invoke(prompt)
    result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
    return result

tools = [extract_fields_from_md, analyze_extraction_failure]

agent = create_react_agent(
    llm1,
    tools,
    prompt="You are an agent that extracts investment information from md files. Only use the tool to answer. /no_think"
)

# 3. md 파일 읽기 및 정보 추출
with open("./data/로보스.md", "r", encoding="utf-8") as f:
    content = f.read()

print("=== Starting extraction from 로보스.md ===")
print(f"MD file content length: {len(content)} characters")

info = StartupInvestmentInfo()
max_iter = 10
total_fields = len(StartupInvestmentInfo.model_fields)
previous_filled_count = 0
analysis_feedback = ""

for i in range(max_iter):
    fields_to_fill = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None]
    filled_fields = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is not None]
    num_filled = len(filled_fields)
    num_remaining = len(fields_to_fill)
    fill_ratio = num_filled / total_fields * 100
    
    print(f"\n[Iteration {i+1}] Filled: {num_filled}/{total_fields} ({fill_ratio:.1f}%) | Remaining: {num_remaining}")
    print(f"  Remaining fields: {fields_to_fill[:10]}{'...' if len(fields_to_fill) > 10 else ''}")
    
    if not fields_to_fill:
        print("All fields have been filled!")
        break
        
    # Check if no progress was made in the previous iteration
    if i > 0 and num_filled == previous_filled_count:
        print("No new fields were filled. Running analysis...")
        
        # Run analysis for failed fields
        analysis_response = agent.invoke({
            "messages": [{
                "role": "user", 
                "content": f"Analyze why these {len(fields_to_fill)} fields could not be extracted and provide suggestions"
            }],
            "analyze_extraction_failure": {
                "md_content": content,
                "failed_fields": fields_to_fill,
                "descriptions": [StartupInvestmentInfo.model_fields[k].description for k in fields_to_fill]
            }
        })
        
        analysis_feedback = analysis_response["messages"][-1].content
        print(f"  Analysis: {analysis_feedback[:200]}...")
        
    # 병렬 처리: 필드를 두 그룹으로 나누기
    if len(fields_to_fill) > 1:
        mid_point = len(fields_to_fill) // 2
        fields_group1 = fields_to_fill[:mid_point]
        fields_group2 = fields_to_fill[mid_point:]
        
        descriptions_group1 = [StartupInvestmentInfo.model_fields[k].description for k in fields_group1]
        descriptions_group2 = [StartupInvestmentInfo.model_fields[k].description for k in fields_group2]
        
        print(f"  Parallel processing: Group1({len(fields_group1)}) + Group2({len(fields_group2)}) fields...")
        
        # 병렬 실행
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(extract_with_llm, llm1, content, fields_group1, descriptions_group1, analysis_feedback, "1")
            future2 = executor.submit(extract_with_llm, llm2, content, fields_group2, descriptions_group2, analysis_feedback, "2")
            
            result1_raw = future1.result()
            result2_raw = future2.result()
            
        # 두 결과를 파싱하고 합치기
        combined_result = {}
        
        for raw_result, fields_group in [(result1_raw, fields_group1), (result2_raw, fields_group2)]:
            try:
                # JSON 부분만 추출
                json_match = re.search(r'\{.*\}', raw_result, flags=re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    parsed = json.loads(json_str)
                    combined_result.update(parsed)
                else:
                    print(f"Warning: No JSON found in parallel result: {raw_result[:100]}...")
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse parallel JSON: {raw_result[:100]}...")
                continue
                
        result = combined_result
        
    else:
        # 단일 필드인 경우 기존 방식 사용
        descriptions = [StartupInvestmentInfo.model_fields[k].description for k in fields_to_fill]
        
        # agent에게 tool 사용 요청
        user_msg = {
            "role": "user", 
            "content": f"Extract ONLY the following {len(fields_to_fill)} fields as JSON from the MD file: {', '.join(fields_to_fill[:5])}{'...' if len(fields_to_fill) > 5 else ''}"
        }
        tool_input = {
            "md_content": content,
            "fields": fields_to_fill,
            "descriptions": descriptions,
            "analysis_feedback": analysis_feedback
        }
        
        print(f"  Requesting extraction of {len(fields_to_fill)} fields...")
        
        # agent가 tool을 사용하도록 메시지 전달
        response = agent.invoke({
            "messages": [user_msg],
            "extract_fields_from_md": tool_input
        })
        
        # 결과 반영
        result_content = response["messages"][-1].content
        try:
            # qwen3 모델의 <think></think> 태그 제거
            if isinstance(result_content, str):
                # <think>...</think> 태그와 그 내용을 제거
                cleaned_content = re.sub(r'<think>.*?</think>', '', result_content, flags=re.DOTALL).strip()
                
                # JSON 부분만 추출 (중괄호로 시작하는 부분)
                json_match = re.search(r'\{.*\}', cleaned_content, flags=re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    result = json.loads(json_str)
                else:
                    print(f"Warning: No JSON found in response: {cleaned_content[:100]}...")
                    continue
            else:
                result = result_content
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response: {result_content[:100]}...")
            print(f"JSON Error: {e}")
            continue
        
    # Count newly filled fields
    newly_filled = 0
    for k, v in result.items():
        if v is not None and k in StartupInvestmentInfo.model_fields and getattr(info, k) is None:
            setattr(info, k, v)
            newly_filled += 1
            
    print(f"  Successfully filled {newly_filled} new fields")
    previous_filled_count = num_filled

print(f"\n=== Final Results ===")
final_filled = len([field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is not None])
final_ratio = final_filled / total_fields * 100
print(f"Total filled: {final_filled}/{total_fields} ({final_ratio:.1f}%)")
print(f"Final result:")
print(info.model_dump_json(ensure_ascii=False, indent=2))