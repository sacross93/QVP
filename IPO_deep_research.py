import json
import re
import os
import time # 시간 지연을 위해 time 모듈 추가
import argparse # 인자 처리를 위해 추가
import datetime # 파일 저장을 위해 datetime 모듈 추가
from glob import glob
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain.retrievers.multi_query import MultiQueryRetriever
import sys
from langchain_core.embeddings import Embeddings

# --- 0. 상수 정의 ---
VECTOR_DB_PATH = "chroma_db_bge_m3_ko"
DOCUMENT_PATH = "data/merged.txt"
SUMMARY_PATH = "data/summary_refined.txt" # 요약 파일 경로 추가
MODEL_ID = "dragonkue/bge-m3-ko"

# 코스닥 상장 규정 텍스트 (지식 베이스로 활용)
KOSDAQ_LISTING_REQUIREMENTS = """
### 코스닥 상장 수치 기준

#### 기본 요건
- **납입자본금**: 3억 원 이상
- **자기자본**: 10억 원 이상
- **소액주주**: 500명 이상
- **영업활동 기간**: 3년 이상

#### 주식분산 요건 (택1)
- **트랙 1**: 소액주주 500명 이상 + 소액주주 지분율 25% 이상 + 공모 5% 이상
- **트랙 2**: 자기자본 500억 원 이상 + 소액주주 500명 이상 + 공모 10% 이상
- **트랙 3**: 공모 25% 이상 + 소액주주 500명 이상

#### 경영성과 요건 (다양한 트랙 중 택1)
- **이익실현 상장요건**:
  - 법인세 차감전 계속사업이익 20억 원 + 시가총액 90억 원 이상
  - 법인세 차감전 계속사업이익 20억 원 + 자기자본 30억 원 이상
  - 시가총액 200억 원 + 매출액 100억 원 이상 + 계속사업이익 발생
  - 계속사업이익 50억 원 이상 (단독 요건)
- **이익미실현 상장요건(테슬라 요건)**:
  - 시가총액 500억 원 + 매출액 30억 원 + 최근 2년 연속 매출증가율 20% 이상
  - 시가총액 1,000억 원 이상 (단독 요건)
  - 자기자본 250억 원 이상 (단독 요건)
  - 시가총액 300억 원 + 매출액 100억 원 이상

#### 기술성장기업 특례
- **자기자본**: 10억 원 이상
- **시가총액**: 90억 원 이상
- **기술평가**: 전문평가기관 A등급 & BBB등급 이상

#### 기타 질적 심사요건
- **감사 요건**: 최근 사업연도 재무제표에 대한 지정감사인의 '적정' 감사의견 필수
- **기업 계속성, 경영 투명성, 경영 안정성** 종합 평가
"""

# --- 1. LLM, 임베딩 모델, 텍스트 분할기 설정 ---
print("LLM 및 임베딩 모델을 로드합니다...")
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

# 임베딩 모델 로드 (HuggingFaceEmbeddings 래퍼 대신 직접 사용)
embedding_model = SentenceTransformer(MODEL_ID)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, # 청크 크기를 약간 줄여 맥락 집중
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

# Langchain의 Embeddings 클래스를 상속받아 직접 구현
class CustomSentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """텍스트 목록을 임베딩합니다."""
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        """단일 텍스트를 임베딩합니다."""
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()

# --- 웹 검색 기능 추가 ---
def web_search_company_info(company_name: str, search_query: str) -> str:
    """
    웹 검색을 통해 회사 정보를 찾습니다.
    DuckDuckGo를 사용하여 안전하고 개인정보 보호에 중점을 둔 검색을 수행합니다.
    """
    try:
        # duckduckgo-search 패키지를 설치해야 함: pip install duckduckgo-search
        from duckduckgo_search import DDGS
        
        ddgs = DDGS()
        search_term = f"{company_name} {search_query}"
        
        print(f"  🔍 웹 검색: '{search_term}'")
        
        # 검색 결과를 가져옵니다 (최대 5개)
        results = ddgs.text(search_term, max_results=5)
        
        if not results:
            return "웹 검색 결과를 찾을 수 없습니다."
        
        # 검색 결과를 포맷팅합니다
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'N/A')
            snippet = result.get('body', 'N/A')
            url = result.get('href', 'N/A')
            
            formatted_result = f"""
[검색 결과 {i}]
제목: {title}
내용: {snippet}
출처: {url}
"""
            formatted_results.append(formatted_result)
        
        return "\n".join(formatted_results)
        
    except ImportError:
        print("  ⚠️ duckduckgo-search 패키지가 설치되지 않았습니다.")
        print("  설치 명령: pip install duckduckgo-search")
        return "웹 검색 기능을 사용하려면 duckduckgo-search 패키지를 설치해주세요."
    except Exception as e:
        print(f"  ❌ 웹 검색 중 오류 발생: {e}")
        return f"웹 검색 중 오류가 발생했습니다: {str(e)}"

