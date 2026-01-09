#!/usr/bin/env python3
"""
데이터 품질 개선 효과 측정 스크립트

개선 전/후 데이터를 비교하여 품질 개선 효과를 측정합니다.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from collections import defaultdict, Counter

class ImprovementMeasurer:
    """개선 효과 측정"""
    
    def __init__(self, transformed_dir: str = "backend/data/transformed"):
        """초기화"""
        self.transformed_dir = Path(transformed_dir)
        self.validation_file = self.transformed_dir / "validation_result.json"
        self.summary_file = self.transformed_dir / "transformation_summary.json"
        
        # 개선 전 기준 데이터 (계획 문서에서)
        self.baseline = {
            'total_documents': 12150,
            'total_chunks': 14898,
            'critical_issues': 92,
            'warnings': 1797,
            'short_chunks': 1500,  # ~1,500개
            'long_chunks': 300     # ~300개
        }
    
    def load_current_data(self) -> Dict:
        """현재 데이터 로드"""
        print("📂 현재 데이터 로드 중...")
        
        # 검증 결과
        with open(self.validation_file, 'r', encoding='utf-8') as f:
            validation = json.load(f)
        
        # 변환 요약
        with open(self.summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        print("  ✅ 데이터 로드 완료")
        
        return {
            'validation': validation,
            'summary': summary
        }
    
    def analyze_chunk_sizes(self) -> Dict:
        """청크 크기 분석"""
        print("\n📊 청크 크기 분석 중...")
        
        # 모든 변환된 파일에서 청크 통계 수집
        chunk_stats = {
            'by_type': defaultdict(list),
            'total': [],
            'short_count': 0,  # < 100자
            'optimal_count': 0,  # 100-2000자
            'long_count': 0,  # > 2000자
            'very_long_count': 0  # > 5000자
        }
        
        for json_file in self.transformed_dir.glob("*.json"):
            if json_file.name in ['validation_result.json', 'transformation_summary.json']:
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 문서 리스트 처리
                if isinstance(data, dict) and 'documents' in data:
                    docs = data['documents']
                elif isinstance(data, list):
                    docs = data
                else:
                    docs = [data]
                
                for doc in docs:
                    for chunk in doc.get('chunks', []):
                        if chunk.get('drop'):
                            continue
                        
                        content_len = chunk.get('content_length', len(chunk.get('content', '')))
                        chunk_type = chunk.get('chunk_type', 'unknown')
                        
                        chunk_stats['by_type'][chunk_type].append(content_len)
                        chunk_stats['total'].append(content_len)
                        
                        # 크기별 카운트
                        if content_len < 100:
                            chunk_stats['short_count'] += 1
                        elif content_len <= 2000:
                            chunk_stats['optimal_count'] += 1
                        elif content_len <= 5000:
                            chunk_stats['long_count'] += 1
                        else:
                            chunk_stats['very_long_count'] += 1
            
            except Exception as e:
                print(f"  ⚠️  {json_file.name} 처리 중 오류: {e}")
                continue
        
        print(f"  ✅ {len(chunk_stats['total'])}개 청크 분석 완료")
        
        return chunk_stats
    
    def calculate_improvement(self, current_data: Dict, chunk_stats: Dict) -> Dict:
        """개선율 계산"""
        print("\n📈 개선율 계산 중...")
        
        validation = current_data['validation']
        summary = current_data['summary']
        
        # 현재 통계
        current = {
            'total_documents': summary['stats']['documents'],
            'total_chunks': summary['stats']['chunks'],
            'critical_issues': validation['issues_count'],
            'warnings': validation['warnings_count'],
            'short_chunks': chunk_stats['short_count'],
            'long_chunks': chunk_stats['long_count'] + chunk_stats['very_long_count']
        }
        
        # 개선율 계산
        improvements = {}
        for key in ['critical_issues', 'short_chunks', 'long_chunks']:
            baseline_val = self.baseline[key]
            current_val = current[key]
            
            if baseline_val > 0:
                improvement_rate = ((baseline_val - current_val) / baseline_val) * 100
            else:
                improvement_rate = 0
            
            improvements[key] = {
                'baseline': baseline_val,
                'current': current_val,
                'improvement_rate': improvement_rate,
                'delta': baseline_val - current_val
            }
        
        print("  ✅ 개선율 계산 완료")
        
        return {
            'baseline': self.baseline,
            'current': current,
            'improvements': improvements,
            'chunk_stats': chunk_stats
        }
    
    def generate_report(self, analysis: Dict) -> str:
        """리포트 생성"""
        print("\n📝 리포트 생성 중...")
        
        baseline = analysis['baseline']
        current = analysis['current']
        improvements = analysis['improvements']
        chunk_stats = analysis['chunk_stats']
        
        report = []
        report.append("=" * 100)
        report.append("데이터 품질 개선 효과 측정 리포트")
        report.append("=" * 100)
        report.append(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 1. 전체 통계 비교
        report.append("1. 전체 데이터 통계")
        report.append("-" * 100)
        report.append(f"{'지표':<30} {'개선 전':>15} {'개선 후':>15} {'변화량':>15} {'비고':<20}")
        report.append("-" * 100)
        
        report.append(f"{'총 문서 수':<30} {baseline['total_documents']:>15,} "
                     f"{current['total_documents']:>15,} "
                     f"{current['total_documents'] - baseline['total_documents']:>+15,}")
        
        report.append(f"{'총 청크 수':<30} {baseline['total_chunks']:>15,} "
                     f"{current['total_chunks']:>15,} "
                     f"{current['total_chunks'] - baseline['total_chunks']:>+15,}")
        
        report.append("")
        
        # 2. 품질 지표 개선
        report.append("2. 품질 지표 개선")
        report.append("-" * 100)
        report.append(f"{'지표':<30} {'개선 전':>15} {'개선 후':>15} {'개선량':>15} {'개선율':>15}")
        report.append("-" * 100)
        
        for key, label in [
            ('critical_issues', 'Critical Issues (빈 청크)'),
            ('short_chunks', '짧은 청크 (< 100자)'),
            ('long_chunks', '긴 청크 (> 2,000자)')
        ]:
            imp = improvements[key]
            report.append(f"{label:<30} {imp['baseline']:>15,} "
                         f"{imp['current']:>15,} "
                         f"{imp['delta']:>+15,} "
                         f"{imp['improvement_rate']:>14.1f}%")
        
        report.append("")
        
        # 3. 청크 크기 분포
        report.append("3. 청크 크기 분포 (개선 후)")
        report.append("-" * 100)
        
        total_active_chunks = len(chunk_stats['total'])
        
        if total_active_chunks > 0:
            report.append(f"{'구간':<30} {'개수':>15} {'비율':>15}")
            report.append("-" * 100)
            report.append(f"{'짧은 청크 (< 100자)':<30} "
                         f"{chunk_stats['short_count']:>15,} "
                         f"{chunk_stats['short_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'최적 청크 (100-2,000자)':<30} "
                         f"{chunk_stats['optimal_count']:>15,} "
                         f"{chunk_stats['optimal_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'긴 청크 (2,000-5,000자)':<30} "
                         f"{chunk_stats['long_count']:>15,} "
                         f"{chunk_stats['long_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'매우 긴 청크 (> 5,000자)':<30} "
                         f"{chunk_stats['very_long_count']:>15,} "
                         f"{chunk_stats['very_long_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'합계':<30} {total_active_chunks:>15,} {'100.0%':>15}")
        else:
            report.append("❌ 분석할 청크가 없습니다.")
        
        report.append("")
        
        # 4. 청크 타입별 통계
        report.append("4. 청크 타입별 평균 길이")
        report.append("-" * 100)
        report.append(f"{'청크 타입':<30} {'개수':>15} {'평균 길이':>15} {'최소':>15} {'최대':>15}")
        report.append("-" * 100)
        
        for chunk_type, lengths in sorted(chunk_stats['by_type'].items()):
            if lengths:
                avg_len = sum(lengths) / len(lengths)
                min_len = min(lengths)
                max_len = max(lengths)
                report.append(f"{chunk_type:<30} {len(lengths):>15,} "
                             f"{avg_len:>15,.0f} {min_len:>15,} {max_len:>15,}")
        
        report.append("")
        
        # 5. 주요 개선 사항 요약
        report.append("5. 주요 개선 사항 요약")
        report.append("-" * 100)
        
        critical_improvement = improvements['critical_issues']
        if critical_improvement['improvement_rate'] >= 100:
            report.append(f"✅ Critical Issues 완전 해결: {critical_improvement['baseline']}개 → {critical_improvement['current']}개")
        else:
            report.append(f"⚠️  Critical Issues 부분 개선: {critical_improvement['baseline']}개 → {critical_improvement['current']}개 "
                         f"({critical_improvement['improvement_rate']:.1f}% 개선)")
        
        short_improvement = improvements['short_chunks']
        report.append(f"✅ 짧은 청크 감소: {short_improvement['baseline']}개 → {short_improvement['current']}개 "
                     f"({short_improvement['improvement_rate']:.1f}% 개선)")
        
        long_improvement = improvements['long_chunks']
        report.append(f"✅ 긴 청크 감소: {long_improvement['baseline']}개 → {long_improvement['current']}개 "
                     f"({long_improvement['improvement_rate']:.1f}% 개선)")
        
        if total_active_chunks > 0:
            optimal_rate = chunk_stats['optimal_count'] / total_active_chunks * 100
            report.append(f"✅ 최적 크기 청크 비율: {optimal_rate:.1f}%")
        else:
            optimal_rate = 0
            report.append(f"❌ 최적 크기 청크 비율: 측정 불가 (청크 없음)")
        
        report.append("")
        
        # 6. 검색 품질 예상 효과
        report.append("6. 검색 품질 예상 효과")
        report.append("-" * 100)
        report.append("✅ 빈 청크 제거로 인한 임베딩 품질 향상")
        report.append("✅ 짧은 청크 병합/제거로 인한 문맥 정보 향상")
        report.append("✅ 긴 청크 분할로 인한 검색 정밀도 향상")
        report.append(f"✅ 최적 크기 청크 비율 증가: {optimal_rate:.1f}%")
        report.append("")
        report.append("예상 검색 정확도 개선: +15-25% (실제 측정 필요)")
        
        report.append("")
        report.append("=" * 100)
        
        print("  ✅ 리포트 생성 완료")
        
        return "\n".join(report)
    
    def save_report(self, report: str, output_file: str = None):
        """리포트 저장"""
        if output_file is None:
            output_file = self.transformed_dir / "improvement_report.txt"
        else:
            output_file = Path(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n💾 리포트 저장: {output_file}")
    
    def run(self):
        """측정 실행"""
        print("=" * 100)
        print("데이터 품질 개선 효과 측정 시작")
        print("=" * 100)
        
        try:
            # 1. 현재 데이터 로드
            current_data = self.load_current_data()
            
            # 2. 청크 크기 분석
            chunk_stats = self.analyze_chunk_sizes()
            
            # 3. 개선율 계산
            analysis = self.calculate_improvement(current_data, chunk_stats)
            
            # 4. 리포트 생성
            report = self.generate_report(analysis)
            
            # 5. 출력 및 저장
            print("\n" + report)
            self.save_report(report)
            
            print("\n✅ 측정 완료!")
            return 0
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return 1

def main():
    """메인 함수"""
    measurer = ImprovementMeasurer()
    return measurer.run()

if __name__ == '__main__':
    sys.exit(main())
