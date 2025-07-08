import os
import argparse
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 0. 상수 정의 ---
MODEL_ID = "qwen3:32b"
BASE_URL = "http://192.168.120.102:11434"
FACT_SHEET_PATH = "data/summary_refined.txt"
REPORT_PATH = "ipo_analysis_report.md"

KOSDAQ_REQUIREMENTS = """
### 코스닥 상장 주요 요건

#### 1. 기본 요건
- **납입자본금:** 3억 원 이상
- **자기자본:** 10억 원 이상
- **영업활동 기간:** 3년 이상
- **소액주주:** 500명 이상

#### 2. 주식분산 요건 (다음 중 택1)
- **트랙 1:** 소액주주 500명 이상 + 소액주주 지분율 25% 이상 + 공모 5% 이상
- **트랙 2:** 자기자본 500억 원 이상 + 소액주주 500명 이상 + 공모 10% 이상
- **트랙 3:** 공모 25% 이상 + 소액주주 500명 이상

#### 3. 경영성과 요건 (다음 중 택1)
- **이익실현 요건:**
  - 법인세차감전 계속사업이익 20억 원 + 시가총액 90억 원 이상
  - 법인세차감전 계속사업이익 20억 원 + 자기자본 30억 원 이상
- **이익미실현(테슬라) 요건:**
  - 시가총액 500억 원 + 매출액 30억 원 + 최근 2년 연속 매출증가율 20% 이상
  - 시가총액 1,000억 원 이상 (단독)

#### 4. 기술성장기업 특례
- **자기자본:** 10억 원 이상
- **시가총액:** 90억 원 이상
- **기술평가:** 전문평가기관 A등급 & BBB등급 이상

#### 5. 질적 심사요건
- 기업의 계속성, 경영투명성, 경영안정성 등 종합 평가
"""

def analyze_ipo_viability():
    """
    생성된 팩트 시트와 코스닥 상장 요건을 비교하여 분석 리포트를 생성합니다.
    """
    if not os.path.exists(FACT_SHEET_PATH):
        print(f"오류: 분석의 기반이 될 팩트 시트 파일을 찾을 수 없습니다.")
        print(f"먼저 'summarize_with_refine.py'를 실행하여 '{FACT_SHEET_PATH}'를 생성해주세요.")
        return

    print("LLM을 로드하고 분석을 준비합니다...")
    llm = ChatOllama(model=MODEL_ID, base_url=BASE_URL, temperature=0)

    with open(FACT_SHEET_PATH, 'r', encoding='utf-8') as f:
        company_fact_sheet = f.read()

    analysis_prompt_template = """
    당신은 대한민국 코스닥 시장 상장 전문 컨설턴트입니다.
    제공된 '코스닥 상장 요건'과 '회사 팩트 시트'를 바탕으로, 이 회사의 상장 가능성을 냉철하게 분석하고 평가하는 리포트를 작성해야 합니다.

    [코스닥 상장 요건]
    {kosdaq_reqs}

    [회사 팩트 시트]
    {fact_sheet}
    
    ---
    
    [리포트 작성 지침]
    아래 형식에 맞춰, 각 항목에 대한 평가를 표 형태로 작성하고 종합 의견을 제시해주세요.
    - '회사 현황' 칸에는 팩트 시트에서 관련된 정보를 최대한 찾아 기입하세요.
    - 정보가 없어 판단이 불가능한 경우, '회사 현황'에 '[정보 확인 불가]'라고 명확히 기재하세요.
    - '평가' 칸에는 '충족', '미충족', '일부 충족', '확인 필요' 중 하나로 평가하세요.
    - '추가 필요 정보' 칸에는 평가를 위해 어떤 구체적인 자료가 필요한지 제안해주세요.
    
    ## (주)비메스원 코스닥 상장 가능성 예비 검토 리포트

    | 구분 | 세부 항목 | 상장 기준 | 회사 현황 | 평가 (충족/미충족/확인 필요) | 추가 필요 정보 |
    |:---|:---|:---|:---|:---|:---|
    | **기본 요건** | 납입자본금 | 3억 원 이상 | | | |
    | | 자기자본 | 10억 원 이상 | | | |
    | | 영업 기간 | 3년 이상 | | | |
    | **경영성과** | 이익실현 - 1 | 법인세차감전이익 20억 원 이상 | | | 정식 손익계산서 |
    | | 이익실현 - 2 | 시가총액 90억 원 이상 | | | 주관사 평가 필요 |
    | | 이익미실현(테슬라) - 1 | 시가총액 500억 원 + 매출 30억 + 2년 연속 매출증가율 20% | | | |
    | **기술성장기업**| 기술평가 등급 | A & BBB 이상 | | | 외부 전문평가기관 평가서 |
    | ... | ... | ... | ... | ... | ... |

    ## 종합 의견
    
    **[긍정적 요인]**
    (회사의 기술력, 시장성 등 상장에 유리한 점을 팩트 기반으로 서술)

    **[보완 필요 사항]**
    (상장을 위해 반드시 해결해야 할 과제나 부족한 점을 서술. 특히 확인 불가능한 정량적 지표들을 중심으로 언급)

    **[최종 결론]**
    (현재 정보 기준으로 볼 때, 이 회사가 어떤 상장 트랙(예: 기술성장기업 특례)을 목표로 하는 것이 가장 현실적인지, 그리고 성공적인 상장을 위해 지금부터 준비해야 할 가장 중요한 3가지는 무엇인지 제안)
    """
    
    analysis_prompt = PromptTemplate.from_template(analysis_prompt_template)

    chain = analysis_prompt | llm | StrOutputParser()

    print("상장 가능성 분석 리포트를 생성합니다. 잠시만 기다려주세요...")
    report = chain.invoke({
        "kosdaq_reqs": KOSDAQ_REQUIREMENTS,
        "fact_sheet": company_fact_sheet
    })

    print("\n--- [IPO 상장 가능성 분석 리포트] ---")
    print(report)

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)
        
    print(f"\n리포트가 성공적으로 저장되었습니다: {REPORT_PATH}")

def main():
    """uv run으로 실행할 수 있는 메인 함수"""
    analyze_ipo_viability()

if __name__ == '__main__':
    main() 