# 정보 충족도 분석 함수
def analyze_information_sufficiency(content: str) -> bool:
    """
    주어진 내용이 충분한 정보를 포함하고 있는지 분석합니다.
    """
    if not content or content.strip() == "":
        return False
    
    # 정보 부족을 나타내는 키워드들
    insufficient_indicators = [
        "관련 정보를 찾을 수 없음",
        "정보 부족",
        "확인 필요",
        "데이터 없음",
        "N/A",
        "정보가 없습니다",
        "찾을 수 없습니다"
    ]
    
    content_lower = content.lower()
    for indicator in insufficient_indicators:
        if indicator.lower() in content_lower:
            return False
    
    # 최소 길이 체크 (매우 짧은 내용은 불충분하다고 판단)
    if len(content.strip()) < 50:
        return False
        
    return True

# 웹 검색 쿼리 생성 체인
web_search_query_prompt = PromptTemplate.from_template(
    """당신은 웹 검색 전문가입니다. 
    
회사명: {company_name}
분석 항목: {analysis_item}

위 회사에 대해 해당 분석 항목의 정보를 찾기 위한 효과적인 웹 검색 쿼리를 생성해주세요.
검색 쿼리는 한국어로 작성하고, 실제 검색 엔진에서 좋은 결과를 얻을 수 있도록 구체적이고 명확해야 합니다.

JSON 형식으로 3개의 다양한 검색 쿼리를 제공해주세요:
{{"queries": ["검색쿼리1", "검색쿼리2", "검색쿼리3"]}}"""
)

web_search_query_chain = (
    web_search_query_prompt
    | llm
    | JsonOutputParser()
    | RunnableLambda(lambda x: x.get("queries", []))
)

# --- 유틸리티 함수 ---
def read_file_content(filepath: str) -> str:
    """파일 내용을 읽어 문자열로 반환합니다."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"경고: {filepath} 파일을 찾을 수 없습니다.")
        return ""

# --- 2. 오프라인: 벡터 데이터베이스 설정 (지식 베이스 구축) ---
def get_vectorstore() -> Chroma:
    """
    문서에서 벡터 DB를 생성하거나 기존 DB를 로드합니다.
    '오프라인: 문서 처리 및 지식 베이스 구축' 단계에 해당합니다.
    """
    # Langchain 호환 임베딩 함수 래퍼를 먼저 생성
    embedding_function_wrapper = CustomSentenceTransformerEmbeddings(embedding_model)

    if os.path.exists(VECTOR_DB_PATH):
        print(f"기존 벡터 DB를 로드합니다: {VECTOR_DB_PATH}")
        vectorstore = Chroma(
            persist_directory=VECTOR_DB_PATH,
            embedding_function=embedding_function_wrapper # 로드 시점부터 래퍼를 지정
        )
        return vectorstore
    else:
        print(f"새로운 벡터 DB를 생성합니다. 문서: {DOCUMENT_PATH}")
        print("문서를 로드하고 청크로 분할합니다...")
        with open(DOCUMENT_PATH, 'r', encoding='utf-8') as f:
            text = f.read()

        docs_list = text_splitter.split_text(text)
        
        print(f"{len(docs_list)}개의 청크로 분할되었습니다. 임베딩 및 DB 생성을 시작합니다...")
        
        vectorstore = Chroma.from_texts(
            texts=docs_list,
            embedding=embedding_function_wrapper, # 생성 시에도 래퍼를 사용
            ids=[str(i) for i in range(len(docs_list))],
            persist_directory=VECTOR_DB_PATH,
        )
        vectorstore.persist()
        print("벡터 DB 생성 및 저장이 완료되었습니다.")
        
        return vectorstore


# --- 3. 온라인: RAG 파이프라인 구성 ---

# 3-1. 질문 분해 (Query Decomposition)
query_decomposition_prompt = PromptTemplate.from_template(
    """당신은 사용자의 복합적인 질문을 여러 개의 간단한 하위 질문으로 분해하는 전문가입니다.
각 하위 질문은 독립적으로 검색하여 답변을 찾을 수 있어야 합니다.
사용자의 질문에 대한 답변을 찾기 위해 필요한 모든 검색 쿼리를 생성하세요.

사용자 질문: "{question}"

