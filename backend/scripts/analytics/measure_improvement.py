#!/usr/bin/env python3
"""
     

 /      .
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from collections import defaultdict, Counter

class ImprovementMeasurer:
    """  """
    
    def __init__(self, transformed_dir: str = "backend/data/transformed"):
        """"""
        self.transformed_dir = Path(transformed_dir)
        self.validation_file = self.transformed_dir / "validation_result.json"
        self.summary_file = self.transformed_dir / "transformation_summary.json"
        
        #     ( )
        self.baseline = {
            'total_documents': 12150,
            'total_chunks': 14898,
            'critical_issues': 92,
            'warnings': 1797,
            'short_chunks': 1500,  # ~1,500
            'long_chunks': 300     # ~300
        }
    
    def load_current_data(self) -> Dict:
        """  """
        print("    ...")
        
        #  
        with open(self.validation_file, 'r', encoding='utf-8') as f:
            validation = json.load(f)
        
        #  
        with open(self.summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        print("     ")
        
        return {
            'validation': validation,
            'summary': summary
        }
    
    def analyze_chunk_sizes(self) -> Dict:
        """  """
        print("\n    ...")
        
        #      
        chunk_stats = {
            'by_type': defaultdict(list),
            'total': [],
            'short_count': 0,  # < 100
            'optimal_count': 0,  # 100-2000
            'long_count': 0,  # > 2000
            'very_long_count': 0  # > 5000
        }
        
        for json_file in self.transformed_dir.glob("*.json"):
            if json_file.name in ['validation_result.json', 'transformation_summary.json']:
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                #   
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
                        
                        #  
                        if content_len < 100:
                            chunk_stats['short_count'] += 1
                        elif content_len <= 2000:
                            chunk_stats['optimal_count'] += 1
                        elif content_len <= 5000:
                            chunk_stats['long_count'] += 1
                        else:
                            chunk_stats['very_long_count'] += 1
            
            except Exception as e:
                print(f"    {json_file.name}   : {e}")
                continue
        
        print(f"   {len(chunk_stats['total'])}   ")
        
        return chunk_stats
    
    def calculate_improvement(self, current_data: Dict, chunk_stats: Dict) -> Dict:
        """ """
        print("\n   ...")
        
        validation = current_data['validation']
        summary = current_data['summary']
        
        #  
        current = {
            'total_documents': summary['stats']['documents'],
            'total_chunks': summary['stats']['chunks'],
            'critical_issues': validation['issues_count'],
            'warnings': validation['warnings_count'],
            'short_chunks': chunk_stats['short_count'],
            'long_chunks': chunk_stats['long_count'] + chunk_stats['very_long_count']
        }
        
        #  
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
        
        print("     ")
        
        return {
            'baseline': self.baseline,
            'current': current,
            'improvements': improvements,
            'chunk_stats': chunk_stats
        }
    
    def generate_report(self, analysis: Dict) -> str:
        """ """
        print("\n   ...")
        
        baseline = analysis['baseline']
        current = analysis['current']
        improvements = analysis['improvements']
        chunk_stats = analysis['chunk_stats']
        
        report = []
        report.append("=" * 100)
        report.append("     ")
        report.append("=" * 100)
        report.append(f" : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 1.   
        report.append("1.   ")
        report.append("-" * 100)
        report.append(f"{'':<30} {' ':>15} {' ':>15} {'':>15} {'':<20}")
        report.append("-" * 100)
        
        report.append(f"{'  ':<30} {baseline['total_documents']:>15,} "
                     f"{current['total_documents']:>15,} "
                     f"{current['total_documents'] - baseline['total_documents']:>+15,}")
        
        report.append(f"{'  ':<30} {baseline['total_chunks']:>15,} "
                     f"{current['total_chunks']:>15,} "
                     f"{current['total_chunks'] - baseline['total_chunks']:>+15,}")
        
        report.append("")
        
        # 2.   
        report.append("2.   ")
        report.append("-" * 100)
        report.append(f"{'':<30} {' ':>15} {' ':>15} {'':>15} {'':>15}")
        report.append("-" * 100)
        
        for key, label in [
            ('critical_issues', 'Critical Issues ( )'),
            ('short_chunks', '  (< 100)'),
            ('long_chunks', '  (> 2,000)')
        ]:
            imp = improvements[key]
            report.append(f"{label:<30} {imp['baseline']:>15,} "
                         f"{imp['current']:>15,} "
                         f"{imp['delta']:>+15,} "
                         f"{imp['improvement_rate']:>14.1f}%")
        
        report.append("")
        
        # 3.   
        report.append("3.    ( )")
        report.append("-" * 100)
        
        total_active_chunks = len(chunk_stats['total'])
        
        if total_active_chunks > 0:
            report.append(f"{'':<30} {'':>15} {'':>15}")
            report.append("-" * 100)
            report.append(f"{'  (< 100)':<30} "
                         f"{chunk_stats['short_count']:>15,} "
                         f"{chunk_stats['short_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'  (100-2,000)':<30} "
                         f"{chunk_stats['optimal_count']:>15,} "
                         f"{chunk_stats['optimal_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'  (2,000-5,000)':<30} "
                         f"{chunk_stats['long_count']:>15,} "
                         f"{chunk_stats['long_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'   (> 5,000)':<30} "
                         f"{chunk_stats['very_long_count']:>15,} "
                         f"{chunk_stats['very_long_count']/total_active_chunks*100:>14.1f}%")
            report.append(f"{'':<30} {total_active_chunks:>15,} {'100.0%':>15}")
        else:
            report.append("   .")
        
        report.append("")
        
        # 4.   
        report.append("4.    ")
        report.append("-" * 100)
        report.append(f"{' ':<30} {'':>15} {' ':>15} {'':>15} {'':>15}")
        report.append("-" * 100)
        
        for chunk_type, lengths in sorted(chunk_stats['by_type'].items()):
            if lengths:
                avg_len = sum(lengths) / len(lengths)
                min_len = min(lengths)
                max_len = max(lengths)
                report.append(f"{chunk_type:<30} {len(lengths):>15,} "
                             f"{avg_len:>15,.0f} {min_len:>15,} {max_len:>15,}")
        
        report.append("")
        
        # 5.    
        report.append("5.    ")
        report.append("-" * 100)
        
        critical_improvement = improvements['critical_issues']
        if critical_improvement['improvement_rate'] >= 100:
            report.append(f" Critical Issues  : {critical_improvement['baseline']} → {critical_improvement['current']}")
        else:
            report.append(f"  Critical Issues  : {critical_improvement['baseline']} → {critical_improvement['current']} "
                         f"({critical_improvement['improvement_rate']:.1f}% )")
        
        short_improvement = improvements['short_chunks']
        report.append(f"   : {short_improvement['baseline']} → {short_improvement['current']} "
                     f"({short_improvement['improvement_rate']:.1f}% )")
        
        long_improvement = improvements['long_chunks']
        report.append(f"   : {long_improvement['baseline']} → {long_improvement['current']} "
                     f"({long_improvement['improvement_rate']:.1f}% )")
        
        if total_active_chunks > 0:
            optimal_rate = chunk_stats['optimal_count'] / total_active_chunks * 100
            report.append(f"    : {optimal_rate:.1f}%")
        else:
            optimal_rate = 0
            report.append(f"    :   ( )")
        
        report.append("")
        
        # 6.    
        report.append("6.    ")
        report.append("-" * 100)
        report.append("       ")
        report.append("   /    ")
        report.append("       ")
        report.append(f"     : {optimal_rate:.1f}%")
        report.append("")
        report.append("   : +15-25% (  )")
        
        report.append("")
        report.append("=" * 100)
        
        print("     ")
        
        return "\n".join(report)
    
    def save_report(self, report: str, output_file: str = None):
        """ """
        if output_file is None:
            output_file = self.transformed_dir / "improvement_report.txt"
        else:
            output_file = Path(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n  : {output_file}")
    
    def run(self):
        """ """
        print("=" * 100)
        print("     ")
        print("=" * 100)
        
        try:
            # 1.   
            current_data = self.load_current_data()
            
            # 2.   
            chunk_stats = self.analyze_chunk_sizes()
            
            # 3.  
            analysis = self.calculate_improvement(current_data, chunk_stats)
            
            # 4.  
            report = self.generate_report(analysis)
            
            # 5.   
            print("\n" + report)
            self.save_report(report)
            
            print("\n  !")
            return 0
            
        except Exception as e:
            print(f"\n  : {e}")
            import traceback
            traceback.print_exc()
            return 1

def main():
    """ """
    measurer = ImprovementMeasurer()
    return measurer.run()

if __name__ == '__main__':
    sys.exit(main())
