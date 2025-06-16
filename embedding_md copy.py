from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
import torch
import json
import os

# GPU 장치 설정
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# md file path
file_path = "./data/델타엑스인수안.md"
# file_path = "./data/블루브릿지글로벌.md"
print(f"\n분석 대상 파일: {file_path}")
# ---------------------------------------------

# Download from the 🤗 Hub
print("Embedding 모델을 로드합니다...")
model = SentenceTransformer("dragonkue/bge-m3-ko", device=device)

with open(file_path, "r", encoding="utf-8") as f:
    md_file_content = f.read()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=300
)
# separators=["\n\n---\n\n", "\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""] # 마크다운 구조에 최적화된 구분자
sentences = text_splitter.split_text(md_file_content)

llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0,
    timeout=120
)

def generate_answer(llm, context, query):
    prompt = f"""당신은 주어진 문서에서 특정 정보만을 정확하게 추출하는 AI입니다.
    
# 지시사항
- '문서' 내용을 바탕으로 '질문'에 대한 답변을 찾으세요.
- **찾은 정보만으로 답변을 구성하고, 추가적인 설명은 절대 포함하지 마세요.**
- **만약 질문에 대한 정보를 일부만 찾았다면, 찾은 부분만으로 답변해주세요.**
- 문서에서 질문에 대한 정보를 **전혀** 찾을 수 없는 경우에만, 오직 **'정보 없음'** 이라고만 답변해주세요.
- 답변은 최대한 간결하게 작성해주세요.

# 문서
```
{context}
```

# 질문
```{query}```

답변
"""

    try:
        response = llm.invoke(prompt)
        raw_answer = response.content

        # <think> 태그가 있는 경우, 해당 블록을 제거하고 순수 답변만 추출
        if "</think>" in raw_answer:
            answer = raw_answer.split("</think>")[-1].strip()
        else:
            answer = raw_answer.strip()
            
    except Exception as e:
        answer = f"LLM 호출 중 오류 발생: {e}"

    return answer

# Run inference
print("문서 청크를 임베딩합니다...")
embeddings = model.encode(sentences)
print(f"총 {len(sentences)}개의 청크로 분할되었습니다.")


# 어떤 IR 문서에도 적용 가능한 일반적인 질문 목록
queries = [
    # === 회사 기본 정보 ===
    "회사 공식 명칭은 무엇인가요?",
    "회사의 설립일은 언제인가요?",
    "회사의 주요 사업 분야와 핵심 제품 또는 서비스는 무엇인가요?",
    "회사의 비전이나 슬로건은 무엇인가요?",
    "본사(소재지) 및 연구소의 주소는 어디인가요?",
    "대표 연락처(전화번호, 이메일)는 무엇인가요?",
    "회사의 주요 연혁과 마일스톤은 무엇인가요?",

    # === 경영진 및 팀 ===
    "대표이사(CEO)의 이름과 주요 경력은 무엇인가요?",
    "핵심 경영진(CTO, CIO, CFO 등)의 이름과 주요 경력은 무엇인가요?",
    "총 임직원 수는 몇 명인가요?",
    "주요 주주 구성 및 지분율은 어떻게 되나요?",

    # === 시장 및 문제 정의 ===
    "회사가 목표로 하는 시장과 해결하고자 하는 문제점은 무엇인가요?",
    "목표 시장의 전체 규모(TAM, SAM, SOM)는 어느 정도로 추정하고 있나요?",
    "주요 경쟁사는 어디이며, 이들과의 경쟁 상황은 어떤가요?",

    # === 제품 및 기술 ===
    "회사의 주요 제품 또는 서비스 라인업은 어떻게 구성되어 있나요?",
    "경쟁사 대비 자사 제품/서비스가 가지는 핵심적인 차별점이나 경쟁 우위는 무엇인가요?",
    "회사의 핵심 기술은 무엇이며, 그 특징은 무엇인가요?",
    "보유하고 있는 특허나 지적재산권 현황은 어떤가요?",
    "향후 기술 또는 서비스의 개발 로드맵이나 확장 계획이 있나요?",

    # === 사업 전략 및 현황 ===
    "지금까지의 주요 사업 성과나 실적(매출, 사용자 수, 계약 등)은 무엇인가요?",
    "향후 재무 추정치(매출, 영업이익 등)는 어떻게 예상하고 있나요?(재무 현황)",
    "회사의 비즈니스 모델 또는 주요 수익원은 무엇인가요?",
    "주요 목표 고객은 누구인가요?",
    "해외 시장 진출 계획이나 전략이 있다면 무엇인가요?",
    "향후 사업화 계획이나 성장 전략을 단계별로 설명해주세요.",
    "회사가 강조하는 핵심 투자 포인트는 무엇인가요?",
    "사업의 주요 위험 요인과 대응 전략은 무엇인가요?",
    "회사의 엑시트(Exit) 전략은 무엇인가요? (IPO, M&A 등)",

    # === 자금 조달 ===
    "이번 투자의 주요 조건(투자 방식, 기업가치, 특약 등)은 무엇인가요?",
    "지금까지의 투자 유치 이력(라운드, 금액, 기업가치)은 어떻게 되나요?",
    "향후 자금 조달 계획과 목표 기업 가치는 어떻게 되나요?",
    "투자금의 주요 사용 계획은 무엇인가요?"
]

