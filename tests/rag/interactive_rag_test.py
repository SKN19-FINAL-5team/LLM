"""
인터랙티브 RAG 테스트 도구

사용자가 직접 쿼리를 입력하여 RAG 시스템을 테스트하고,
다양한 검색 방식의 결과를 비교 분석할 수 있는 CLI 도구
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
import time
import statistics

# 프로젝트 루트와 backend 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag import VectorRetriever, MultiStageRetriever

# rich 라이브러리 사용 (없으면 기본 출력)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  rich 라이브러리가 없습니다. 기본 출력을 사용합니다.")
    print("   더 나은 출력을 위해: pip install rich")

# 환경 변수 로드
load_dotenv()

# 전역 변수
console = Console() if RICH_AVAILABLE else None
test_history: List[Dict] = []


class InteractiveRAGTester:
    """인터랙티브 RAG 테스터"""
    
    def __init__(self, db_config: Dict):
        """초기화"""
        self.db_config = db_config
        self.single_retriever = None
        self.multi_retriever = None
        self._init_retrievers()
    
    def _init_retrievers(self):
        """검색기 초기화"""
        try:
            if RICH_AVAILABLE:
                with console.status("[bold green]검색기 초기화 중...") as status:
                    self.single_retriever = VectorRetriever(self.db_config)
                    self.multi_retriever = MultiStageRetriever(self.db_config)
            else:
                print("검색기 초기화 중...")
                self.single_retriever = VectorRetriever(self.db_config)
                self.multi_retriever = MultiStageRetriever(self.db_config)
            
            if RICH_AVAILABLE:
                console.print("[bold green]✅ 검색기 초기화 완료[/bold green]")
            else:
                print("✅ 검색기 초기화 완료")
        except Exception as e:
            error_msg = f"검색기 초기화 실패: {e}"
            if RICH_AVAILABLE:
                console.print(f"[bold red]❌ {error_msg}[/bold red]")
            else:
                print(f"❌ {error_msg}")
            raise
    
    def close(self):
        """리소스 정리"""
        if self.single_retriever:
            self.single_retriever.close()
        if self.multi_retriever:
            self.multi_retriever.close()
    
    def test_single_search(self, query: str, top_k: int = 10) -> Dict:
        """단일 검색 테스트"""
        start_time = time.time()
        results = self.single_retriever.search(query, top_k=top_k)
        elapsed_time = time.time() - start_time
        
        return {
            'query': query,
            'method': 'single',
            'results': results,
            'count': len(results),
            'elapsed_time': elapsed_time,
            'similarities': [r.get('similarity', 0) for r in results] if results else []
        }
    
    def test_multi_stage_search(
        self, 
        query: str,
        law_top_k: int = 3,
        criteria_top_k: int = 3,
        mediation_top_k: int = 5,
        counsel_top_k: int = 3
    ) -> Dict:
        """멀티 스테이지 검색 테스트"""
        start_time = time.time()
        results = self.multi_retriever.search_multi_stage(
            query=query,
            law_top_k=law_top_k,
            criteria_top_k=criteria_top_k,
            mediation_top_k=mediation_top_k,
            counsel_top_k=counsel_top_k,
            enable_agency_recommendation=True
        )
        elapsed_time = time.time() - start_time
        
        # 모든 청크 수집
        all_chunks = []
        if results.get('stage1'):
            all_chunks.extend(results['stage1'].get('law', []))
            all_chunks.extend(results['stage1'].get('criteria', []))
        all_chunks.extend(results.get('stage2', []))
        all_chunks.extend(results.get('stage3', []))
        
        similarities = [chunk.get('similarity', 0) for chunk in all_chunks if chunk.get('similarity')]
        
        return {
            'query': query,
            'method': 'multi_stage',
            'results': results,
            'count': len(all_chunks),
            'elapsed_time': elapsed_time,
            'similarities': similarities,
            'stage1_law': len(results.get('stage1', {}).get('law', [])),
            'stage1_criteria': len(results.get('stage1', {}).get('criteria', [])),
            'stage2': len(results.get('stage2', [])),
            'stage3': len(results.get('stage3', [])),
            'used_fallback': results.get('used_fallback', False),
            'agency_recommendation': results.get('agency_recommendation')
        }
    
    def compare_searches(self, query: str) -> Dict:
        """단일 검색 vs 멀티 스테이지 검색 비교"""
        single_result = self.test_single_search(query, top_k=10)
        multi_result = self.test_multi_stage_search(query)
        
        return {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'single': single_result,
            'multi': multi_result,
            'comparison': {
                'result_count_diff': multi_result['count'] - single_result['count'],
                'time_diff': multi_result['elapsed_time'] - single_result['elapsed_time'],
                'avg_similarity_single': statistics.mean(single_result['similarities']) if single_result['similarities'] else 0,
                'avg_similarity_multi': statistics.mean(multi_result['similarities']) if multi_result['similarities'] else 0,
            }
        }
    
    def calculate_similarity_stats(self, similarities: List[float]) -> Dict:
        """유사도 통계 계산"""
        if not similarities:
            return {}
        
        # 구간별 분포
        ranges = {
            '0.0-0.3': sum(1 for s in similarities if 0.0 <= s < 0.3),
            '0.3-0.5': sum(1 for s in similarities if 0.3 <= s < 0.5),
            '0.5-0.7': sum(1 for s in similarities if 0.5 <= s < 0.7),
            '0.7-1.0': sum(1 for s in similarities if 0.7 <= s <= 1.0)
        }
        
        return {
            'count': len(similarities),
            'mean': statistics.mean(similarities),
            'median': statistics.median(similarities),
            'max': max(similarities),
            'min': min(similarities),
            'stdev': statistics.stdev(similarities) if len(similarities) > 1 else 0,
            'ranges': ranges
        }
    
    def display_results(self, comparison_result: Dict, detailed: bool = False):
        """결과 출력"""
        query = comparison_result['query']
        single = comparison_result['single']
        multi = comparison_result['multi']
        comp = comparison_result['comparison']
        
        if RICH_AVAILABLE:
            # 쿼리 표시
            console.print(Panel(
                f"[bold cyan]{query}[/bold cyan]",
                title="검색 쿼리",
                border_style="cyan"
            ))
            
            # 비교 테이블
            table = Table(title="검색 방법 비교", box=box.ROUNDED)
            table.add_column("항목", style="cyan")
            table.add_column("단일 검색", style="green")
            table.add_column("멀티 스테이지", style="yellow")
            table.add_column("차이", style="magenta")
            
            table.add_row(
                "결과 수",
                str(single['count']),
                str(multi['count']),
                f"{comp['result_count_diff']:+d}"
            )
            table.add_row(
                "응답 시간",
                f"{single['elapsed_time']:.2f}초",
                f"{multi['elapsed_time']:.2f}초",
                f"{comp['time_diff']:+.2f}초"
            )
            table.add_row(
                "평균 유사도",
                f"{comp['avg_similarity_single']:.3f}",
                f"{comp['avg_similarity_multi']:.3f}",
                f"{comp['avg_similarity_multi'] - comp['avg_similarity_single']:+.3f}"
            )
            
            console.print(table)
            
            # 멀티 스테이지 상세 정보
            stage_table = Table(title="멀티 스테이지 검색 상세", box=box.ROUNDED)
            stage_table.add_column("Stage", style="cyan")
            stage_table.add_column("결과 수", style="green")
            
            stage_table.add_row("Stage 1: 법령", str(multi['stage1_law']))
            stage_table.add_row("Stage 1: 기준", str(multi['stage1_criteria']))
            stage_table.add_row("Stage 2: 분쟁조정사례", str(multi['stage2']))
            stage_table.add_row("Stage 3: 피해구제사례", str(multi['stage3']))
            stage_table.add_row("Fallback 사용", "예" if multi['used_fallback'] else "아니오")
            
            console.print(stage_table)
            
            # 유사도 통계
            if single['similarities']:
                single_stats = self.calculate_similarity_stats(single['similarities'])
                multi_stats = self.calculate_similarity_stats(multi['similarities'])
                
                stats_table = Table(title="유사도 통계", box=box.ROUNDED)
                stats_table.add_column("통계", style="cyan")
                stats_table.add_column("단일 검색", style="green")
                stats_table.add_column("멀티 스테이지", style="yellow")
                
                stats_table.add_row("평균", f"{single_stats['mean']:.3f}", f"{multi_stats['mean']:.3f}")
                stats_table.add_row("중앙값", f"{single_stats['median']:.3f}", f"{multi_stats['median']:.3f}")
                stats_table.add_row("최대값", f"{single_stats['max']:.3f}", f"{multi_stats['max']:.3f}")
                stats_table.add_row("최소값", f"{single_stats['min']:.3f}", f"{multi_stats['min']:.3f}")
                stats_table.add_row("표준편차", f"{single_stats['stdev']:.3f}", f"{multi_stats['stdev']:.3f}")
                
                console.print(stats_table)
                
                # 유사도 구간별 분포
                dist_table = Table(title="유사도 구간별 분포", box=box.ROUNDED)
                dist_table.add_column("구간", style="cyan")
                dist_table.add_column("단일 검색", style="green")
                dist_table.add_column("멀티 스테이지", style="yellow")
                
                for range_key in ['0.0-0.3', '0.3-0.5', '0.5-0.7', '0.7-1.0']:
                    dist_table.add_row(
                        range_key,
                        str(single_stats['ranges'].get(range_key, 0)),
                        str(multi_stats['ranges'].get(range_key, 0))
                    )
                
                console.print(dist_table)
            
            # 기관 추천
            if multi.get('agency_recommendation'):
                agency_info = multi['agency_recommendation']
                if isinstance(agency_info, dict) and 'formatted' in agency_info:
                    console.print(Panel(
                        agency_info['formatted'],
                        title="기관 추천",
                        border_style="yellow"
                    ))
                elif isinstance(agency_info, dict) and 'top_agency' in agency_info:
                    top_agency = agency_info['top_agency']
                    if top_agency:
                        console.print(Panel(
                            f"추천 기관: {top_agency[0]}\n점수: {top_agency[1]:.3f}",
                            title="기관 추천",
                            border_style="yellow"
                        ))
            
            # 상세 결과 (선택적)
            if detailed:
                console.print("\n[bold]상세 검색 결과:[/bold]")
                console.print("\n[bold green]단일 검색 상위 5개:[/bold green]")
                for i, chunk in enumerate(single['results'][:5], 1):
                    console.print(f"{i}. 유사도: {chunk.get('similarity', 0):.3f}")
                    console.print(f"   {chunk.get('content', '')[:100]}...")
                
                console.print("\n[bold yellow]멀티 스테이지 검색 결과:[/bold yellow]")
                if multi['results'].get('stage1', {}).get('law'):
                    console.print("\n[bold]Stage 1 - 법령:[/bold]")
                    for chunk in multi['results']['stage1']['law'][:3]:
                        console.print(f"  - 유사도: {chunk.get('similarity', 0):.3f}")
                        console.print(f"    {chunk.get('content', '')[:80]}...")
                
                if multi['results'].get('stage2'):
                    console.print("\n[bold]Stage 2 - 분쟁조정사례:[/bold]")
                    for chunk in multi['results']['stage2'][:3]:
                        console.print(f"  - 유사도: {chunk.get('similarity', 0):.3f}")
                        console.print(f"    {chunk.get('content', '')[:80]}...")
        else:
            # 기본 출력
            print(f"\n{'='*80}")
            print(f"검색 쿼리: {query}")
            print(f"{'='*80}\n")
            
            print("검색 방법 비교:")
            print(f"  결과 수: 단일={single['count']}, 멀티={multi['count']} (차이: {comp['result_count_diff']:+d})")
            print(f"  응답 시간: 단일={single['elapsed_time']:.2f}초, 멀티={multi['elapsed_time']:.2f}초 (차이: {comp['time_diff']:+.2f}초)")
            print(f"  평균 유사도: 단일={comp['avg_similarity_single']:.3f}, 멀티={comp['avg_similarity_multi']:.3f}")
            
            print("\n멀티 스테이지 검색 상세:")
            print(f"  Stage 1 - 법령: {multi['stage1_law']}개")
            print(f"  Stage 1 - 기준: {multi['stage1_criteria']}개")
            print(f"  Stage 2 - 분쟁조정사례: {multi['stage2']}개")
            print(f"  Stage 3 - 피해구제사례: {multi['stage3']}개")
            print(f"  Fallback 사용: {'예' if multi['used_fallback'] else '아니오'}")
            
            if single['similarities']:
                single_stats = self.calculate_similarity_stats(single['similarities'])
                multi_stats = self.calculate_similarity_stats(multi['similarities'])
                
                print("\n유사도 통계:")
                print(f"  평균: 단일={single_stats['mean']:.3f}, 멀티={multi_stats['mean']:.3f}")
                print(f"  최대: 단일={single_stats['max']:.3f}, 멀티={multi_stats['max']:.3f}")
                print(f"  최소: 단일={single_stats['min']:.3f}, 멀티={multi_stats['min']:.3f}")
    
    def save_result(self, comparison_result: Dict, output_dir: str = "test_results"):
        """결과를 JSON 파일로 저장"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rag_test_{timestamp}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(comparison_result, f, ensure_ascii=False, indent=2)
        
        if RICH_AVAILABLE:
            console.print(f"[bold green]✅ 결과 저장: {filepath}[/bold green]")
        else:
            print(f"✅ 결과 저장: {filepath}")
        
        return filepath
    
    def export_to_csv(self, results: List[Dict], output_file: str = "rag_test_comparison.csv"):
        """여러 결과를 CSV로 내보내기"""
        if not results:
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                '쿼리', '타임스탬프',
                '단일_결과수', '단일_시간', '단일_평균유사도',
                '멀티_결과수', '멀티_시간', '멀티_평균유사도',
                '차이_결과수', '차이_시간', '차이_유사도',
                'Stage1_법령', 'Stage1_기준', 'Stage2', 'Stage3', 'Fallback'
            ])
            
            # 데이터
            for result in results:
                single = result['single']
                multi = result['multi']
                comp = result['comparison']
                
                writer.writerow([
                    result['query'],
                    result['timestamp'],
                    single['count'],
                    f"{single['elapsed_time']:.2f}",
                    f"{comp['avg_similarity_single']:.3f}",
                    multi['count'],
                    f"{multi['elapsed_time']:.2f}",
                    f"{comp['avg_similarity_multi']:.3f}",
                    comp['result_count_diff'],
                    f"{comp['time_diff']:.2f}",
                    f"{comp['avg_similarity_multi'] - comp['avg_similarity_single']:.3f}",
                    multi['stage1_law'],
                    multi['stage1_criteria'],
                    multi['stage2'],
                    multi['stage3'],
                    '예' if multi['used_fallback'] else '아니오'
                ])
        
        if RICH_AVAILABLE:
            console.print(f"[bold green]✅ CSV 내보내기 완료: {output_file}[/bold green]")
        else:
            print(f"✅ CSV 내보내기 완료: {output_file}")


