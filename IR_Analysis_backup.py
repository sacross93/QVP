from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict
from datetime import date
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
import glob
import os
import json
import re

class StartupInvestmentInfo(BaseModel):
    company_name: Optional[str] = Field(None, description="Official company name or corporate name(회사명)")
    industry: Optional[str] = Field(None, description="Primary business sector or industry vertical (e.g., Manufacturing, IT Services, Biotech, Fintech, Robotics, SaaS)(업종)")
    funding_stage: Optional[str] = Field(None, description="Current investment stage (e.g., Seed, Series A, Series B, Bridge, Pre-IPO)(투자단계)")
    last_funding_date: Optional[date] = Field(None, description="Date of the most recent funding round or capital raising(최근 투자일)")
    funding_amount_billion: Optional[int] = Field(None, description="Total cumulative funding raised (in 100 million KRW units)(총 투자금액)")
    valuation_billion: Optional[int] = Field(None, description="Company valuation at the most recent funding round (in 100 million KRW units)(최근 투자 평가액)")

    contact_person: Optional[str] = Field(None, description="IR contact person, CEO, or primary point of contact name(연락담당자)")
    contact_phone: Optional[str] = Field(None, description="Company main phone number or contact person's phone(연락처)")

    latest_revenue_million: Optional[int] = Field(None, description="Most recent annual revenue (in million KRW)(최근 연간 매출액)")
    operating_profit_million: Optional[int] = Field(None, description="Most recent annual operating profit or EBITDA (in million KRW)(최근 연간 영업이익 또는 EBITDA)")
    annual_fixed_cost_million: Optional[int] = Field(None, description="Annual fixed costs or total operating expenses (in million KRW)(연간 고정비용 또는 총 운영비용)")
    cash_runway_months: Optional[int] = Field(None, description="Number of months the company can operate with current cash reserves(현재 현금 잔액으로 운영할 수 있는 개월 수)")
    breakeven_point: Optional[str] = Field(None, description="Expected timeline or plan to reach break-even point(손익분기점 도달 예상 시간)")

    debt_ratio_percent: Optional[int] = Field(None, description="Debt-to-asset ratio (total debt/total assets × 100)(부채비율)")
    num_employees: Optional[int] = Field(None, description="Total number of employees or team members(전체 직원 수)")

    main_competitors: Optional[List[str]] = Field(None, description="List of primary competitors in the market(주요 경쟁사)")
    main_competitor_1: Optional[str] = Field(None, description="Top competitor name or competing product/service(주요 경쟁사 1)")
    main_competitor_2: Optional[str] = Field(None, description="Second major competitor or market share information(주요 경쟁사 2)")

    strengths: Optional[str] = Field(None, description="Core competitive advantages, differentiators, or key strengths (technology, team, patents, customer base)(주요 경쟁력)")
    weaknesses: Optional[str] = Field(None, description="Internal weaknesses, limitations, or areas needing improvement(내부 약점)")
    opportunities: Optional[str] = Field(None, description="Market opportunities, growth drivers, or external favorable conditions(시장 기회)")
    threats: Optional[str] = Field(None, description="Risk factors or threat elements (legal, technical, competitive, market risks)(위험요소)")

    num_patents: Optional[int] = Field(None, description="Number of registered patents owned(등록된 특허 수)")
    last_updated: Optional[date] = Field(None, description="Date when this information was last updated or reference date(최종 업데이트 일자)")
    recent_quarter_revenue_million: Optional[int] = Field(None, description="Most recent quarterly revenue (in million KRW)(최근 분기 매출액)")
    annual_growth_percent: Optional[int] = Field(None, description="Year-over-year revenue growth rate (%)")

    main_operating_expenses: Optional[str] = Field(None, description="Breakdown of major operating expense categories (e.g., Personnel 50%, Marketing 20%, R&D 15%)(주요 운영비용 분할)")
    founder_background: Optional[str] = Field(None, description="Founder's or CEO's key experience, expertise, or professional background(설립자 또는 CEO의 주요 경험, 전문성 또는 전문 배경)")
    key_personnel: Optional[str] = Field(None, description="Core executives' backgrounds, previous employers, or areas of expertise(주요 임원의 배경, 이전 소속 기관 또는 전문 분야)")
    board_members: Optional[List[str]] = Field(None, description="Board members, advisors, or mentors list(이사회 멤버, 조언자 또는 멘토 목록)")

    shareholding_structure: Optional[str] = Field(None, description="Ownership structure and equity distribution (founders, investors, employees)(주주 구조 및 지분 분배)")
    product_roadmap: Optional[str] = Field(None, description="Product/service development roadmap, launch plans, or feature expansion timeline(제품/서비스 개발 로드맵, 출시 계획 또는 기능 확장 시간표)")
    tech_stack: Optional[List[str]] = Field(None, description="Core technology stack, development tools, infrastructure (e.g., Python, AWS, React)(핵심 기술 스택, 개발 도구, 인프라)")

    market_size_billion: Optional[int] = Field(None, description="Target market size or Total Addressable Market (TAM) in 100 million KRW(대상 시장 규모 또는 총 주주 가능 시장(TAM) 100만 원 단위)")
    market_growth_percent: Optional[int] = Field(None, description="Target market's compound annual growth rate (CAGR %)(대상 시장의 복합 연간 성장률(CAGR %))")
    legal_issues: Optional[bool] = Field(None, description="Whether there are ongoing legal disputes, litigation, or regulatory issues(법적 분쟁, 소송, 규제 문제 여부)")
    num_ip_rights: Optional[int] = Field(None, description="Total intellectual property rights owned (patents, trademarks, copyrights, designs)(총 지적 재산권 보유 수(특허, 상표, 저작권, 디자인))")

    funding_round: Optional[str] = Field(None, description="Current or recent funding round name (e.g., Series A, Seed Investment)(현재 또는 최근 투자 단계 이름(예: 시리즈 A, 시드 투자))")
    main_investors: Optional[List[str]] = Field(None, description="List of major investors (VCs, strategic investors, angel investors)(주요 투자자(VC, 전략 투자자, 앙그레이 투자자))")
    fund_usage_plan: Optional[str] = Field(None, description="Investment fund allocation plan (e.g., R&D 40%, Marketing 30%, Hiring 20%)(투자 자금 배분 계획(예: R&D 40%, 마케팅 30%, 채용 20%))")

    exit_strategy: Optional[str] = Field(None, description="Exit strategy plan (IPO, M&A, acquisition, etc.)(출구 전략 계획(IPO, M&A, 인수 등))")
    rnd_to_revenue_ratio: Optional[int] = Field(None, description="R&D spending as percentage of revenue (%)")
    notes: Optional[str] = Field(None, description="Additional important notes, special circumstances, or other considerations(추가 중요 메모, 특별 상황, 기타 고려사항)")