# 결과를 저장할 딕셔너리
extracted_info = {}

print("\n=== 각 필드에 대한 정보 추출 시작 ===")

# 각 질문에 대해 RAG 수행
for i, query in enumerate(queries):
    print(f"\n({i+1}/{len(queries)}) 질문: {query}")

    # 1. 검색 (Retrieve)
    query_embedding = model.encode([query])
    similarities_to_query = model.similarity(query_embedding, embeddings)[0]

    k = 3 # 관련성 높은 상위 3개 청크 사용
    if len(sentences) < k:
        k = len(sentences)
    top_k_indices = torch.topk(similarities_to_query, k=k).indices

    retrieved_chunks = [sentences[index.item()] for index in top_k_indices]
    context = "\n\n---\n\n".join(retrieved_chunks)

    # 2. 생성 (Generate) - 1차 시도
    answer = generate_answer(llm, context, query)
    print(f"1차 답변: {answer}")

    # "정보 없음"일 경우, 질문을 단순화하여 재시도
    if answer.strip() == "정보 없음":
        print("-> 1차 시도에서 정보를 찾지 못했습니다. 질문을 단순화하여 재시도합니다.")
        
        # Step A: LLM을 사용하여 질문 단순화
        simplification_prompt = f"""당신은 복잡한 질문을 검색에 용이한 핵심 키워드로 변환하는 AI입니다.

# 지시사항
- 주어진 '질문'의 핵심 의미를 담은 1~3개의 명사형 키워드를 추출해주세요.
- 이 키워드는 문서 내에서 관련 정보를 찾기 위한 검색어로 사용됩니다.
- 예를 들어, "우리 회사의 핵심 기술과 경쟁사 대비 강점은 무엇인가요?" 라는 질문은 "핵심 기술" 또는 "경쟁 우위"로 변환할 수 있습니다.
- "향후 3년간의 사업 확장 계획과 주요 마일스톤에 대해 설명해주세요." 라는 질문은 "사업 계획" 또는 "로드맵"으로 변환할 수 있습니다.
- 추가 설명 없이 키워드만 응답해주세요.

# 질문
```{query}```

# 핵심 키워드:
/no_think"""

        try:
            simplified_query_response = llm.invoke(simplification_prompt)
            raw_simplified_query = simplified_query_response.content

            # <think> 태그가 있는 경우, 해당 블록을 제거하고 순수 키워드만 추출
            if "</think>" in raw_simplified_query:
                simplified_query = raw_simplified_query.split("</think>")[-1].strip()
            else:
                simplified_query = raw_simplified_query.strip()
            
            simplified_query = simplified_query.replace('`', '')
            
            if not simplified_query: # 빈 문자열이 반환될 경우
                raise ValueError("LLM이 빈 단순화 쿼리를 반환했습니다.")
            print(f"-> 단순화된 키워드: {simplified_query}")

            # Step C: 새로운 context로 다시 생성(Generate) - 2차 시도
            answer = generate_answer(llm, context, query)
            print(f"2차 답변: {answer}")

        except Exception as e:
            print(f"-> 재시도 중 오류 발생: {e}")
            # 재시도 실패 시 기존 답변("정보 없음")을 그대로 사용
    
    extracted_info[query] = answer

print("\n\n=== 최종 추출 결과 ===")

# 결과를 원본 파일 이름에 기반하여 JSON 파일로 저장
base_name = os.path.basename(file_path)
file_name_without_ext = os.path.splitext(base_name)[0]
output_file = f"{file_name_without_ext}_extracted_info.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(extracted_info, f, indent=2, ensure_ascii=False)

print(f"\n추출된 정보가 '{output_file}'에 저장되었습니다.")