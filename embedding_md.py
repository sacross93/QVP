from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
import torch

# GPU 장치 설정
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Download from the 🤗 Hub
model = SentenceTransformer("dragonkue/bge-m3-ko", device=device)

with open("./data/로보스.md", "r", encoding="utf-8") as f:
    md_file_content = f.read()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=400,
    separators=["\\n\\n", "\\n", " ", ""] # 마크다운 등을 고려한 구분자
)
sentences = text_splitter.split_text(md_file_content)

llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

# Run inference
embeddings = model.encode(sentences)
print(f"Number of chunks: {len(sentences)}")
print(embeddings.shape)

# RAG 테스트
query = "CEO 이름 알려줘"
query_embedding = model.encode([query]) # 2D 배열로 유지

# 질문 임베딩과 문서 청크 임베딩 간의 유사도 계산
similarities_to_query = model.similarity(query_embedding, embeddings)[0]

# 가장 유사도가 높은 상위 K개 청크 인덱스 찾기
k = 3
if len(sentences) < k:
    k = len(sentences)
top_k_indices = torch.topk(similarities_to_query, k=k).indices

print(f"\n질문: {query}")
print(f"\n검색된 상위 {k}개 청크:")
retrieved_chunks = []
for i, index in enumerate(top_k_indices):
    chunk_index = index.item()
    chunk_text = sentences[chunk_index]
    retrieved_chunks.append(chunk_text)
    print(f"--- 청크 {chunk_index} (유사도: {similarities_to_query[index]:.4f}) ---")
    print(chunk_text)
    print("-" * (20 + len(str(chunk_index))))

# LLM에 전달할 프롬프트 구성
context = "\n\n---\n\n".join(retrieved_chunks)
prompt = f"""당신은 대화형 AI로서, 사용자의 질문에 신뢰할 수 있는 정보를 제공하는 것이 주요 역할입니다. 
사용자의 요구를 정확히 이해하고, 관련 문서를 분석하여 최적의 답변을 생성해야 합니다. \n
당신은 다음과 같은 원칙을 준수해야 합니다:\n
    1. 항상 사용자의 요청을 최우선으로 고려하며, 명확하고 이해하기 쉬운 답변을 제공합니다.\n
    2. 제공된 문서를 최대한 활용하여 응답을 구성하되, 추가적인 분석과 논리를 통해 응답의 질을 높입니다.\n
    3. 응답을 생성할 때는 반드시 주어진 지침을 따르고, 명확한 출처를 제공해야 합니다.\n
    4. 사용자의 질문이 모호할 경우, 명확성을 확보하기 위해 질문을 재구성하는 방안을 고려할 수 있습니다.\n\n
    
# 사용자 안내문\n
    ## 작업 및 맥락\n
        당신은 사용자 질문에 대해 관련 문서를 분석하고, 신뢰할 수 있는 정보를 바탕으로 응답을 생성해야 합니다.
        단순한 정보 전달을 넘어, 문맥을 고려하여 가장 적절한 형태로 정보를 제공하는 것이 중요합니다.

문서:
```
{context}
```

질문: ```{query}```

답변:"""


# LLM 호출
print("\nOllama 모델을 호출하여 답변을 생성합니다...")
response = llm.invoke(prompt)

print("\nLLM 답변:")
print(response.content)