각 하위 질문을 명확하게 구분하여 JSON 형식의 리스트로 반환해주세요. 예: {{"queries": ["질문 1", "질문 2", "질문 3"]}}
"""
)

decompose_chain = (
    query_decomposition_prompt
    | llm
    | JsonOutputParser()
    | RunnableLambda(lambda x: x.get("queries", []))
)

# 3-2. 검색 및 컨텍스트 포맷팅
def format_docs(docs: List[Document]) -> str:
    """검색된 문서를 프롬프트에 삽입하기 좋은 형태로 포맷합니다."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)

# 3-3. 최종 답변 생성 프롬프트
final_prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     """당신은 제공된 컨텍스트 정보를 바탕으로 사용자의 질문에 대해 종합적이고 상세한 답변을 생성하는 AI 어시스턴트입니다.
컨텍스트에 없는 내용은 답변에 포함하지 마세요. 모든 답변은 컨텍스트에 근거해야 합니다.
만약 컨텍스트만으로 답변하기 어려운 경우, "제공된 정보만으로는 답변하기 어렵습니다."라고 솔직하게 답변하세요.

[컨텍스트 정보]
{context}
"""),
    ("human", "[원본 질문]\n{question}"),
    ("ai", "답변:")
])


# --- 4. 새로운 파이프라인: IPO 보고서 생성 ---

# 4-1. 분석 체크리스트 생성 체인
checklist_generation_prompt = PromptTemplate.from_template(
    """당신은 IPO 전문가입니다. 주어진 코스닥 상장 규정을 바탕으로 특정 회사의 상장 가능성을 분석하기 위해 반드시 확인해야 할 항목들을 구체적인 질문 형태의 JSON 리스트로 만들어주세요.

[코스닥 상장 규정]
{regulations}

JSON 형식 예시: {{"checklist": ["질문 1", "질문 2", "질문 3"]}}"""
)

checklist_chain = (
    checklist_generation_prompt
    | llm
    | JsonOutputParser()
    | RunnableLambda(lambda x: x.get("checklist", []))
)

# 4-2. 최종 보고서 생성 체인
report_generation_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """당신은 M&A 및 IPO 전문 컨설턴트입니다. 아래 제공된 [정보]들을 바탕으로 '{company_name}'의 코스닥 상장 가능성을 분석하고, 향후 1~2년 내 상장을 위한 로드맵을 제시하는 보고서를 작성해 주십시오.

모든 분석과 주장은 반드시 제공된 [정보]에 근거해야 합니다. 만약 특정 항목에 대한 정보가 부족하다면, "정보 부족" 또는 "확인 필요"라고 명확하게 명시해야 합니다. 보고서는 다음 두 가지 핵심 섹션을 포함해야 합니다.

1. **현황 진단**: 각 상장 요건(자본, 경영 성과, 기술성 등)에 대해 '{company_name}'의 현재 상태를 조목조목 비교 분석하여 '충족', '미충족', '정보 부족'으로 판정합니다.
2. **실행 계획 (Roadmap)**: '미충족' 또는 '정보 부족'으로 판단된 항목들을 해결하고 1~2년 내 상장을 위해 무엇을, 언제까지, 어떻게 준비해야 하는지에 대한 구체적인 실행 계획을 제시합니다.

---
[정보 1: 코스닥 상장 규정]
{regulations}
---
[정보 2: {company_name} 현황 요약]
{summary}
---
[정보 3: 항목별 심층 분석 자료 (내부 데이터 기반)]
{analysis_results}
---

[보고서 작성 시작]"""),
    ("human", "위 정보를 바탕으로 보고서를 작성해주세요."),
])

report_chain = (
    report_generation_prompt
    | llm
    | StrOutputParser()
)