# State 정의
class ExtractionState(TypedDict):
    info: StartupInvestmentInfo
    md_content: str
    iteration: int
    no_progress_count: int
    analysis_feedback: str
    total_fields: int
    last_action: str  # "extract", "analyze", "verify"
    verification_index: int  # 현재 검증 중인 필드 인덱스
    verified_fields: List[str]  # 검증 완료된 필드 목록

# 2. LLM 준비
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

parser = JsonOutputParser(pydantic_object=StartupInvestmentInfo)

# 필드 추출 함수 (원래 방식으로 복원)
def extract_fields(state: ExtractionState) -> ExtractionState:
    """MD 파일에서 빈 필드들을 추출합니다."""
    info = state["info"]
    md_content = state["md_content"]
    analysis_feedback = state["analysis_feedback"]
    iteration = state["iteration"] + 1
    
    # 빈 필드들 찾기
    fields_to_fill = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None]
    field_descriptions = [StartupInvestmentInfo.model_fields[field].description for field in fields_to_fill]
    
    # 진행 상황 출력
    filled_count = state["total_fields"] - len(fields_to_fill)
    fill_ratio = filled_count / state["total_fields"] * 100
    print(f"\n[Iteration {iteration}] Filled: {filled_count}/{state['total_fields']} ({fill_ratio:.1f}%) | Remaining: {len(fields_to_fill)}")
    print(f"  Remaining fields: {fields_to_fill[:10]}{'...' if len(fields_to_fill) > 10 else ''}")
    
    if not fields_to_fill:
        return state
    
    # 추출 프롬프트 (실제 LLM 호출용)
    feedback_prompt = f"\nPrevious analysis feedback: {analysis_feedback}\n" if analysis_feedback else ""
    prompt = f"""
You are an expert data extractor for Korean startup IR documents. Extract specific values from the MD file for the given fields.

CRITICAL RULES:
1. ONLY extract information that is explicitly stated in the document
2. DO NOT generate, guess, or hallucinate any information
3. If information is not clearly present, return null
4. Return ONLY the specified field names as JSON keys
5. Use exact Korean text as found in the document
6. Be sure to write only what is in the MD document content. If you don't know, write None.

DOCUMENT STRUCTURE PATTERNS TO LOOK FOR:

For company_name:
- Look in document titles, headers, or company info sections
- Common Korean labels: "회사명", "상호", "기업명", "회사개요", "Company Info"
- Often appears in tables with company details

For contact_person:
- Look in "Investor Relations" sections, team descriptions, or contact info
- Common patterns: "대표", "CEO", "연락담당자", "Contact"
- Usually appears with names and titles

For contact_phone:
- Look for Korean phone number patterns: +82-xx-xxxx-xxxx or similar
- Common labels: "전화", "연락처", "Company", "Personal"
- Often in contact or company info sections

For industry:
- Look in business descriptions, company overview sections
- Common labels: "업종", "사업분야", "업종", "주요사업"
- May appear in tables or descriptive text

For funding info (funding_stage, funding_amount_billion, valuation_billion):
- Look for "투자", "자금조달", "시리즈A/B", "밸류에이션", "Post Value"
- Convert Korean numbers: 억=100million, 천만=10million, 만=10thousand

For financial data (revenue, profit, costs):
- Look for "매출", "영업이익", "자본금", "운영비"
- Convert Korean numbers accordingly

For personnel info (num_employees, team info):
- Look for "임직원수", "직원수", "구성원", team member lists

For competitors:
- Look for "경쟁사", "경쟁업체", competitor analysis sections

For last_updated:
- Look for document dates, publication dates, or "최종수정일"
- Date formats may vary (YYYY-MM-DD, YYYY년 MM월 등)

MD document content:
```
{md_content}
{feedback_prompt}
```

Fields to extract: ```{dict(zip(fields_to_fill, field_descriptions))}```

Be sure to write only what is in the MD document content. If you don't know, write None.
Return ONLY a valid JSON object with the specified field names. Extract real values from the document, not placeholder data.
/no_think
"""
    
    # 프롬프트 저장용 (MD 내용 생략)
    os.makedirs("prompt", exist_ok=True)
    prompt_for_save = (
        f"You are an expert data extractor for Korean startup IR documents.\n\n"
        f"CRITICAL RULES:\n"
        f"1. ONLY extract information that is explicitly stated in the document\n"
        f"2. DO NOT generate, guess, or hallucinate any information\n"
        f"3. If information is not clearly present, return null\n"
        f"4. Return ONLY the specified field names as JSON keys\n"
        f"5. Use exact Korean text as found in the document\n\n"
        f"DOCUMENT STRUCTURE PATTERNS TO LOOK FOR:\n\n"
        f"For company_name: Look in document titles, headers, company info sections\n"
        f"For contact_person: Look in IR sections, team descriptions, contact info\n"
        f"For contact_phone: Look for Korean phone patterns (+82-xx-xxxx-xxxx)\n"
        f"For industry: Look in business descriptions, company overview sections\n"
        f"For funding info: Look for investment, funding rounds, valuations\n"
        f"For financial data: Look for revenue, profits, costs\n"
        f"For personnel info: Look for employee counts, team info\n"
        f"For competitors: Look for competitive analysis sections\n"
        f"For last_updated: Look for document dates, publication dates\n\n"
        f"NUMBER CONVERSION: 억=100million, 천만=10million, 만=10thousand\n\n"
        f"MD content: [MD_CONTENT_OMITTED - {len(md_content)} characters]\n\n"
        f"{feedback_prompt}"
        f"Fields to extract: {dict(zip(fields_to_fill, field_descriptions))}\n\n"
        f"Return ONLY a valid JSON object with the specified field names."
    )
    
    with open(f"prompt/iteration_{iteration:02d}_extract_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_for_save)
    print(f"  Prompt saved to: prompt/iteration_{iteration:02d}_extract_prompt.txt")
    
    print(f"  Requesting extraction of {len(fields_to_fill)} fields...")
    result = llm.invoke(prompt)
    
    # LLM 응답 저장
    with open(f"prompt/iteration_{iteration:02d}_extract_response.txt", "w", encoding="utf-8") as f:
        f.write(str(result.content))
    print(f"  Response saved to: prompt/iteration_{iteration:02d}_extract_response.txt")
    
    # 결과 처리
    try:
        if isinstance(result.content, str):
            cleaned_content = re.sub(r'<think>.*?</think>', '', result.content, flags=re.DOTALL).strip()
            json_match = re.search(r'\{.*\}', cleaned_content, flags=re.DOTALL)
            if json_match:
                json_str = json_match.group()
                extracted_data = json.loads(json_str)
            else:
                print(f"Warning: No JSON found in response: {cleaned_content[:100]}...")
                extracted_data = {}
        else:
            extracted_data = result.content
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON response: {result.content[:100]}...")
        print(f"JSON Error: {e}")
        extracted_data = {}
    
    # 무효한 값들 필터링 (Not specified, 데이터 없음 등은 null로 처리)
    invalid_values = {
        "Not specified", "not specified", "NOT SPECIFIED",
        "데이터 없음", "정보 없음", "해당 없음", "명시되지 않음",
        "N/A", "n/a", "NA", "na", "null", "NULL", "None", "NONE",
        "정보 부족", "확인 불가", "불명", "미확인", "미명시",
        "-", "—", "–", "", "정보가 없음", "자료 없음"
    }
    
    # 추출된 데이터 검증 및 필터링
    newly_filled = 0
    for k, v in extracted_data.items():
        if k in StartupInvestmentInfo.model_fields and getattr(info, k) is None:
            # 무효한 값인지 확인
            is_invalid = False
            if isinstance(v, str):
                is_invalid = v.strip() in invalid_values or len(v.strip()) == 0
                # 환각 데이터 패턴 검사
                if not is_invalid and v.strip():
                    # 일반적인 환각 패턴들
                    hallucination_patterns = [
                        "blue bottle", "john doe", "jane doe", "café 24", "starbucks",
                        "sample", "example", "test", "demo", "placeholder"
                    ]
                    v_lower = v.lower()
                    if any(pattern in v_lower for pattern in hallucination_patterns):
                        is_invalid = True
                        print(f"    ⚠ {k}: '{v}' (환각 패턴 감지됨)")
            elif v is None:
                is_invalid = True
            
            if not is_invalid:
                setattr(info, k, v)
                newly_filled += 1
                print(f"    ✓ {k}: {v}")
            else:
                print(f"    ✗ {k}: '{v}' (무효한 값으로 필터링됨)")
    
    print(f"  Successfully filled {newly_filled} new fields")
    
    # 진전 여부 확인
    new_remaining_count = len([field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None])
    previous_remaining_count = len(fields_to_fill)
    
    if new_remaining_count == previous_remaining_count:
        no_progress_count = state["no_progress_count"] + 1
    else:
        no_progress_count = 0
    
    return {
        **state,
        "info": info,
        "iteration": iteration,
        "no_progress_count": no_progress_count,
        "last_action": "extract"
    }

# 분석 함수
def analyze_failure(state: ExtractionState) -> ExtractionState:
    """추출 실패 이유를 분석합니다."""
    info = state["info"]
    md_content = state["md_content"]
    iteration = state["iteration"]
    
    # 빈 필드들 찾기 (처음 10개만)
    failed_fields = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None]
    failed_fields_sample = failed_fields[:10]  # 32B 모델을 위해 처음 10개만
    
    print("No progress detected. Running failure analysis...")
    
    # 간결한 분석 프롬프트
    prompt = (
"""IR Document:```{{md_content}}```

Target Fields for Summarization: ```{{target_fields_list}}```
(예: "연간 매출", "유저 수", "투자 유치 금액", "경쟁사", "고객 확보 전략")

Instructions:
Based on the IR Document provided, you will generate a summary focused on the 'Target Fields for Summarization'. This summary will be created in a "Chain of Density" manner, progressively becoming more detailed and entity-rich across 3 stages, while trying to maintain a reasonable overall length.

For each stage, focus on incorporating information related to the 'Target Fields for Summarization'.

---

**Stage 1: Sparse Summary (Key Facts Extraction)**
*   **Objective:** Identify and extract the most direct values or key statements for each of the 'Target Fields for Summarization' from the IR document. If a direct value is not found, state "정보 없음" or a brief reason.
*   **Output:** A very concise summary (1-2 sentences per field, or a bulleted list) presenting these extracted key facts with minimal context. Focus on accuracy and directness.
    *   Example for "연간 매출": "2023년 연간 매출: 10억 원." or "연간 매출: 현재 비공개, 성장세 강조."
    *   Example for "경쟁사": "주요 경쟁사: A사, B사 언급." or "경쟁사: 구체적 언급 없음, 시장 선도 목표."

---

**Stage 2: Denser Summary (Contextual Integration)**
*   **Objective:** Re-write the Stage 1 summary to be more fluent and integrated. Add relevant context, brief explanations, or supporting details for the extracted field values from the surrounding text in the IR document. If multiple target fields are related, start to show these connections.
*   **Guidelines:**
    *   Do not simply list facts; weave them into a coherent narrative.
    *   Incorporate 1-2 additional pieces of relevant information (entities, brief explanations, or supporting data points from the IR document) for each target field, or for the summary as a whole, compared to Stage 1.
    *   Maintain conciseness but improve readability and information flow.
    *   If a field had "정보 없음" in Stage 1, explain briefly why based on the document (e.g., "초기 단계로 매출 비공개 상태이며, 대신 사용자 증가율에 집중하고 있음.").
*   **Output:** A more detailed paragraph-style summary that connects the key facts with their immediate context.

---

**Stage 3: Densest Summary (Comprehensive Overview & Insights)**
*   **Objective:** Create the most informative summary by further enriching the Stage 2 summary. Incorporate more nuanced details, interconnections between different target fields, and potentially implied insights or strategic importance as suggested by the IR document.
*   **Guidelines:**
    *   Fuse and compress information effectively to add more detail without excessive length.
    *   Incorporate another 1-2 significant pieces of information (e.g., specific strategies related to a field, quantitative backing, future outlook related to a field, comparisons if available) for each target field or for the overall narrative.
    *   The summary should provide a good, self-contained overview of the startup's position regarding the target fields.
    *   If information for a field remains absent, reflect this accurately within the broader context.
*   **Output:** A rich, concise, and insightful summary that provides a comprehensive understanding of the IR document's content related to the specified target fields.

---

Please generate the 3-stage CoD summary focusing on the 'Target Fields for Summarization'.
Present each stage clearly labeled./no_think"""
    )
    
    # 분석 프롬프트 저장용 (MD 내용 생략)
    os.makedirs("prompt", exist_ok=True)
    prompt_for_save = (
        "Analyze why these fields couldn't be extracted from the Korean startup IR document:\n\n"
        f"Failed fields: {failed_fields_sample}\n\n"
        "For each field, provide:\n"
        "- Korean keywords to look for\n"
        "- Likely section/table names\n"
        "- Alternative extraction approach\n\n"
        f"MD content: [MD_CONTENT_OMITTED - {len(md_content)} characters]\n\n"
        "Keep response concise. Focus on actionable extraction tips."
    )
    
    with open(f"prompt/iteration_{iteration:02d}_analyze_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_for_save)
    print(f"  Analysis prompt saved to: prompt/iteration_{iteration:02d}_analyze_prompt.txt")
    
    result = llm.invoke(prompt)
    analysis_feedback = re.sub(r'<think>.*?</think>', '', result.content, flags=re.DOTALL).strip()
    
    # 분석 응답 저장
    with open(f"prompt/iteration_{iteration:02d}_analyze_response.txt", "w", encoding="utf-8") as f:
        f.write(analysis_feedback)
    print(f"  Analysis response saved to: prompt/iteration_{iteration:02d}_analyze_response.txt")
    
    print(f"  Analysis feedback received: {len(analysis_feedback)} characters")
    
    return {
        **state,
        "analysis_feedback": analysis_feedback,
        "no_progress_count": state["no_progress_count"],  # 분석 후에도 카운트 유지
        "last_action": "analyze"
    }

# 종료 조건 체크
def should_continue(state: ExtractionState) -> str:
    """다음 단계를 결정합니다."""
    info = state["info"]
    last_action = state.get("last_action", "start")
    
    # 검증 완료 확인
    if last_action == "verify_complete":
        return "end"
    
    # 검증 중인 경우 계속 검증
    if last_action == "verify":
        return "verify"
    
    # 추출이 끝났는지 확인
    fields_to_fill = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None]
    
    # 모든 필드가 채워졌으면 검증 시작
    if not fields_to_fill:
        filled_count = len([field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is not None])
        print(f"추출 완료! 채워진 필드: {filled_count}개")
        print("🔍 검증 단계를 시작합니다...")
        return "verify"
    
    # 진전이 없으면 종료
    if state["no_progress_count"] >= 5:
        filled_count = len([field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is not None])
        print(f"추출 완료 (진전 없음). 채워진 필드: {filled_count}개")
        
        # 채워진 필드가 있으면 검증 시작
        if filled_count > 0:
            print("🔍 검증 단계를 시작합니다...")
            return "verify"
        else:
            print("검증할 필드가 없어 종료합니다.")
            return "end"
    
    # 방금 analyze를 했다면 반드시 extract로
    if last_action == "analyze":
        return "extract"
    
    # 2회 이상 진전이 없으면 분석 실행
    if state["no_progress_count"] >= 2:
        return "analyze"
    
    # 그 외에는 계속 추출
    return "extract"

