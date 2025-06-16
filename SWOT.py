from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnableLambda
import json
import re
from glob import glob
import os

llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

class SWOT(BaseModel):
    strength: Optional[str] = Field(None, description="강점")
    weakness: Optional[str] = Field(None, description="약점")
    opportunity: Optional[str] = Field(None, description="기회")
    threat: Optional[str] = Field(None, description="위협")
    
class S(BaseModel):
    reason: str = Field(description="해당 부분을 강점이라고 한 근거 (실제 문서 내용을 기반으로 작성)")
    contexts: List[str] = Field(description="분석 결과를 바탕으로 핵심 강점들을 요약")

class W(BaseModel):
    reason: str = Field(description="해당 부분을 약점이라고 한 근거 (실제 문서 내용을 기반으로 작성)")
    contexts: List[str] = Field(description="분석 결과를 바탕으로 핵심 약점들을 요약")

class O(BaseModel):
    reason: str = Field(description="해당 부분을 기회라고 한 근거 (실제 문서 내용을 기반으로 작성)")
    contexts: List[str] = Field(description="분석 결과를 바탕으로 핵심 기회들을 요약")

class T(BaseModel):
    reason: str = Field(description="해당 부분을 위협이라고 한 근거 (실제 문서 내용을 기반으로 작성)")
    contexts: List[str] = Field(description="분석 결과를 바탕으로 핵심 위협들을 요약")

class SWOTState(TypedDict):
    swot: SWOT
    iteration: int
    no_progress_count: int

def clean_llm_output(text: str) -> str:
    """LLM 출력에서 <think> 태그를 제거하고 순수한 JSON 문자열만 추출합니다."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text
    
def get_s_analyzer_chain(text: str):
    prompt = PromptTemplate.from_template("""
당신은 SWOT 분석 중 강점(S)을 분석하는 전문가입니다.
The output should be formatted as a JSON instance that conforms to the JSON schema below.

당신은 다음과 같은 원칙을 준수해야 합니다:
    1. 주어진 텍스트 내용에만 근거하여 분석해야 합니다.
    2. 조직의 목표 달성에 도움이 되는 '내부적인 요인', 즉 '강점'만을 식별해야 합니다.
    3. 강점은 구체적이고 명확하게 기술되어야 합니다. (예: '기술력이 좋다' 보다는 'OO 분야에서 특허를 보유한 독점 기술력')
    4. 외부 요인(기회)이나 약점, 위협과 혼동하지 않도록 주의해야 합니다.
    5. 분석 결과를 바탕으로 핵심 강점들을 요약하여 제시해야 합니다.
    6. 기술, 인력, 특허, 재무 등 여러 섹션의 정보를 종합하여 강점을 도출하세요.
    
주어진 텍스트:
{text}
    
Your response must be a JSON object with two keys:
    reason: 해당 부분을 강점이라고 한 근거 (실제 문서 내용을 기반으로 작성)
    contexts: 분석 결과를 바탕으로 핵심 강점들을 요약한 리스트

