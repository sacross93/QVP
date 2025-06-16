import json
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import Tool, create_react_agent, AgentExecutor
from langchain_core.output_parsers import StrOutputParser
import re
from glob import glob
import os

# 1. LLM 및 검색 도구 설정
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.120.102:11434",
    temperature=0
)

search = DuckDuckGoSearchResults()
tools = [
    Tool(
        name="web_search",
        func=search.run,
        description="A wrapper around DuckDuckGo Search. Useful for when you need to answer questions about current events. Input should be a search query. Output is a JSON string of a list of dictionaries with 'title', 'snippet', and 'link' keys.",
    )
]

# 2. Deep Research를 위한 에이전트 프롬프트 정의
# ReAct 에이전트의 표준 프롬프트 형식에 맞춰 수정
prompt_template = """
You are an expert business analyst and researcher. Your mission is to perform 'Deep Research' on the initial SWOT analysis provided. You must use web searches to verify and deepen the insights for each category.

**Workflow:**
1.  **Formulate a Research Plan:** First, review the entire SWOT analysis. Then, formulate a concise research plan with 2-4 high-impact search queries to verify the most critical claims. **To avoid being rate-limited, be efficient: combine related topics into a single query where possible.**
2.  **Execute & Synthesize:** Use the 'web_search' tool to execute your planned queries. The tool will return a list of search results with titles, snippets, and links. Extract the most relevant information and the corresponding link to use as a source.
3.  **Write Final Report:** Once your research is complete, write a comprehensive report in the 'Final Answer'. Your report must be analytical. For each point you make, you must cite the specific data or finding from your research and include the source URL. For example: "The initial analysis noted a market growth opportunity. This is supported by a report from [Source Name], which states the market will grow by 15% annually (Source: [link from search result])."

**Available Tools:**
{tools}

**Begin Analysis!**

**Initial SWOT Analysis:**
{input}

{agent_scratchpad}

---
**CRITICAL: You must strictly follow the response format below. Do not add any other text outside this format.**

Thought: I need to analyze the current situation and decide what to do next, concisely.
Action: The tool to use, which must be one of [{tool_names}].
Action Input: The input query for the tool.
Observation: The result of the tool.
... (this Thought/Action/Action Input/Observation cycle can repeat N times)
Thought: I have now gathered enough information and can formulate the final answer.
Final Answer: [The final, comprehensive deep research report. **For each point, you must cite specific data and the source URL from your web search.**]
"""

prompt = PromptTemplate.from_template(prompt_template)


# 3. 에이전트 및 실행기 생성
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # 에이전트의 생각 과정을 볼 수 있도록 설정
    handle_parsing_errors=True
)

# 4. 메인 실행 로직
if __name__ == "__main__":
    swot_files = glob('./result/swot_analysis_*.json')
    
    for output in swot_files:
        try:
            with open(output, 'r', encoding='utf-8') as f:
                swot_data = json.load(f)
        except FileNotFoundError:
            print("오류: 'result/swot_analysis.json' 파일을 찾을 수 없습니다.")
            print("먼저 'python SWOT.py'를 실행하여 분석 파일을 생성해주세요.")
            exit()

        swot_input_string = json.dumps(swot_data, ensure_ascii=False, indent=2)

        print("=" * 30)
        print("🤖 Deep Research 에이전트를 시작합니다...")
        print("=" * 30)
        
        result = agent_executor.invoke({
            "input": swot_input_string,
        })

        print("\n" + "=" * 30)
        print("✅ Deep Research 최종 보고서 (영문)")
        print("=" * 30)
        print(result['output']) 

        korean_report = "" # 번역본을 저장할 변수 초기화
        # 5. 최종 보고서를 한국어로 번역
        if result['output']:
            print("\n" + "=" * 30)
            print("🇰🇷 최종 보고서 (한국어 번역)")
            print("=" * 30)
            
            translation_prompt = PromptTemplate.from_template(
                "Translate the following English text to Korean. Maintain the original structure and formatting, including markdown like headers and bullet points:\n\n{english_text}"
            )
            
            translation_chain = translation_prompt | llm | StrOutputParser()

            korean_report = translation_chain.invoke({"english_text": result['output']})
            
            # <think>...</think> 태그와 그 내용을 정규식을 사용하여 제거
            think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
            korean_report = think_pattern.sub("", korean_report).strip()

            print(korean_report)
        else:
            print("\n번역할 내용이 없습니다.")

        # 6. 최종 보고서를 JSON 파일로 저장
        if result['output']:
            report_data = {
                "english_report": result['output'],
                "korean_report": korean_report
            }
            
            base_name = os.path.basename(output)
            identifier = base_name.replace('swot_analysis_', '').replace('.json', '')
            output_path = f'result/deep_research_report_{identifier}.json'

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=4)
            
            print(f"\n✅ 최종 보고서가 {output_path} 에 성공적으로 저장되었습니다.") 