# --- 5. 전체 파이프라인 실행 ---
def generate_ipo_report(company_name: str):
    """IPO 상장 가능성 분석 보고서 생성 파이프라인을 실행합니다."""

    # 1단계: 지식 베이스 준비 (VectorDB, 요약본, 규정)
    print("[1단계] 지식 베이스를 준비합니다 (VectorDB, 요약본, 규정)...")
    vectorstore = get_vectorstore()
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # 각 항목 당 3개 청크 검색

    # MultiQueryRetriever를 위한 프롬프트 정의 (키워드 추출 강화)
    MULTI_QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template="""당신은 AI 언어 모델 보조입니다. 당신의 임무는 사용자 질문에서 검색에 사용할 여러 쿼리를 생성하는 것입니다.
사용자 질문의 의미를 폭넓게 파악하기 위한 다양한 형태의 '하위 질문'과, 가장 핵심적인 정보를 직접 찾기 위한 '핵심 키워드'를 모두 생성해주세요.
이렇게 생성된 질문과 키워드는 벡터 데이터베이스에서 관련 문서를 찾는 데 사용됩니다.
각 쿼리는 줄바꿈으로 구분하여 제공하세요.

원본 질문: {question}"""
    )

    multi_query_retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever, llm=llm, prompt=MULTI_QUERY_PROMPT
    )

    company_summary = read_file_content(SUMMARY_PATH)
    
    if not company_summary:
        print("오류: 회사 요약 정보를 불러올 수 없어 프로세스를 중단합니다.")
        return

    # 2단계: 분석 체크리스트 생성
    print("\n[2단계] 코스닥 상장 규정을 바탕으로 분석 체크리스트를 생성합니다...")
    checklist = checklist_chain.invoke({"regulations": KOSDAQ_LISTING_REQUIREMENTS})
    print("생성된 분석 체크리스트:")
    for item in checklist:
        print(f"- {item}")

    # 3단계: 각 체크리스트 항목에 대해 RAG 수행 (로컬 DB + 웹 검색)
    print("\n[3단계] 각 체크리스트 항목에 대해 정보를 수집합니다 (로컬 DB + 웹 검색)...")
    analysis_results_list = []
    
    for i, item in enumerate(checklist, 1):
        print(f"\n  📋 [{i}/{len(checklist)}] 분석 중: \"{item}\"")
        
        # 3-1: 먼저 로컬 벡터 DB에서 검색
        print("    📚 로컬 데이터베이스 검색...")
        retrieved_docs = multi_query_retriever.invoke(item)
        local_context = format_docs(retrieved_docs)
        
        # 3-2: 로컬 정보가 충분하지 않으면 웹 검색 수행
        is_local_sufficient = analyze_information_sufficiency(local_context)
        web_context = ""
        
        if not is_local_sufficient:
            print("    🌐 로컬 정보 부족으로 웹 검색을 시작합니다...")
            
            # 웹 검색 쿼리 생성
            search_queries = web_search_query_chain.invoke({
                "company_name": company_name,
                "analysis_item": item
            })
            
            web_results = []
            for query in search_queries[:2]:  # 처음 2개 쿼리만 사용
                web_result = web_search_company_info(company_name, query)
                web_results.append(f"검색쿼리: {query}\n{web_result}")
                time.sleep(2)  # 웹 검색 간 지연
            
            web_context = "\n\n---\n\n".join(web_results)
        else:
            print("    ✅ 로컬 데이터베이스에서 충분한 정보를 찾았습니다.")
        
        # 3-3: 최종 컨텍스트 구성
        final_context = ""
        if local_context and local_context.strip():
            final_context += f"[로컬 데이터]\n{local_context}"
        
        if web_context and web_context.strip():
            if final_context:
                final_context += "\n\n---\n\n"
            final_context += f"[웹 검색 결과]\n{web_context}"
        
        if not final_context.strip():
            final_context = "로컬 및 웹 검색에서 관련 정보를 찾을 수 없음."
        
        analysis_results_list.append(f"- 질문: {item}\n- 자료: {final_context}")

    analysis_results_str = "\n".join(analysis_results_list)
    print("\n✅ 모든 정보 수집이 완료되었습니다.")

    # 4단계: 수집된 정보를 종합하여 최종 보고서 생성
    print("\n[4단계] 수집된 모든 정보를 종합하여 최종 보고서를 생성합니다...")
    final_report = report_chain.invoke({
        "company_name": company_name,
        "regulations": KOSDAQ_LISTING_REQUIREMENTS,
        "summary": company_summary,
        "analysis_results": analysis_results_str
    })
    
    # 5단계: 결과 출력
    print("\n=========================================")
    print(f"        {company_name} KOSDAQ 상장 가능성 분석 보고서")
    print("=========================================\n")
    print(final_report)

    # 6단계: 결과 파일로 저장
    output_dir = "result"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"IPO_report_{timestamp}.md")

    # <think> 블록을 정규표현식을 사용하여 제거
    report_content_for_file = re.sub(r'<think>.*?</think>', '', final_report, flags=re.DOTALL).strip()

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {company_name} KOSDAQ 상장 가능성 분석 보고서\n\n")
            f.write(f"보고서 생성 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(report_content_for_file)
        print(f"\n보고서가 다음 경로에 저장되었습니다: {filepath}")
    except Exception as e:
        print(f"\n오류: 보고서를 파일로 저장하는 중 문제가 발생했습니다 - {e}")


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description="지능형 RAG 파이프라인을 사용하여 복합 질문에 답변합니다.")
    # parser.add_argument("question", type=str, help="LLM에게 할 복합 질문")
    # args = parser.parse_args()
    # main(args.question)

    generate_ipo_report(company_name="(주)비에스원")

    # 예시 질문:
    # python IPO_deep_research.py "ROBOS의 주요 제품과 기술은 무엇이며, 주요 경쟁사는 어디인가요? 그리고 회사의 재무 상태는 어떤가요?"