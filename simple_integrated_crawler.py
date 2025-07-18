#!/usr/bin/env python3
"""
심플 통합 크롤러
Innoforest + TheVC 크롤러를 순차 실행하고 결과 통합

사용법:
1. 회사명 입력
2. Innoforest 크롤러 실행
3. TheVC 크롤러 실행
4. 두 결과 통합하여 JSON 저장
"""

import asyncio
import json
import logging
import os
import psutil
import signal
from datetime import datetime
from pathlib import Path

# 기존 크롤러 임포트
from innoforest_stealth import InnoforestStealthCrawler
from main_stealth import TheVCStealthCrawler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_integrated_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 추가: 환경 감지 함수
def should_run_headless():
    """실행 환경에 따라 headless 모드 결정"""
    # SSH 접속 환경 감지
    if os.environ.get('SSH_CLIENT') or os.environ.get('SSH_TTY'):
        return True
    
    # DISPLAY 환경변수 확인
    if not os.environ.get('DISPLAY'):
        return True
    
    # CI/CD 환경 감지
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
        return True
    
    return False

class SimpleIntegratedCrawler:
    """
    간단한 통합 크롤러 클래스
    """
    
    def __init__(self):
        self.company_name = None
        self.innoforest_data = None
        self.thevc_data = None
        self.integrated_data = None
        
    def get_company_name_from_user(self):
        """
        사용자로부터 회사명 입력받기
        """
        try:
            print("\n" + "="*60)
            print("🚀 심플 통합 크롤러 - Innoforest + TheVC")
            print("="*60)
            print("검색할 스타트업/기업명을 입력해주세요.")
            print("예시: 로보스, 십일리터, 토스, 카카오, 퓨리오사 등")
            print("-"*60)
            
            while True:
                keyword = input("🏢 검색할 회사명: ").strip()
                
                if not keyword:
                    print("❌ 회사명을 입력해주세요!")
                    continue
                
                if len(keyword) > 60:
                    print("❌ 회사명은 60자 이하로 입력해주세요!")
                    continue
                
                # 확인
                print(f"\n📝 입력된 회사명: '{keyword}'")
                confirm = input("이 회사명으로 검색하시겠습니까? (y/n): ").strip().lower()
                
                if confirm in ['y', 'yes', '예', 'ㅇ']:
                    self.company_name = keyword
                    return keyword
                elif confirm in ['n', 'no', '아니오', 'ㄴ']:
                    continue
                else:
                    print("y 또는 n을 입력해주세요.")
                    continue
                    
        except KeyboardInterrupt:
            print("\n❌ 사용자에 의해 취소되었습니다.")
            return None
    
    async def run_innoforest_crawler(self):
        """
        Innoforest 크롤러 실행
        """
        try:
            logger.info(f"🌲 Innoforest 크롤러 시작: '{self.company_name}'")
            
            # Innoforest 크롤러 생성
            innoforest_crawler = InnoforestStealthCrawler()
            
            # 환경에 맞는 헤드리스 모드 결정
            headless_mode = should_run_headless()
            logger.info(f"🖥️ Headless 모드: {headless_mode}")
            
            # 브라우저 초기화
            if not await innoforest_crawler.initialize(headless=headless_mode):
                # 실패 시 headless 모드로 재시도
                if not headless_mode:
                    logger.warning("⚠️ GUI 모드 실패, Headless 모드로 재시도...")
                    if not await innoforest_crawler.initialize(headless=True):
                        logger.error("❌ Innoforest 브라우저 초기화 실패")
                        return False
                else:
                    logger.error("❌ Innoforest 브라우저 초기화 실패")
                    return False
            
            # 사이트 접속
            if not await innoforest_crawler.navigate_to_innoforest():
                logger.error("❌ Innoforest 사이트 접속 실패")
                await innoforest_crawler.close()
                return False
            
            # 로그인 확인 및 수행
            is_logged_in = await innoforest_crawler.check_if_logged_in()
            if not is_logged_in:
                logger.info("🔐 Innoforest 로그인 시도 중...")
                login_success = await innoforest_crawler.perform_login()
                if not login_success:
                    logger.error("❌ Innoforest 로그인 실패")
                    await innoforest_crawler.close()
                    return False
            
            # 스타트업 검색
            search_success = await innoforest_crawler.search_startup(self.company_name)
            if not search_success:
                logger.error(f"❌ Innoforest에서 '{self.company_name}' 검색 실패")
                await innoforest_crawler.close()
                return False
            
            # 검색 결과 확인
            results_found = await innoforest_crawler.check_search_results(self.company_name)
            if not results_found:
                logger.warning(f"⚠️ Innoforest에서 '{self.company_name}' 검색 결과 없음")
                await innoforest_crawler.close()
                return False
            
            # 첫 번째 검색 결과 클릭
            click_success = await innoforest_crawler.click_first_search_result(self.company_name)
            if not click_success:
                logger.error(f"❌ Innoforest에서 '{self.company_name}' 첫 번째 결과 클릭 실패")
                await innoforest_crawler.close()
                return False
            
            # 회사 정보 추출
            company_info = await innoforest_crawler.extract_company_info(self.company_name)
            if not company_info:
                logger.error(f"❌ Innoforest에서 '{self.company_name}' 정보 추출 실패")
                await innoforest_crawler.close()
                return False
            
            # 데이터 저장
            await innoforest_crawler.save_company_data_to_json(company_info, self.company_name)
            self.innoforest_data = company_info
            
            # 브라우저 종료
            await innoforest_crawler.close()
            
            logger.info(f"✅ Innoforest 크롤링 완료: '{self.company_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Innoforest 크롤링 중 오류: {e}")
            return False
    
    async def run_thevc_crawler(self):
        """
        TheVC 크롤러 실행
        """
        try:
            logger.info(f"🎯 TheVC 크롤러 시작: '{self.company_name}'")
            
            # TheVC 크롤러 생성
            thevc_crawler = TheVCStealthCrawler()
            
            # 환경에 맞는 헤드리스 모드 결정
            headless_mode = should_run_headless()
            logger.info(f"🖥️ Headless 모드: {headless_mode}")
            
            # 브라우저 초기화
            if not await thevc_crawler.initialize(headless=headless_mode):
                # 실패 시 headless 모드로 재시도
                if not headless_mode:
                    logger.warning("⚠️ GUI 모드 실패, Headless 모드로 재시도...")
                    if not await thevc_crawler.initialize(headless=True):
                        logger.error("❌ TheVC 브라우저 초기화 실패")
                        return False
                else:
                    logger.error("❌ TheVC 브라우저 초기화 실패")
                    return False
            
            # 사이트 접속
            if not await thevc_crawler.navigate_to_thevc():
                logger.error("❌ TheVC 사이트 접속 실패")
                await thevc_crawler.close()
                return False
            
            # 로그인 확인 및 수행
            is_logged_in = await thevc_crawler.check_if_logged_in()
            if not is_logged_in:
                logger.info("🔐 TheVC 로그인 시도 중...")
                
                # 로그인 버튼 클릭
                if not await thevc_crawler.click_login_button():
                    logger.error("❌ TheVC 로그인 버튼 클릭 실패")
                    await thevc_crawler.close()
                    return False
                
                # 로그인 모달 대기
                if not await thevc_crawler.wait_for_login_modal():
                    logger.error("❌ TheVC 로그인 모달 대기 실패")
                    await thevc_crawler.close()
                    return False
                
                # 로그인 수행
                login_success = await thevc_crawler.perform_login()
                if not login_success:
                    logger.error("❌ TheVC 로그인 실패")
                    await thevc_crawler.close()
                    return False
            
            # 스타트업 검색
            search_success = await thevc_crawler.search_startup(self.company_name)
            if not search_success:
                logger.error(f"❌ TheVC에서 '{self.company_name}' 검색 실패")
                await thevc_crawler.close()
                return False
            
            # 검색 결과 확인
            results_found = await thevc_crawler.check_search_results(self.company_name)
            if not results_found:
                logger.warning(f"⚠️ TheVC에서 '{self.company_name}' 검색 결과 없음")
                await thevc_crawler.close()
                return False
            
            # 첫 번째 검색 결과 클릭
            click_success = await thevc_crawler.click_first_search_result()
            if not click_success:
                logger.error(f"❌ TheVC에서 '{self.company_name}' 첫 번째 결과 클릭 실패")
                await thevc_crawler.close()
                return False
            
            # 회사 정보 추출
            company_data = await thevc_crawler.extract_company_data(self.company_name)
            if not company_data:
                logger.error(f"❌ TheVC에서 '{self.company_name}' 정보 추출 실패")
                await thevc_crawler.close()
                return False
            
            # 데이터 저장
            await thevc_crawler.save_company_data_to_json(company_data, self.company_name)
            self.thevc_data = company_data
            
            # 브라우저 종료
            await thevc_crawler.close()
            
            logger.info(f"✅ TheVC 크롤링 완료: '{self.company_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ TheVC 크롤링 중 오류: {e}")
            return False
    
    def integrate_data(self):
        """
        두 데이터 소스 통합
        """
        try:
            logger.info(f"🔄 데이터 통합 시작: '{self.company_name}'")
            
            if not self.innoforest_data and not self.thevc_data:
                logger.error("❌ 통합할 데이터가 없습니다")
                return False
            
            # 통합 데이터 구조 생성
            integrated_data = {
                'company_name': self.company_name,
                'crawling_date': datetime.now().isoformat(),
                'data_sources': {
                    'innoforest': self.innoforest_data is not None,
                    'thevc': self.thevc_data is not None
                },
                'integrated_info': {}
            }
            
            # Innoforest 데이터 추가 (뉴스 제외 - 중복 방지)
            if self.innoforest_data:
                innoforest_copy = self.innoforest_data.copy()
                innoforest_copy.pop('news', None)  # 뉴스 제거
                integrated_data['innoforest_data'] = innoforest_copy
                logger.info("📊 Innoforest 데이터 추가 완료")
            
            # TheVC 데이터 추가 (뉴스 제외 - 중복 방지)
            if self.thevc_data:
                thevc_copy = self.thevc_data.copy()
                thevc_copy.pop('news', None)  # 뉴스 제거
                integrated_data['thevc_data'] = thevc_copy
                logger.info("📊 TheVC 데이터 추가 완료")
            
            # 통합 정보 생성 (중복 제거 및 보완)
            integrated_info = {}
            
            # 회사명 통합
            if self.innoforest_data and self.innoforest_data.get('company_name'):
                integrated_info['company_name'] = self.innoforest_data['company_name']
            elif self.thevc_data and self.thevc_data.get('company_name'):
                integrated_info['company_name'] = self.thevc_data['company_name']
            else:
                integrated_info['company_name'] = self.company_name
            
            # URL 정보 통합
            urls = {}
            if self.innoforest_data and self.innoforest_data.get('url'):
                urls['innoforest'] = self.innoforest_data['url']
            if self.thevc_data and self.thevc_data.get('url'):
                urls['thevc'] = self.thevc_data['url']
            if urls:
                integrated_info['urls'] = urls
            
            # 주요 정보 통합 (Innoforest 기준, TheVC로 보완)
            if self.innoforest_data and self.innoforest_data.get('main_info'):
                integrated_info['main_info'] = self.innoforest_data['main_info']
            
            # TheVC의 업력 정보 추가
            if self.thevc_data and self.thevc_data.get('key_info', {}).get('business_years'):
                integrated_info['business_age'] = self.thevc_data['key_info']['business_years']
            
            # 특허 정보 통합
            patent_info = {}
            if self.innoforest_data and self.innoforest_data.get('patent_info'):
                patent_info['innoforest'] = self.innoforest_data['patent_info']
            if self.thevc_data and self.thevc_data.get('patents'):
                patent_info['thevc'] = self.thevc_data['patents']
            if patent_info:
                integrated_info['patent_info'] = patent_info
            
            # 투자 정보 통합
            investment_info = {}
            if self.innoforest_data and self.innoforest_data.get('investment'):
                investment_info['innoforest'] = self.innoforest_data['investment']
            if self.thevc_data and self.thevc_data.get('investment_info'):
                investment_info['thevc'] = self.thevc_data['investment_info']
            if investment_info:
                integrated_info['investment_info'] = investment_info
            
            # 재무 정보 (주로 Innoforest)
            if self.innoforest_data and self.innoforest_data.get('financial'):
                integrated_info['financial_info'] = self.innoforest_data['financial']
            
            if self.innoforest_data and self.innoforest_data.get('profit_loss'):
                integrated_info['profit_loss_info'] = self.innoforest_data['profit_loss']
            
            # 뉴스 정보 통합
            news_info = {}
            if self.innoforest_data and self.innoforest_data.get('news'):
                news_info['innoforest'] = self.innoforest_data['news']
            if self.thevc_data and self.thevc_data.get('news'):
                news_info['thevc'] = self.thevc_data['news']
            if news_info:
                integrated_info['news_info'] = news_info
            
            integrated_data['integrated_info'] = integrated_info
            self.integrated_data = integrated_data
            
            logger.info(f"✅ 데이터 통합 완료: '{self.company_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ 데이터 통합 중 오류: {e}")
            return False
    
    def save_integrated_data(self):
        """
        통합 데이터를 JSON 파일로 저장
        """
        try:
            if not self.integrated_data:
                logger.error("❌ 저장할 통합 데이터가 없습니다")
                return False
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integrated_data_{self.company_name.replace(' ', '_')}_{timestamp}.json"
            
            # JSON 파일로 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.integrated_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 통합 데이터 저장 완료: {filename}")
            
            # 저장된 데이터 요약 출력
            print("\n" + "="*60)
            print(f"📊 통합 데이터 저장 완료: {filename}")
            print("="*60)
            
            if self.integrated_data.get('data_sources'):
                sources = self.integrated_data['data_sources']
                print(f"🌲 Innoforest 데이터: {'✅' if sources.get('innoforest') else '❌'}")
                print(f"🎯 TheVC 데이터: {'✅' if sources.get('thevc') else '❌'}")
            
            if self.integrated_data.get('integrated_info'):
                info = self.integrated_data['integrated_info']
                print(f"🏢 회사명: {info.get('company_name', 'N/A')}")
                print(f"📅 업력: {info.get('business_age', 'N/A')}")
                print(f"💰 투자정보: {'✅' if info.get('investment_info') else '❌'}")
                print(f"🔬 특허정보: {'✅' if info.get('patent_info') else '❌'}")
                print(f"📰 뉴스정보: {'✅' if info.get('news_info') else '❌'}")
            
            print("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 통합 데이터 저장 실패: {e}")
            return False
    
    async def run(self):
        """
        전체 크롤링 프로세스 실행
        """
        try:
            logger.info("🚀 심플 통합 크롤러 시작")
            
            # 1. 회사명 입력받기
            company_name = self.get_company_name_from_user()
            if not company_name:
                logger.warning("⚠️ 회사명 입력이 취소되었습니다")
                return False
            
            print(f"\n🎯 '{company_name}' 크롤링 시작!")
            print("="*60)
            
            # 2. Innoforest 크롤링
            print("\n🌲 1단계: Innoforest 크롤링 시작...")
            innoforest_success = await self.run_innoforest_crawler()
            if innoforest_success:
                print("✅ Innoforest 크롤링 완료!")
            else:
                print("❌ Innoforest 크롤링 실패!")
            
            # 3. TheVC 크롤링
            print("\n🎯 2단계: TheVC 크롤링 시작...")
            thevc_success = await self.run_thevc_crawler()
            if thevc_success:
                print("✅ TheVC 크롤링 완료!")
            else:
                print("❌ TheVC 크롤링 실패!")
            
            # 4. 데이터 통합
            print("\n🔄 3단계: 데이터 통합 시작...")
            if innoforest_success or thevc_success:
                integration_success = self.integrate_data()
                if integration_success:
                    print("✅ 데이터 통합 완료!")
                    
                    # 5. 통합 데이터 저장
                    print("\n💾 4단계: 통합 데이터 저장 시작...")
                    save_success = self.save_integrated_data()
                    if save_success:
                        print("✅ 통합 데이터 저장 완료!")
                        print(f"\n🎉 '{company_name}' 크롤링 및 통합 완료!")
                        return True
                    else:
                        print("❌ 통합 데이터 저장 실패!")
                        return False
                else:
                    print("❌ 데이터 통합 실패!")
                    return False
            else:
                print("❌ 두 크롤러 모두 실패했습니다!")
                return False
                
        except Exception as e:
            logger.error(f"❌ 크롤링 프로세스 중 오류: {e}")
            return False

