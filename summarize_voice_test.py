
import asyncio
import re
from typing import List, Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

# 1. Instantiate LLM
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0,
)

# 2. Load Documents
try:
    with open("/home/wlsdud022/QVP/voice_txt/voice_test.txt", "r", encoding="utf-8") as f:
        text_content = f.read()
    # Split the text into smaller documents by chunking lines.
    lines = [line for line in text_content.splitlines() if line.strip()]
    chunk_size = 10
    documents = [
        Document(page_content="\n".join(lines[i : i + chunk_size]))
        for i in range(0, len(lines), chunk_size)
    ]
except FileNotFoundError:
    print("Error: voice_txt/voice_test.txt not found.")
    exit()


# 3. Create Chains
# Initial summary chain
summarize_prompt = ChatPromptTemplate.from_template(
    "다음 내용을 간결하게 요약해 주세요: {context}"
)
initial_summary_chain = summarize_prompt | llm | StrOutputParser()

# Refining the summary with new docs
refine_template = """
기존 요약 내용을 새로운 내용을 바탕으로 개선해주세요.

기존 요약:
{existing_answer}

새로운 내용:
------------
{context}
------------

새로운 내용을 바탕으로 기존 요약을 개선해주세요. /no_think
"""
refine_prompt = ChatPromptTemplate.from_template(refine_template)
refine_summary_chain = refine_prompt | llm | StrOutputParser()


# 4. Define Graph State
class State(TypedDict):
    contents: List[str]
    index: int
    summary: str


# 5. Define Graph Nodes
def clean_summary(summary: str) -> str:
    """Removes <think> blocks from the summary."""
    return re.sub(r"<think>.*?</think>", "", summary, flags=re.DOTALL).strip()


async def generate_initial_summary(state: State, config: RunnableConfig):
    """Generates the initial summary."""
    summary = await initial_summary_chain.ainvoke(
        {"context": state["contents"][0]},
        config,
    )
    cleaned_summary = clean_summary(summary)
    return {"summary": cleaned_summary, "index": 1}


async def refine_summary(state: State, config: RunnableConfig):
    """Refines the existing summary with new content."""
    content = state["contents"][state["index"]]
    summary = await refine_summary_chain.ainvoke(
        {"existing_answer": state["summary"], "context": content},
        config,
    )
    cleaned_summary = clean_summary(summary)
    return {"summary": cleaned_summary, "index": state["index"] + 1}


# 6. Define Conditional Edge
def should_refine(state: State) -> Literal["refine_summary", "__end__"]:
    """Determines whether to continue refining or to end."""
    if state["index"] >= len(state["contents"]):
        return "__end__"
    else:
        return "refine_summary"


# 7. Build Graph
graph = StateGraph(State)
graph.add_node("generate_initial_summary", generate_initial_summary)
graph.add_node("refine_summary", refine_summary)

graph.add_edge(START, "generate_initial_summary")
graph.add_conditional_edges(
    "generate_initial_summary",
    should_refine,
    {
        "refine_summary": "refine_summary",
        "__end__": "__end__"
    }
)
graph.add_conditional_edges(
    "refine_summary",
    should_refine,
    {
        "refine_summary": "refine_summary",
        "__end__": "__end__"
    }
)


app = graph.compile()


# 8. Execute and Stream
async def main():
    """Main function to run the summarization graph."""
    print("--- Iterative Refinement Summarization ---")
    final_summary = ""
    async for step in app.astream(
        {"contents": [doc.page_content for doc in documents]},
        stream_mode="values",
    ):
        if summary := step.get("summary"):
            final_summary = summary
            print(f"--- 중간 요약 (단계 {step.get('index', 0)}) ---")
            print(summary)
            print("\n")

    print("--- Final Summary ---")
    print(final_summary)


if __name__ == "__main__":
    asyncio.run(main())
