import os
import argparse
import re # 정규표현식 모듈 추가
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 0. 상수 정의 ---
MODEL_ID = "qwen3:32b"
BASE_URL = "http://192.168.120.102:11434"

def remove_think_tags(text: str) -> str:
    """LLM의 생각/추론 과정을 담은 <think> 태그를 제거합니다."""
    think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
    return think_pattern.sub("", text).strip()

def generate_summary(document_path: str="data/merged.txt", summary_path: str="data/summary_refined.txt", overwrite: bool = False):
    """
    '점진적 정제(Refine)' 방식으로 문서의 전체 요약본을 생성합니다.
    """
    if not os.path.exists(document_path):
        print(f"오류: 문서 파일을 찾을 수 없습니다 - {document_path}")
        return

    if not overwrite and os.path.exists(summary_path):
        print(f"이미 요약 파일이 존재합니다: {summary_path}")
        print("새로 생성하려면 --overwrite 플래그를 사용하세요.")
        return

    # --- 1. LLM 및 로더, 텍스트 분할기 설정 ---
    print("LLM 및 관련 도구를 로드합니다...")
    llm = ChatOllama(model=MODEL_ID, base_url=BASE_URL, temperature=0)
    
    loader = TextLoader(document_path, encoding='utf-8')
    docs = loader.load()

    # 문서를 청크로 나눔 (청크 사이즈를 4000 -> 2000으로 줄여 처리 부담 감소)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    split_docs = text_splitter.split_documents(docs)
    print(f"'{document_path}' 문서를 {len(split_docs)}개의 청크로 분할했습니다.")

    # --- 2. [설계 강화] 1단계: 보고서의 핵심 주체(회사명) 식별 ---
    print("\n[1단계] 보고서의 핵심 주체(회사명)를 식별합니다...")
    
    identity_prompt_template = """
    당신은 문서의 핵심을 파악하는 AI입니다. 아래 텍스트는 특정 회사에 대한 보고서의 첫 부분입니다.
    이 보고서가 주로 다루고 있는 '주인공' 회사의 공식 명칭(Official Name)을 정확히 찾아주세요.
    다른 협력사나 고객사 이름이 아닌, 이 보고서의 주체가 되는 단 하나의 회사 이름만 답변해야 합니다.
    
    [보고서 첫 부분]
    {text}
    
    [답변]
    회사명:
    """
    identity_prompt = PromptTemplate.from_template(identity_prompt_template)
    identity_chain = identity_prompt | llm | StrOutputParser()
    
    # 첫 번째 청크만 사용하여 회사명 추출
    main_company_name = identity_chain.invoke({"text": split_docs[0].page_content})
    main_company_name = main_company_name.replace("회사명:", "").strip()
    print(f"핵심 주체 식별 완료: {main_company_name}")


    # --- 3. [설계 강화] 2단계: 식별된 회사명을 중심으로 상세 팩트 요약 ---
    print(f"\n[2단계] '{main_company_name}'을 중심으로 상세 팩트 요약을 시작합니다...")

    # Map 프롬프트 (개별 청크 요약)
    map_prompt_template = """
    당신은 '{main_company_name}'에 대한 사업/기술 문서의 일부를 분석하여 핵심 정보를 추출하는 전문 분석가입니다.

    다음 텍스트는 전체 문서의 한 부분입니다. 이 부분에서 '{main_company_name}'과 관련된 다음 항목들의 핵심 내용을 최대한 자세하게, 빠짐없이 목록(bullet points) 형태로 요약해주세요.
    - 주요 내용: 이 텍스트 덩어리의 핵심 주장을 요약합니다.
    - 핵심 기술 및 제품: 언급된 기술, 제품, 서비스, 특허, 인증 정보.
    - 사업 모델 및 전략: 비즈니스 모델, 수익 구조, B2B/B2C 전략, 파트너십.
    - 재무 정보 및 성장 지표: 매출, 이익, 투자, 사용자 수, 검사 수 등 구체적인 수치.
    - 시장 및 경쟁사: 시장 규모, 경쟁사 분석, 시장 내 위치.
    - 팀 및 비전: 팀 구성, 향후 계획, 비전.

    [텍스트 시작]
    {text}
    [텍스트 끝]

    위 텍스트의 핵심 정보 요약:
    """
    map_prompt = PromptTemplate.from_template(map_prompt_template)

    # Combine 프롬프트 (개별 요약본들을 종합)
    combine_prompt_template = """
    당신은 '{main_company_name}'에 대한 여러 요약본들을 종합하여 하나의 완성된 최종 보고서를 작성하는 수석 분석가입니다.

    아래에는 문서의 각기 다른 부분들을 요약한 내용들이 있습니다. 이 모든 정보를 취합하여, 아래 목차 구조에 따라 상세하고 논리적인 최종 핵심 정보 요약 보고서를 작성해주세요.

    - **1. 회사 개요:** 공식 회사명, 대표 제품/서비스, 연락처, 핵심 경영진(CEO, CTO 등).
    - **2. 시장 문제 및 해결책:** 목표 시장의 어떤 문제를 해결하려 하며, 이 회사의 제품/서비스는 어떤 해결책을 제공하는가?
    - **3. 핵심 기술 및 경쟁력:**
        - 보유 기술 및 원리
        - 기술적 성과 (데이터 기반 진단 정확도, 특허, 공식 인증 등)
    - **4. 사업 모델 및 현황:**
        - B2C 및 B2B 등 주요 사업 모델 설명
        - 주요 파트너십 현황
    - **5. 성장 지표 (Traction):** 누적 사용자 수, 서비스 이용 건수, 매출 성장 등 구체적인 성장 지표.
    - **6. 재무 현황 및 계획:**
        - 현재까지의 매출 성과 및 단기 목표
        - 중장기 재무 목표 (매출, 손익분기점 등)
        - 투자 유치 및 자금 사용 계획
    - **7. 종합 평가:** 분석된 정보를 바탕으로 한 회사의 핵심 강점과 기회 요인.

    다음 규칙을 반드시 지켜주세요:
    1. 각 항목에 해당하는 내용을 아래 요약본들에서 모두 찾아서 종합해주세요.
    2. 비슷한 내용은 합치고, 논리적인 흐름에 맞게 재구성해주세요.
    3. 최종 보고서는 반드시 한글로, 완결된 문장 형태로 작성해주세요.

    [개별 요약본들]
    {text}

    [최종 종합 요약 보고서]
    """
    combine_prompt = PromptTemplate.from_template(combine_prompt_template)
    
    # 체인 로드 (Map Reduce 방식)
    summarize_chain = load_summarize_chain(
        llm=llm,
        chain_type="map_reduce",
        map_prompt=map_prompt,
        combine_prompt=combine_prompt,
        return_intermediate_steps=False,
        input_key="input_documents",
        output_key="output_text",
        token_max=8192, # 처리 가능한 최대 토큰 수를 명시적으로 설정
        verbose=True
    )

    # --- 4. 요약 실행 및 저장 ---
    print("\n각 단계별 진행 상황이 아래에 표시됩니다...")
    summary = summarize_chain.invoke({
        "input_documents": split_docs,
        "main_company_name": main_company_name
    })
    
    # 후처리: <think> 태그 제거
    cleaned_summary = remove_think_tags(summary["output_text"])

    print("\n--- [최종 요약본] ---")
    print(cleaned_summary)
    
    # 요약 파일 저장 디렉토리 생성
    summary_dir = os.path.dirname(summary_path)
    if summary_dir and not os.path.exists(summary_dir):
        os.makedirs(summary_dir)

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_summary)
        
    print(f"\n요약본이 성공적으로 저장되었습니다: {summary_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="'점진적 정제' 방식으로 긴 문서를 요약합니다.")
    parser.add_argument(
        "--document_path",
        type=str,
        default="data/십일리터 IR_20250701_141252.txt",
        help="요약할 원본 문서의 경로입니다. (기본값: data/십일리터 IR_20250701_141252.txt)"
    )
    parser.add_argument(
        "--summary_path",
        type=str,
        default="data/summary_refined.txt",
        help="생성된 요약본을 저장할 경로입니다. (기본값: data/summary_refined.txt)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="요약 파일이 이미 존재할 경우 덮어씁니다."
    )
    args = parser.parse_args()

    generate_summary(args.document_path, args.summary_path, args.overwrite) 