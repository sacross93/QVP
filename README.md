# QVP: AI-Powered Investment Research Pipeline

An LLM-powered multi-agent pipeline that provides insightful IR analysis and investment opinions based on corporate disclosures and financial data.

## Overview

QVP (Quantitative & Qualitative Venture-Capital Partner)는 비정형 데이터(기업 IR 문서)로부터 정형 정보를 추출하고, 이를 바탕으로 SWOT 분석을 수행한 뒤, 웹 검색을 통해 분석 내용을 검증하고 심화시키는 3단계 AI 분석 파이프라인입니다. 각 단계는 독립적인 스크립트로 구성되어 있으며, 이전 단계의 결과물을 다음 단계의 입력으로 사용하여 깊이 있는 분석을 자동화합니다.

## Core Features

- **Iterative Data Extraction (`IR_Analysis.py`)**: LangGraph를 활용하여 IR 문서에서 정보를 반복적으로 추출하고, 추출 실패 시 스스로 원인을 분석하여 다음 추출을 개선하는 지능형 에이전트입니다.
- **Structured SWOT Analysis (`SWOT.py`)**: 추출된 정형 데이터를 바탕으로, 각 항목(S, W, O, T)에 특화된 LLM 에이전트가 내부/외부 요인을 구분하여 구조화된 SWOT 분석 결과를 생성합니다.
- **Web-Verified Deep Research (`deep_research.py`)**: 생성된 SWOT 분석을 기반으로, ReAct 에이전트가 웹 검색 도구를 사용하여 각 주장을 검증하고, 최신 데이터와 소스 링크를 포함한 최종 심층 분석 보고서를 생성합니다.
- **Source-Cited Reporting**: Deep Research 에이전트는 분석의 모든 근거가 되는 데이터의 출처(URL)를 명시하여 보고서의 신뢰도를 높입니다.
- **Bilingual Output**: 최종 보고서는 LLM의 안정성을 위해 영어로 먼저 생성된 후, 자연스러운 한국어로 번역되어 함께 제공됩니다.

## Architecture & Workflow

프로젝트는 다음과 같은 3단계 파이프라인으로 동작합니다.

### Step 1: `IR_Analysis.py` - Initial Data Extraction

- **Input**: 기업의 IR 정보가 담긴 Markdown 파일 (예: `data/company_ir.md`).
- **Process**:
    1. LangGraph 기반의 에이전트가 실행되어, 비정형 텍스트로부터 `StartupInvestmentInfo` Pydantic 모델에 정의된 필드들을 추출합니다.
    2. 정보 추출이 더 이상 진행되지 않으면, 에이전트는 자체적으로 실패 원인을 분석하여 다음 추출 시도에 활용할 전략을 수립합니다.
    3. 모든 필드 추출 및 검증이 완료되면, 최종 결과를 정형 데이터인 JSON 파일로 저장합니다.
- **Output**: `result/robos_gt.json` (또는 유사한 이름의 구조화된 기업 정보 파일).

### Step 2: `SWOT.py` - Structured SWOT Analysis

- **Input**: Step 1에서 생성된 기업 정보 JSON 파일 (`result/robos_gt.json`).
- **Process**:
    1. 강점(S), 약점(W), 기회(O), 위협(T) 분석을 위한 4개의 독립적인 LLM 체인이 실행됩니다.
    2. 각 체인은 프롬프트에 명시된 원칙(내부/외부 요인 구분, 데이터 단위 해석 등)에 따라 입력된 데이터를 분석합니다.
    3. 각 항목에 대한 분석 근거(reason)와 핵심 내용(contexts)을 구조화된 형태로 생성합니다.
- **Output**: `result/swot_analysis.json` (구조화된 SWOT 분석 결과).

### Step 3: `deep_research.py` - AI-Powered Deep Dive

- **Input**: Step 2에서 생성된 SWOT 분석 JSON 파일 (`result/swot_analysis.json`).
- **Process**:
    1. DuckDuckGo 웹 검색 기능이 탑재된 ReAct 에이전트가 실행됩니다.
    2. 에이전트는 입력된 SWOT 분석의 각 항목을 검증하기 위한 리서치 계획을 스스로 수립합니다.
    3. 계획에 따라 웹 검색을 수행하여 주장들을 뒷받침할 최신 데이터와 기사를 찾습니다.
    4. 초기 분석 내용과 웹 검색 결과를 종합하여, 구체적인 데이터와 출처(URL)가 포함된 심층 분석 보고서를 영어로 작성합니다.
    5. 생성된 영문 보고서를 다시 LLM을 통해 한국어로 번역합니다.
- **Output**: 콘솔에 출력되는 영문 및 국문 최종 보고서.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd QVP
    ```

2.  **Install dependencies:**
    (It is recommended to use a virtual environment)
    ```bash
    uv pip install langchain ollama langchain-community duckduckgo-search pydantic langgraph
    ```

3.  **Run Local LLM:**
    이 프로젝트는 로컬에서 실행되는 Ollama 서버를 사용합니다. 코드에 설정된 모델(`qwen3:32b`)이 로컬 서버에 설치 및 실행 중인지 확인해야 합니다.
    - **Model**: `qwen3:32b`
    - **Base URL**: `http://192.168.120.102:11434` (필요시 `SWOT.py`, `deep_research.py` 에서 수정)

## Usage

파이프라인을 순서대로 실행합니다.

1.  **(Optional) Run IR Analysis:**
    IR Markdown 파일로부터 초기 데이터를 추출하려면 `IR_Analysis.py`를 실행합니다. (현재 `SWOT.py`는 `result/robos_gt.json`을 직접 사용하도록 되어 있습니다.)
    ```bash
    uv run IR_Analysis.py
    ```

2.  **Run SWOT Analysis:**
    `result/robos_gt.json` 파일을 기반으로 SWOT 분석을 수행하고 `result/swot_analysis.json` 파일을 생성합니다.
    ```bash
    uv run SWOT.py
    ```

3.  **Run Deep Research:**
    생성된 SWOT 분석 파일을 기반으로 웹 검색을 포함한 심층 분석을 수행하고 최종 보고서를 확인합니다.
    ```bash
    uv run deep_research.py
    ```