Here is the output schema:
{{"properties": {{"reason": {{"description": "해당 부분을 강점이라고 한 근거 (실제 문서 내용을 기반으로 작성)", "type": "string"}}, "contexts": {{"description": "분석 결과를 바탕으로 핵심 강점들을 요약", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["reason", "contexts"]}}
""")
    parser = JsonOutputParser(pydantic_object=S)
    chain = prompt | llm | StrOutputParser() | RunnableLambda(clean_llm_output) | parser
    return chain.invoke({"text":text})
    
def get_w_analyzer_chain(text: str):
    prompt = PromptTemplate.from_template("""
당신은 SWOT 분석 중 약점(W)을 분석하는 전문가입니다.
The output should be formatted as a JSON instance that conforms to the JSON schema below.

당신은 다음과 같은 원칙을 준수해야 합니다:
    1. 주어진 텍스트 내용에만 근거하여 분석해야 합니다.
    2. 조직의 목표 달성을 저해하는 '내부적인 요인', 즉 '약점'만을 식별해야 합니다.
    3. 약점은 구체적이고 명확하게 기술되어야 합니다. (예: '자금이 부족하다' 보다는 '신규 프로젝트 투자에 필요한 자금 20% 부족')
    4. 외부 요인(위협)이나 강점, 기회와 혼동하지 않도록 주의해야 합니다.
    5. 분석 결과를 바탕으로 핵심 약점들을 요약하여 제시해야 합니다.
    6. '주요 위험 요인' 항목을 주의 깊게 분석하여 약점을 식별하세요.
    7. 특정 파트너, 기술, 시장에 대한 과도한 의존성도 약점이 될 수 있습니다.
    8. '정보 없음'으로 기재된 항목(예: 핵심 인력 부재, 특정 기술 정보 부재)도 잠재적 약점으로 고려할 수 있습니다.
    9. 제시된 재무 계획이나 목표가 지나치게 낙관적이거나 구체성이 떨어진다면 이 또한 약점으로 지적할 수 있습니다.

주어진 텍스트:
{text}

Your response must be a JSON object with two keys:
    reason: 해당 부분을 약점이라고 한 근거 (실제 문서 내용을 기반으로 작성)
    contexts: 분석 결과를 바탕으로 핵심 약점들을 요약한 리스트

Here is the output schema:
{{"properties": {{"reason": {{"description": "해당 부분을 약점이라고 한 근거 (실제 문서 내용을 기반으로 작성)", "type": "string"}}, "contexts": {{"description": "분석 결과를 바탕으로 핵심 약점들을 요약", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["reason", "contexts"]}}
        """)
    parser = JsonOutputParser(pydantic_object=W)
    chain = prompt | llm | StrOutputParser() | RunnableLambda(clean_llm_output) | parser
    return chain.invoke({"text":text})
    
def get_o_analyzer_chain(text: str):
    prompt = PromptTemplate.from_template(
        """
당신은 SWOT 분석 중 기회(O)를 분석하는 전문가입니다.
The output should be formatted as a JSON instance that conforms to the JSON schema below.

당신은 다음과 같은 원칙을 준수해야 합니다:
    1. 주어진 텍스트 내용에만 근거하여 분석해야 합니다.
    2. 조직에 긍정적인 영향을 줄 수 있는 '외부 환경 요인', 즉 '기회'만을 식별해야 합니다.
    3. 기회는 시장 동향, 기술 발전, 정책 변화, 경쟁사 동향 등 외부 환경의 변화에서 찾아야 합니다.
    4. 내부적인 요인(강점)이나 위협, 약점과 혼동하지 않도록 주의해야 합니다.
    5. 분석 결과를 바탕으로 핵심 기회들을 요약하여 제시해야 합니다.
    6. 시장 동향, 기술 발전, 정책 변화 외에도, 새로운 파트너십, 투자 유치 계획, 사업 확장 전략 등에서 기회 요인을 찾을 수 있습니다.

주어진 텍스트:
{text}

Your response must be a JSON object with two keys:
    reason: 해당 부분을 기회라고 한 근거 (실제 문서 내용을 기반으로 작성)
    contexts: 분석 결과를 바탕으로 핵심 기회들을 요약한 리스트

Here is the output schema:
{{"properties": {{"reason": {{"description": "해당 부분을 기회라고 한 근거 (실제 문서 내용을 기반으로 작성)", "type": "string"}}, "contexts": {{"description": "분석 결과를 바탕으로 핵심 기회들을 요약", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["reason", "contexts"]}}
        """
    )
    parser = JsonOutputParser(pydantic_object=O)
    chain = prompt | llm | StrOutputParser() | RunnableLambda(clean_llm_output) | parser
    return chain.invoke({"text":text})
    
def get_t_analyzer_chain(text: str):
    prompt = PromptTemplate.from_template(
        """
당신은 SWOT 분석 중 위협(T)을 분석하는 전문가입니다.
The output should be formatted as a JSON instance that conforms to the JSON schema below.

당신은 다음과 같은 원칙을 준수해야 합니다:
    1. 주어진 텍스트 내용에만 근거하여 분석해야 합니다.
    2. 조직에 부정적인 영향을 줄 수 있는 '외부 환경 요인', 즉 '위협'만을 식별해야 합니다.
    3. 위협은 새로운 경쟁자의 등장, 시장 축소, 법규 규제 강화 등 외부 환경의 부정적 변화에서 찾아야 합니다.
    4. 내부적인 요인(약점)이나 기회, 강점과 혼동하지 않도록 주의해야 합니다.
    5. 분석 결과를 바탕으로 핵심 위협들을 요약하여 제시해야 합니다.
    6. '주요 경쟁사' 정보를 바탕으로 경쟁 심화, 시장 점유율 하락 등의 위협을 분석하세요.
    7. '주요 위험 요인'으로 언급된 외부 환경 변화나 시장의 불확실성을 위협으로 식별하세요.
    8. 기회 요인의 이면(예: 미중 분쟁으로 인한 반사이익은, 반대로 정치 상황 변화에 따른 리스크가 될 수 있음)에 있는 잠재적 위협도 고려하세요.

주어진 텍스트:
{text}

Your response must be a JSON object with two keys:
    reason: 해당 부분을 위협이라고 한 근거 (실제 문서 내용을 기반으로 작성)
    contexts: 분석 결과를 바탕으로 핵심 위협들을 요약한 리스트

Here is the output schema:
{{"properties": {{"reason": {{"description": "해당 부분을 위협이라고 한 근거 (실제 문서 내용을 기반으로 작성)", "type": "string"}}, "contexts": {{"description": "분석 결과를 바탕으로 핵심 위협들을 요약", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["reason", "contexts"]}}
        """
    )
    parser = JsonOutputParser(pydantic_object=T)
    chain = prompt | llm | StrOutputParser() | RunnableLambda(clean_llm_output) | parser
    return chain.invoke({"text":text})

if __name__ == "__main__":
    jsons = glob('./*.json')
    
    output_dir = 'result'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for name in jsons:
        with open(name, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cleaned_data = {k: v for k, v in data.items() if v is not None and v != ""}
        text_input = json.dumps(cleaned_data, ensure_ascii=False, indent=2)

        print("="*20 + " SWOT 분석 시작 " + "="*20)
        print(f"입력 데이터:\n{text_input}\n")

        s_result = get_s_analyzer_chain(text_input)
        print("--- 강점 (Strength) 분석 결과 ---")
        print(f"근거: {s_result['reason']}")
        print(f"핵심 강점: {s_result['contexts']}")
        print("-" * 50)

        w_result = get_w_analyzer_chain(text_input)
        print("--- 약점 (Weakness) 분석 결과 ---")
        print(f"근거: {w_result['reason']}")
        print(f"핵심 약점: {w_result['contexts']}")
        print("-" * 50)

        o_result = get_o_analyzer_chain(text_input)
        print("--- 기회 (Opportunity) 분석 결과 ---")
        print(f"근거: {o_result['reason']}")
        print(f"핵심 기회: {o_result['contexts']}")
        print("-" * 50)

        t_result = get_t_analyzer_chain(text_input)
        print("--- 위협 (Threat) 분석 결과 ---")
        print(f"근거: {t_result['reason']}")
        print(f"핵심 위협: {t_result['contexts']}")
        print("-" * 50)

        # 전체 SWOT 분석 결과를 딕셔너리로 묶기
        swot_results = {
            "strength": s_result,
            "weakness": w_result,
            "opportunity": o_result,
            "threat": t_result,
        }

        # JSON 파일로 저장
        input_filename = os.path.splitext(os.path.basename(name))[0]
        output_path = os.path.join(output_dir, f'swot_analysis_{input_filename}.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(swot_results, f, ensure_ascii=False, indent=4)
        
        print(f"\n✅ SWOT 분석 결과가 {output_path} 에 성공적으로 저장되었습니다.")
    