async def cleanup_and_wait():
    """
    모든 서브프로세스 정리 및 대기
    """
    try:
        logger.info("🔄 최종 정리 작업 시작...")
        
        # 1. 현재 실행 중인 Playwright 관련 프로세스 확인
        playwright_processes = []
        current_process = psutil.Process()
        
        try:
            for child in current_process.children(recursive=True):
                if any(name in child.name().lower() for name in ['chrome', 'chromium', 'playwright', 'node']):
                    playwright_processes.append(child)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        if playwright_processes:
            logger.info(f"🔄 {len(playwright_processes)}개의 브라우저 관련 프로세스 발견")
            
            # 2. 프로세스들이 자연스럽게 종료되도록 대기
            max_wait_time = 10.0  # 최대 10초 대기
            wait_interval = 0.5
            waited_time = 0.0
            
            while waited_time < max_wait_time:
                still_running = []
                for proc in playwright_processes:
                    try:
                        if proc.is_running():
                            still_running.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass  # 프로세스가 이미 종료됨
                
                if not still_running:
                    logger.info("✅ 모든 브라우저 프로세스가 자연스럽게 종료됨")
                    break
                
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
                
                if waited_time % 2.0 == 0:  # 2초마다 로그
                    logger.info(f"⏳ 브라우저 프로세스 종료 대기 중... ({waited_time:.1f}/{max_wait_time}초)")
            
            # 3. 여전히 실행 중인 프로세스가 있으면 강제 종료
            final_check = []
            for proc in playwright_processes:
                try:
                    if proc.is_running():
                        final_check.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if final_check:
                logger.warning(f"⚠️ {len(final_check)}개의 프로세스가 여전히 실행 중 - 강제 종료")
                for proc in final_check:
                    try:
                        proc.terminate()
                        await asyncio.sleep(0.5)
                        if proc.is_running():
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        
        # 4. 이벤트 루프의 모든 미완료 태스크 강제 취소 및 정리
        logger.info("🔄 미완료 태스크 정리 중...")
        
        # 현재 실행 중인 태스크들 확인
        current_task = asyncio.current_task()
        all_tasks = [task for task in asyncio.all_tasks() if task != current_task]
        
        if all_tasks:
            logger.info(f"⏳ {len(all_tasks)}개의 미완료 태스크 취소 중...")
            
            # 모든 태스크 즉시 취소
            for task in all_tasks:
                if not task.done():
                    task.cancel()
            
            # 취소된 태스크들이 완전히 정리되도록 대기
            try:
                await asyncio.wait_for(
                    asyncio.gather(*all_tasks, return_exceptions=True),
                    timeout=3.0
                )
                logger.info("✅ 모든 태스크 정리 완료")
            except asyncio.TimeoutError:
                logger.warning("⚠️ 일부 태스크 정리 타임아웃")
            except Exception as e:
                logger.warning(f"⚠️ 태스크 정리 중 예외 (무시됨): {e}")
        
        # 5. 남은 Future 객체들 정리
        logger.info("🔄 Future 객체 정리 중...")
        
        # 모든 Future 객체 취소 시도
        try:
            import gc
            gc.collect()  # 가비지 컬렉션 강제 실행
            
            # 추가 대기로 Future 객체들이 정리되도록 함
            await asyncio.sleep(1.0)
            logger.info("✅ Future 객체 정리 완료")
        except Exception as e:
            logger.warning(f"⚠️ Future 정리 중 예외 (무시됨): {e}")
        
        # 6. 최종 대기
        logger.info("⏳ 최종 정리를 위한 대기...")
        await asyncio.sleep(3.0)
        
        logger.info("✅ 최종 정리 작업 완료")
        
    except Exception as e:
        logger.error(f"❌ 정리 작업 중 오류: {e}")

