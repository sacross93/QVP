import json
import sys
import os
from glob import glob

def print_report(file_path):
    """
    딥 리서치 보고서 JSON 파일을 읽어 터미널에 보기 좋게 출력하고,
    사용자 요청 시 한글 보고서를 .md 파일로 저장합니다.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"오류: 파일 '{file_path}'를 찾을 수 없습니다.")
        return
    except json.JSONDecodeError:
        print(f"오류: '{file_path}' 파일이 올바른 JSON 형식이 아닙니다.")
        return

    # 파일명에서 회사 이름 추출
    company_name = os.path.basename(file_path).replace('deep_research_report_', '').replace('.json', '').replace('_extracted_info', '')

    print("\n" + "=" * 80)
    print(f"📄 Deep Research 분석 보고서: {company_name}")
    print("=" * 80)

    if 'english_report' in data and data['english_report']:
        print("\n" + "--- 🇬🇧 English Report ---")
        print(data['english_report'])
    
    if 'korean_report' in data and data['korean_report']:
        print("\n" + "--- 🇰🇷 Korean Report (번역) ---")
        print(data['korean_report'])

    print("\n" + "=" * 80)

    # 보고서 출력 후, 한글 보고서가 있으면 저장 여부를 물어봄
    if 'korean_report' in data and data['korean_report']:
        try:
            save_choice = input("\n이 한글 보고서를 마크다운(.md) 파일로 저장하시겠습니까? (y/n): ").lower()
            if save_choice in ['y', 'yes', 'ㅛ']:
                # 저장할 파일 경로 생성 (예: .../report.json -> .../report.md)
                md_path = os.path.splitext(file_path)[0] + '.md'
                
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(data['korean_report'])
                print(f"\n✅ 보고서가 성공적으로 저장되었습니다: {md_path}")

        except KeyboardInterrupt:
            print("\n저장을 취소했습니다.")
        except Exception as e:
            print(f"\n❌ 파일 저장 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    # 터미널에서 파일 경로를 인자로 받았을 경우
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"오류: 지정된 경로에 파일이 없습니다: {file_path}")
        elif not file_path.endswith('.json'):
             print(f"오류: JSON 파일만 지원됩니다: {file_path}")
        else:
            print_report(file_path)
    else:
        # 인자가 없을 경우, result 폴더에서 보고서를 찾아 목록을 보여줌
        report_files = glob('./result/deep_research_report_*.json')
        if not report_files:
            print("사용 가능한 보고서 파일이 'result/' 폴더에 없습니다.")
        else:
            print("다음은 사용 가능한 분석 보고서 목록입니다:")
            for i, file in enumerate(report_files):
                company_name = os.path.basename(file).replace('deep_research_report_', '').replace('.json', '').replace('_extracted_info', '')
                print(f"  [{i + 1}] {company_name}")
            
            try:
                choice = input("\n내용을 확인하고 싶은 보고서의 번호를 입력하세요 (나가려면 q): ")
                if choice.lower() == 'q':
                    print("프로그램을 종료합니다.")
                else:
                    choice_num = int(choice) - 1
                    if 0 <= choice_num < len(report_files):
                        print_report(report_files[choice_num])
                    else:
                        print("잘못된 번호입니다.")
            except ValueError:
                print("숫자를 입력해주세요.")
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.") 