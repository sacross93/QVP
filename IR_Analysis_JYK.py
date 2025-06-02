from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict
from datetime import date
from langchain_ollama import OllamaLLM, ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import glob
import os
import json
import re

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

# 2. LLM 준비
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.110.102:11434",
    temperature=0.1,
)

def classification_fileds(md_content: str) -> dict:
    parser = JsonOutputParser(pydantic_object=StartupInvestmentInfo)
    
    prompt = PromptTemplate(
    template="""당신은 스타트업의 기업소개 및 IR(Investor Relations) 자료에서 filed 값들을 찾아 잘 분류해주는 전문가입니다.\n
    ```
    {format_instructions}
    ```
    \n
    ```
    {document}
    ```
    resonse in JSON format. /no_think
    """,
    input_variables=["document"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    chain = prompt | llm | parser
    
    result = chain.invoke({"document": md_content})
    
    return result

with open("./data/로보스.md", "r", encoding="utf-8") as f:
    content = f.read()
    
test = classification_fileds(content)

print(test)