async def main():
    """
    메인 함수
    """
    try:
        print("🚀 심플 통합 크롤러 시작")
        
        # 크롤러 생성 및 실행
        crawler = SimpleIntegratedCrawler()
        success = await crawler.run()
        
        if success:
            print("\n🎉 모든 작업이 완료되었습니다!")
        else:
            print("\n❌ 작업 중 오류가 발생했습니다.")
        
        # 최종 정리 작업
        await cleanup_and_wait()
            
    except KeyboardInterrupt:
        print("\n❌ 사용자에 의해 중단됨")
        try:
            await cleanup_and_wait()
        except:
            pass
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        try:
            await cleanup_and_wait()
        except:
            pass

if __name__ == "__main__":
    # 시그널 핸들러 설정 (Linux/Mac)
    def signal_handler(signum, frame):
        print(f"\n🛑 시그널 {signum} 수신 - 정리 작업 후 종료")
        
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, signal_handler)
    
    # 이벤트 루프 실행
    try:
        asyncio.run(main())
        # 추가 대기 시간 (서브프로세스 완전 정리)
        import time
        time.sleep(2.0)
        print("🔚 프로그램 종료")
    except KeyboardInterrupt:
        print("\n🔚 프로그램 강제 종료")
    except Exception as e:
        print(f"\n❌ 프로그램 종료 중 오류: {e}") 