# 그래프 생성
workflow = StateGraph(ExtractionState)

# 노드 추가
workflow.add_node("extract", extract_fields)
workflow.add_node("analyze", analyze_failure)
workflow.add_node("verify", verify_field)

# 시작점 설정
workflow.set_entry_point("extract")

# 조건부 엣지 추가
workflow.add_conditional_edges(
    "extract",
    should_continue,
    {
        "extract": "extract",
        "analyze": "analyze",
        "verify": "verify",
        "end": END
    }
)

workflow.add_conditional_edges(
    "analyze",
    should_continue,
    {
        "extract": "extract",
        "analyze": "analyze",
        "verify": "verify",
        "end": END
    }
)

workflow.add_conditional_edges(
    "verify",
    should_continue,
    {
        "verify": "verify",
        "end": END
    }
)

# 그래프 컴파일
app = workflow.compile()

# 3. md 파일 읽기 및 정보 추출
with open("./data/블루브릿지글로벌.md", "r", encoding="utf-8") as f:
    md_file_content = f.read()

print("=== Starting extraction from 블루브릿지글로벌.md ===")
print(f"MD file content length: {len(md_file_content)} characters")

# 초기 상태 설정
initial_state = ExtractionState(
    info=StartupInvestmentInfo(),
    md_content=md_file_content,
    iteration=0,
    no_progress_count=0,
    analysis_feedback="",
    total_fields=len(StartupInvestmentInfo.model_fields),
    last_action="start",
    verification_index=0,
    verified_fields=[]
)

