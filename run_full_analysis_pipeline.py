import os
import subprocess
import argparse
import sys
from glob import glob

# ==============================================================================
# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 설정 부분 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
#
# 분석하고 싶은 SWOT 분석 파일의 경로를 여기에 입력하세요.
# 예시: 'result/델타엑스_swot_analysis_20250611_155431.json'
#
INPUT_SWOT_FILE = 'result/ROBOS_swot_analysis_20250611_163629.json'
#
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 설정 부분 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
# ==============================================================================

def find_latest_file(pattern):
    """주어진 패턴에 맞는 파일 중 가장 최신 파일을 찾습니다."""
    files = glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def run_script(script_name, arguments):
    """주어진 인자와 함께 파이썬 스크립트를 실행하고, 출력을 실시간으로 보여줍니다."""
    command = [sys.executable, script_name] + arguments
    print(f"\n{'='*20} RUNNING: {' '.join(command)} {'='*20}\n")
    try:
        # capture_output=True를 제거하여 하위 프로세스의 출력이 실시간으로 터미널에 표시되도록 함
        subprocess.run(command, check=True, text=True)
    except subprocess.CalledProcessError as e:
        # 에러가 발생하면 check=True에 의해 예외가 발생하므로, 별도 에러 메시지 출력
        print(f"\n🚨🚨🚨 ERROR: {script_name} failed to execute with return code {e.returncode}. 🚨🚨🚨")
        return False
    except FileNotFoundError:
        print(f"🚨🚨🚨 ERROR: Script '{script_name}' not found. Make sure it's in the same directory. 🚨🚨🚨")
        return False
    except Exception as e:
        print(f"🚨🚨🚨 ERROR: Unexpected error running {script_name}: {e} 🚨🚨🚨")
        return False
    return True

def get_identifier_from_swot(swot_file_path):
    """SWOT 파일 경로에서 고유 식별자를 추출합니다."""
    base_name = os.path.basename(swot_file_path)
    # 예: '델타엑스_swot_analysis_20250611_155431.json' -> '델타엑스_20250611_155431'
    identifier = base_name.replace('_swot_analysis', '').replace('.json', '')
    return identifier

def main(swot_file_path):
    """
    전체 분석 파이프라인을 실행합니다.
    1. Advanced Deep Research
    2. Competitive Analysis
    3. Lean Canvas Extraction
    4. Strategic Report Generation
    """
    
    # bm_result 디렉토리 생성
    os.makedirs('bm_result', exist_ok=True)
    
    # 입력된 SWOT 파일이 실제로 존재하는지 확인
    if not os.path.exists(swot_file_path):
        print(f"🚨 ERROR: Input SWOT file not found at '{swot_file_path}'")
        print(f"�� TIP: Make sure the SWOT analysis file exists in the result directory")
        print(f"       Analysis results will be saved to the bm_result directory")
        return False

    print(f"🚀 Starting full analysis pipeline for: {swot_file_path}")
    
    # SWOT 파일에서 식별자 추출
    try:
        identifier = get_identifier_from_swot(swot_file_path)
        print(f"📝 Extracted identifier: {identifier}")
    except Exception as e:
        print(f"🚨 ERROR: Failed to extract identifier from {swot_file_path}: {e}")
        return False

    # --- 단계 1: Advanced Deep Research 실행 ---
    print("\n--- STAGE 1: Advanced Deep Research ---")
    if not run_script('advanced_deep_research.py', [swot_file_path]):
        print("🚨 Stage 1 failed. Stopping pipeline.")
        return False
    
    # 1단계의 결과물 경로를 구성합니다.
    adv_report_path = f'bm_result/advanced_deep_research_report_{identifier}.json'
    if not os.path.exists(adv_report_path):
        print(f"🚨 ERROR: Stage 1 did not produce the expected output file: {adv_report_path}")
        return False
    print(f"✅ Stage 1 completed. Output: {adv_report_path}")

    # --- 단계 2: Competitive Analysis 실행 ---
    print("\n--- STAGE 2: Competitive Analysis ---")
    if not run_script('competitive_analysis.py', [adv_report_path]):
        print("🚨 Stage 2 failed. Stopping pipeline.")
        return False

    # 2단계의 결과물 경로를 구성합니다.
    comp_report_path = f'bm_result/competitive_analysis_report_{identifier}.json'
    if not os.path.exists(comp_report_path):
        print(f"🚨 ERROR: Stage 2 did not produce the expected output file: {comp_report_path}")
        return False
    print(f"✅ Stage 2 completed. Output: {comp_report_path}")

    # --- 단계 3: Lean Canvas Extraction 실행 ---
    print("\n--- STAGE 3: Lean Canvas Extraction ---")
    if not run_script('extract_lean_canvas.py', [comp_report_path]):
        print("🚨 Stage 3 failed. Stopping pipeline.")
        return False
    
    lean_canvas_path = f'bm_result/lean_canvas_{identifier}.json'
    if not os.path.exists(lean_canvas_path):
        print(f"🚨 ERROR: Stage 3 did not produce the expected output file: {lean_canvas_path}")
        return False
    print(f"✅ Stage 3 completed. Output: {lean_canvas_path}")

    # --- 단계 4: Strategic Report Generation ---
    print("\n--- STAGE 4: Strategic Report Generation ---")
    # 4단계 스크립트는 파일 경로 대신 identifier를 인자로 받습니다.
    if not run_script('generate_strategic_report.py', [identifier]):
        print("🚨 Stage 4 failed. Stopping pipeline.")
        return False
    
    # 4단계의 결과물 경로를 구성합니다.
    strategic_report_path = f'bm_result/strategic_report_{identifier}.json'
    if not os.path.exists(strategic_report_path):
        print(f"🚨 ERROR: Stage 4 did not produce the expected output file: {strategic_report_path}")
        return False
    print(f"✅ Stage 4 completed. Output: {strategic_report_path}")

    print("\n\n🎉🎉🎉 Full analysis pipeline completed successfully! 🎉🎉🎉")
    print(f"📁 All outputs are located in the bm_result/ directory:")
    print(f"   - Initial research: {adv_report_path}")
    print(f"   - Competitive analysis: {comp_report_path}")
    print(f"   - Lean Canvas: {lean_canvas_path}")
    print(f"   - Final strategic report: {strategic_report_path}")
    return True

if __name__ == "__main__":
    if not INPUT_SWOT_FILE or INPUT_SWOT_FILE == ' 여기에 경로 입력 ':
        print("🚨 Please set the 'INPUT_SWOT_FILE' variable at the top of the script before running.")
        sys.exit(1)
    else:
        try:
            success = main(INPUT_SWOT_FILE)
            if not success:
                print("\n🚨 Pipeline execution failed. Please check the error messages above.")
                sys.exit(1)
        except Exception as e:
            print(f"\n🚨 ERROR: An unexpected error occurred: {e}")
            sys.exit(1) 