def show_menu():
    """메뉴 표시"""
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]RAG 시스템 인터랙티브 테스트[/bold cyan]")
        console.print("\n[bold]메뉴:[/bold]")
        console.print("  1. 단일 쿼리 테스트 (비교 분석)")
        console.print("  2. 멀티 스테이지 검색만 테스트")
        console.print("  3. 결과 히스토리 보기")
        console.print("  4. 결과 저장/내보내기")
        console.print("  5. 종료")
    else:
        print("\nRAG 시스템 인터랙티브 테스트")
        print("\n메뉴:")
        print("  1. 단일 쿼리 테스트 (비교 분석)")
        print("  2. 멀티 스테이지 검색만 테스트")
        print("  3. 결과 히스토리 보기")
        print("  4. 결과 저장/내보내기")
        print("  5. 종료")


def main():
    """메인 함수"""
    # 데이터베이스 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 테스터 초기화
    tester = InteractiveRAGTester(db_config)
    
    try:
        while True:
            show_menu()
            choice = input("\n선택 (1-5): ").strip()
            
            if choice == '1':
                # 단일 쿼리 테스트 (비교 분석)
                query = input("\n검색할 쿼리를 입력하세요: ").strip()
                if not query:
                    print("쿼리를 입력해주세요.")
                    continue
                
                detailed = input("상세 결과를 보시겠습니까? (y/n): ").strip().lower() == 'y'
                
                if RICH_AVAILABLE:
                    with console.status("[bold green]검색 중...") as status:
                        comparison_result = tester.compare_searches(query)
                else:
                    print("검색 중...")
                    comparison_result = tester.compare_searches(query)
                
                tester.display_results(comparison_result, detailed=detailed)
                
                # 히스토리에 추가
                test_history.append(comparison_result)
                
                save = input("\n결과를 저장하시겠습니까? (y/n): ").strip().lower() == 'y'
                if save:
                    tester.save_result(comparison_result)
            
            elif choice == '2':
                # 멀티 스테이지 검색만 테스트
                query = input("\n검색할 쿼리를 입력하세요: ").strip()
                if not query:
                    print("쿼리를 입력해주세요.")
                    continue
                
                if RICH_AVAILABLE:
                    with console.status("[bold green]멀티 스테이지 검색 중...") as status:
                        result = tester.test_multi_stage_search(query)
                else:
                    print("멀티 스테이지 검색 중...")
                    result = tester.test_multi_stage_search(query)
                
                if RICH_AVAILABLE:
                    console.print(f"\n[bold]검색 결과:[/bold]")
                    console.print(f"총 결과 수: {result['count']}개")
                    console.print(f"응답 시간: {result['elapsed_time']:.2f}초")
                    console.print(f"Stage 1 - 법령: {result['stage1_law']}개")
                    console.print(f"Stage 1 - 기준: {result['stage1_criteria']}개")
                    console.print(f"Stage 2: {result['stage2']}개")
                    console.print(f"Stage 3: {result['stage3']}개")
                else:
                    print(f"\n검색 결과:")
                    print(f"총 결과 수: {result['count']}개")
                    print(f"응답 시간: {result['elapsed_time']:.2f}초")
                    print(f"Stage 1 - 법령: {result['stage1_law']}개")
                    print(f"Stage 1 - 기준: {result['stage1_criteria']}개")
                    print(f"Stage 2: {result['stage2']}개")
                    print(f"Stage 3: {result['stage3']}개")
            
            elif choice == '3':
                # 결과 히스토리 보기
                if not test_history:
                    if RICH_AVAILABLE:
                        console.print("[yellow]히스토리가 비어있습니다.[/yellow]")
                    else:
                        print("히스토리가 비어있습니다.")
                    continue
                
                if RICH_AVAILABLE:
                    console.print(f"\n[bold]히스토리 ({len(test_history)}개):[/bold]")
                    for i, result in enumerate(test_history, 1):
                        console.print(f"{i}. {result['query'][:50]}...")
                        console.print(f"   단일: {result['single']['count']}개, "
                                    f"멀티: {result['multi']['count']}개")
                else:
                    print(f"\n히스토리 ({len(test_history)}개):")
                    for i, result in enumerate(test_history, 1):
                        print(f"{i}. {result['query'][:50]}...")
                        print(f"   단일: {result['single']['count']}개, "
                              f"멀티: {result['multi']['count']}개")
            
            elif choice == '4':
                # 결과 저장/내보내기
                if not test_history:
                    if RICH_AVAILABLE:
                        console.print("[yellow]저장할 결과가 없습니다.[/yellow]")
                    else:
                        print("저장할 결과가 없습니다.")
                    continue
                
                print("\n저장 옵션:")
                print("  1. JSON으로 저장 (개별 파일)")
                print("  2. CSV로 내보내기 (전체 비교)")
                
                save_choice = input("선택 (1-2): ").strip()
                
                if save_choice == '1':
                    for result in test_history:
                        tester.save_result(result)
                elif save_choice == '2':
                    output_file = input("CSV 파일명 (기본: rag_test_comparison.csv): ").strip()
                    if not output_file:
                        output_file = "rag_test_comparison.csv"
                    tester.export_to_csv(test_history, output_file)
            
            elif choice == '5':
                # 종료
                if RICH_AVAILABLE:
                    console.print("[bold green]프로그램을 종료합니다.[/bold green]")
                else:
                    print("프로그램을 종료합니다.")
                break
            
            else:
                if RICH_AVAILABLE:
                    console.print("[red]잘못된 선택입니다.[/red]")
                else:
                    print("잘못된 선택입니다.")
    
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print("\n[yellow]프로그램이 중단되었습니다.[/yellow]")
        else:
            print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]오류 발생: {e}[/bold red]")
        else:
            print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.close()


if __name__ == "__main__":
    main()