# 그래프 실행
final_state = app.invoke(initial_state)
info = final_state["info"]

print(f"\n=== Final Results ===")
final_filled = len([field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is not None])
final_ratio = final_filled / len(StartupInvestmentInfo.model_fields) * 100
print(f"Total filled: {final_filled}/{len(StartupInvestmentInfo.model_fields)} ({final_ratio:.1f}%)")
print(f"Verified fields: {len(final_state['verified_fields'])}")
print(f"Final result:")

# 결과를 JSON으로 저장
os.makedirs("result", exist_ok=True)

try:
    # JSON 형태로 저장 시도
    info_dict = info.model_dump()
    
    # 날짜 필드를 문자열로 변환 (JSON 직렬화를 위해)
    for key, value in info_dict.items():
        if hasattr(value, 'isoformat'):  # date 객체인 경우
            info_dict[key] = value.isoformat()
    
    json_result = json.dumps(info_dict, ensure_ascii=False, indent=2)
    
    with open("result/extraction_result.json", "w", encoding="utf-8") as f:
        f.write(json_result)
    print(f"✅ Results saved to: result/extraction_result.json")
    
    # JSON 형태로 출력도 시도
    print("=== JSON 형태 결과 ===")
    print(json_result)
    
except Exception as e:
    print(f"❌ JSON 저장 실패: {e}")
    print("📝 TXT 형태로 저장 시도...")
    
    try:
        # TXT 형태로 저장
        info_dict = info.model_dump()
        
        result_text = f"=== 로보스 IR 추출 결과 ===\n"
        result_text += f"추출 완료: {final_filled}/{len(StartupInvestmentInfo.model_fields)} ({final_ratio:.1f}%)\n"
        result_text += f"검증 완료: {len(final_state['verified_fields'])}개 필드\n\n"
        
        result_text += "=== 채워진 필드 ===\n"
        filled_fields = {k: v for k, v in info_dict.items() if v is not None}
        for field_name, value in filled_fields.items():
            field_desc = StartupInvestmentInfo.model_fields[field_name].description
            result_text += f"✓ {field_name}: {value}\n"
        
        result_text += "\n=== 빈 필드 ===\n"
        empty_fields = {k: v for k, v in info_dict.items() if v is None}
        for field_name, value in empty_fields.items():
            field_desc = StartupInvestmentInfo.model_fields[field_name].description
            result_text += f"✗ {field_name} ({field_desc}): 데이터 없음\n"
        
        with open("result/extraction_result.txt", "w", encoding="utf-8") as f:
            f.write(result_text)
        print(f"✅ Results saved to: result/extraction_result.txt")
        
    except Exception as txt_error:
        print(f"❌ TXT 저장도 실패: {txt_error}")

# 텍스트 형태로 출력
print("\n=== 텍스트 형태 결과 ===")
info_dict = info.model_dump()
for field_name, value in info_dict.items():
    field_desc = StartupInvestmentInfo.model_fields[field_name].description
    print(f"{field_name} ({field_desc}): {value}")

# 빈 필드와 채워진 필드 구분해서 출력
print(f"\n=== 채워진 필드 ===")
filled_fields = {k: v for k, v in info_dict.items() if v is not None}
for field_name, value in filled_fields.items():
    field_desc = StartupInvestmentInfo.model_fields[field_name].description
    print(f"✓ {field_name}: {value}")

print(f"\n=== 빈 필드 ===")
empty_fields = {k: v for k, v in info_dict.items() if v is None}
for field_name, value in empty_fields.items():
    field_desc = StartupInvestmentInfo.model_fields[field_name].description
    print(f"✗ {field_name} ({field_desc}): 데이터 없음")

# 필드 검증 함수
def verify_field(state: ExtractionState) -> ExtractionState:
    """채워진 필드값을 MD 파일과 대조하여 검증합니다."""
    info = state["info"]
    md_content = state["md_content"]
    verification_index = state["verification_index"]
    verified_fields = state["verified_fields"].copy()
    
    # 채워진 필드들만 가져오기
    filled_fields = [(field, getattr(info, field)) for field in StartupInvestmentInfo.model_fields 
                    if getattr(info, field) is not None]
    
    if verification_index >= len(filled_fields):
        print("모든 필드 검증 완료!")
        return {
            **state,
            "last_action": "verify_complete"
        }
    
    current_field, current_value = filled_fields[verification_index]
    field_description = StartupInvestmentInfo.model_fields[current_field].description
    
    print(f"\n[Verification {verification_index + 1}/{len(filled_fields)}] 검증 중: {current_field}")
    print(f"  현재 값: {current_value}")
    print(f"  설명: {field_description}")
    
    # 검증 프롬프트
    prompt = f"""
당신은 한국 스타트업 IR 문서의 데이터 검증 전문가입니다. 
추출된 필드값이 MD 문서의 내용과 일치하는지 검증하고 근거를 제시해주세요.

검증 대상:
- 필드명: {current_field}
- 필드 설명: {field_description}  
- 추출된 값: {current_value}

MD 문서 내용:
```
{md_content}
```

검증 절차:
1. MD 문서에서 해당 필드와 관련된 정보를 찾아주세요
2. 추출된 값이 문서 내용과 일치하는지 판단해주세요
3. 근거가 되는 문서의 구체적인 문장이나 표현을 인용해주세요

응답 형식 (JSON):
{{
    "field_name": "{current_field}",
    "extracted_value": "{current_value}",
    "is_valid": true/false,
    "evidence": "문서에서 찾은 구체적인 근거 문장",
    "corrected_value": "수정이 필요한 경우 올바른 값 (is_valid가 true면 null)",
    "reasoning": "검증 근거 및 판단 이유"
}}

중요한 규칙:
- 문서에 명시적으로 나와있는 정보만 유효하다고 판단
- 추론이나 추측은 유효하지 않음
- 숫자의 경우 단위와 정확한 값 확인
- 날짜의 경우 정확한 형식 확인
- 근거가 불분명하면 is_valid를 false로 설정

JSON만 반환해주세요.
"""
    
    # 프롬프트 저장
    os.makedirs("prompt/verification", exist_ok=True)
    prompt_for_save = (
        f"필드 검증 프롬프트\n\n"
        f"검증 대상:\n"
        f"- 필드명: {current_field}\n"
        f"- 필드 설명: {field_description}\n"
        f"- 추출된 값: {current_value}\n\n"
        f"MD 내용: [MD_CONTENT_OMITTED - {len(md_content)} 문자]\n\n"
        f"검증 절차: MD 문서에서 근거 찾기, 값 일치 여부 판단, 구체적 인용\n"
        f"응답: JSON 형식으로 is_valid, evidence, corrected_value, reasoning 포함"
    )
    
    with open(f"prompt/verification/verify_{current_field}.txt", "w", encoding="utf-8") as f:
        f.write(prompt_for_save)
    print(f"  검증 프롬프트 저장: prompt/verification/verify_{current_field}.txt")
    
    result = llm.invoke(prompt)
    
    # 응답 저장
    with open(f"prompt/verification/verify_{current_field}_response.txt", "w", encoding="utf-8") as f:
        f.write(str(result.content))
    print(f"  검증 응답 저장: prompt/verification/verify_{current_field}_response.txt")
    
    # 결과 처리
    try:
        if isinstance(result.content, str):
            cleaned_content = re.sub(r'<think>.*?</think>', '', result.content, flags=re.DOTALL).strip()
            json_match = re.search(r'\{.*\}', cleaned_content, flags=re.DOTALL)
            if json_match:
                json_str = json_match.group()
                verification_result = json.loads(json_str)
            else:
                print(f"경고: 응답에서 JSON을 찾을 수 없음: {cleaned_content[:100]}...")
                verification_result = {"is_valid": True}  # 기본값으로 유효하다고 판단
        else:
            verification_result = result.content
    except json.JSONDecodeError as e:
        print(f"경고: JSON 파싱 실패: {result.content[:100]}...")
        print(f"JSON 오류: {e}")
        verification_result = {"is_valid": True}  # 기본값으로 유효하다고 판단
    
    # 검증 결과 처리
    is_valid = verification_result.get("is_valid", True)
    evidence = verification_result.get("evidence", "근거 없음")
    corrected_value = verification_result.get("corrected_value")
    reasoning = verification_result.get("reasoning", "검증 완료")
    
    if is_valid:
        print(f"  ✅ 검증 통과")
        print(f"  📝 근거: {evidence[:100]}...")
    else:
        print(f"  ❌ 검증 실패")
        print(f"  📝 이유: {reasoning}")
        print(f"  🔧 수정값: {corrected_value}")
        
        # 값 수정
        if corrected_value is not None:
            setattr(info, current_field, corrected_value)
            print(f"  🔄 {current_field} 값을 '{corrected_value}'로 수정")
        else:
            setattr(info, current_field, None)
            print(f"  🗑️ {current_field} 값을 null로 변경")
    
    # 검증 완료된 필드에 추가
    verified_fields.append(current_field)
    
    return {
        **state,
        "info": info,
        "verification_index": verification_index + 1,
        "verified_fields": verified_fields,
        "last_action": "verify"
    }