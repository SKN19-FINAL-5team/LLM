"""
 RAG  

    RAG  ,
        CLI 
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

#   backend  Python  
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag import VectorRetriever, MultiStageRetriever

# rich   (  )
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
    print("  rich  .   .")
    print("      : pip install rich")

#   
load_dotenv()

#  
console = Console() if RICH_AVAILABLE else None
test_history: List[Dict] = []


class InteractiveRAGTester:
    """ RAG """
    
    def __init__(self, db_config: Dict):
        """"""
        self.db_config = db_config
        self.single_retriever = None
        self.multi_retriever = None
        self._init_retrievers()
    
    def _init_retrievers(self):
        """ """
        try:
            if RICH_AVAILABLE:
                with console.status("[bold green]  ...") as status:
                    self.single_retriever = VectorRetriever(self.db_config)
                    self.multi_retriever = MultiStageRetriever(self.db_config)
            else:
                print("  ...")
                self.single_retriever = VectorRetriever(self.db_config)
                self.multi_retriever = MultiStageRetriever(self.db_config)
            
            if RICH_AVAILABLE:
                console.print("[bold green]   [/bold green]")
            else:
                print("   ")
        except Exception as e:
            error_msg = f"  : {e}"
            if RICH_AVAILABLE:
                console.print(f"[bold red] {error_msg}[/bold red]")
            else:
                print(f" {error_msg}")
            raise
    
    def close(self):
        """ """
        if self.single_retriever:
            self.single_retriever.close()
        if self.multi_retriever:
            self.multi_retriever.close()
    
    def test_single_search(self, query: str, top_k: int = 10) -> Dict:
        """  """
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
        """   """
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
        
        #   
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
        """  vs    """
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
        """  """
        if not similarities:
            return {}
        
        #  
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
        """ """
        query = comparison_result['query']
        single = comparison_result['single']
        multi = comparison_result['multi']
        comp = comparison_result['comparison']
        
        if RICH_AVAILABLE:
            #  
            console.print(Panel(
                f"[bold cyan]{query}[/bold cyan]",
                title=" ",
                border_style="cyan"
            ))
            
            #  
            table = Table(title="  ", box=box.ROUNDED)
            table.add_column("", style="cyan")
            table.add_column(" ", style="green")
            table.add_column(" ", style="yellow")
            table.add_column("", style="magenta")
            
            table.add_row(
                " ",
                str(single['count']),
                str(multi['count']),
                f"{comp['result_count_diff']:+d}"
            )
            table.add_row(
                " ",
                f"{single['elapsed_time']:.2f}",
                f"{multi['elapsed_time']:.2f}",
                f"{comp['time_diff']:+.2f}"
            )
            table.add_row(
                " ",
                f"{comp['avg_similarity_single']:.3f}",
                f"{comp['avg_similarity_multi']:.3f}",
                f"{comp['avg_similarity_multi'] - comp['avg_similarity_single']:+.3f}"
            )
            
            console.print(table)
            
            #    
            stage_table = Table(title="   ", box=box.ROUNDED)
            stage_table.add_column("Stage", style="cyan")
            stage_table.add_column(" ", style="green")
            
            stage_table.add_row("Stage 1: ", str(multi['stage1_law']))
            stage_table.add_row("Stage 1: ", str(multi['stage1_criteria']))
            stage_table.add_row("Stage 2: ", str(multi['stage2']))
            stage_table.add_row("Stage 3: ", str(multi['stage3']))
            stage_table.add_row("Fallback ", "" if multi['used_fallback'] else "")
            
            console.print(stage_table)
            
            #  
            if single['similarities']:
                single_stats = self.calculate_similarity_stats(single['similarities'])
                multi_stats = self.calculate_similarity_stats(multi['similarities'])
                
                stats_table = Table(title=" ", box=box.ROUNDED)
                stats_table.add_column("", style="cyan")
                stats_table.add_column(" ", style="green")
                stats_table.add_column(" ", style="yellow")
                
                stats_table.add_row("", f"{single_stats['mean']:.3f}", f"{multi_stats['mean']:.3f}")
                stats_table.add_row("", f"{single_stats['median']:.3f}", f"{multi_stats['median']:.3f}")
                stats_table.add_row("", f"{single_stats['max']:.3f}", f"{multi_stats['max']:.3f}")
                stats_table.add_row("", f"{single_stats['min']:.3f}", f"{multi_stats['min']:.3f}")
                stats_table.add_row("", f"{single_stats['stdev']:.3f}", f"{multi_stats['stdev']:.3f}")
                
                console.print(stats_table)
                
                #   
                dist_table = Table(title="  ", box=box.ROUNDED)
                dist_table.add_column("", style="cyan")
                dist_table.add_column(" ", style="green")
                dist_table.add_column(" ", style="yellow")
                
                for range_key in ['0.0-0.3', '0.3-0.5', '0.5-0.7', '0.7-1.0']:
                    dist_table.add_row(
                        range_key,
                        str(single_stats['ranges'].get(range_key, 0)),
                        str(multi_stats['ranges'].get(range_key, 0))
                    )
                
                console.print(dist_table)
            
            #  
            if multi.get('agency_recommendation'):
                agency_info = multi['agency_recommendation']
                if isinstance(agency_info, dict) and 'formatted' in agency_info:
                    console.print(Panel(
                        agency_info['formatted'],
                        title=" ",
                        border_style="yellow"
                    ))
                elif isinstance(agency_info, dict) and 'top_agency' in agency_info:
                    top_agency = agency_info['top_agency']
                    if top_agency:
                        console.print(Panel(
                            f" : {top_agency[0]}\n: {top_agency[1]:.3f}",
                            title=" ",
                            border_style="yellow"
                        ))
            
            #   ()
            if detailed:
                console.print("\n[bold]  :[/bold]")
                console.print("\n[bold green]   5:[/bold green]")
                for i, chunk in enumerate(single['results'][:5], 1):
                    console.print(f"{i}. : {chunk.get('similarity', 0):.3f}")
                    console.print(f"   {chunk.get('content', '')[:100]}...")
                
                console.print("\n[bold yellow]   :[/bold yellow]")
                if multi['results'].get('stage1', {}).get('law'):
                    console.print("\n[bold]Stage 1 - :[/bold]")
                    for chunk in multi['results']['stage1']['law'][:3]:
                        console.print(f"  - : {chunk.get('similarity', 0):.3f}")
                        console.print(f"    {chunk.get('content', '')[:80]}...")
                
                if multi['results'].get('stage2'):
                    console.print("\n[bold]Stage 2 - :[/bold]")
                    for chunk in multi['results']['stage2'][:3]:
                        console.print(f"  - : {chunk.get('similarity', 0):.3f}")
                        console.print(f"    {chunk.get('content', '')[:80]}...")
        else:
            #  
            print(f"\n{'='*80}")
            print(f" : {query}")
            print(f"{'='*80}\n")
            
            print("  :")
            print(f"   : ={single['count']}, ={multi['count']} (: {comp['result_count_diff']:+d})")
            print(f"   : ={single['elapsed_time']:.2f}, ={multi['elapsed_time']:.2f} (: {comp['time_diff']:+.2f})")
            print(f"   : ={comp['avg_similarity_single']:.3f}, ={comp['avg_similarity_multi']:.3f}")
            
            print("\n   :")
            print(f"  Stage 1 - : {multi['stage1_law']}")
            print(f"  Stage 1 - : {multi['stage1_criteria']}")
            print(f"  Stage 2 - : {multi['stage2']}")
            print(f"  Stage 3 - : {multi['stage3']}")
            print(f"  Fallback : {'' if multi['used_fallback'] else ''}")
            
            if single['similarities']:
                single_stats = self.calculate_similarity_stats(single['similarities'])
                multi_stats = self.calculate_similarity_stats(multi['similarities'])
                
                print("\n :")
                print(f"  : ={single_stats['mean']:.3f}, ={multi_stats['mean']:.3f}")
                print(f"  : ={single_stats['max']:.3f}, ={multi_stats['max']:.3f}")
                print(f"  : ={single_stats['min']:.3f}, ={multi_stats['min']:.3f}")
    
    def save_result(self, comparison_result: Dict, output_dir: str = "test_results"):
        """ JSON  """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rag_test_{timestamp}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(comparison_result, f, ensure_ascii=False, indent=2)
        
        if RICH_AVAILABLE:
            console.print(f"[bold green]  : {filepath}[/bold green]")
        else:
            print(f"  : {filepath}")
        
        return filepath
    
    def export_to_csv(self, results: List[Dict], output_file: str = "rag_test_comparison.csv"):
        """  CSV """
        if not results:
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 
            writer.writerow([
                '', '',
                '_', '_', '_',
                '_', '_', '_',
                '_', '_', '_',
                'Stage1_', 'Stage1_', 'Stage2', 'Stage3', 'Fallback'
            ])
            
            # 
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
                    '' if multi['used_fallback'] else ''
                ])
        
        if RICH_AVAILABLE:
            console.print(f"[bold green] CSV  : {output_file}[/bold green]")
        else:
            print(f" CSV  : {output_file}")


def show_menu():
    """ """
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]RAG   [/bold cyan]")
        console.print("\n[bold]:[/bold]")
        console.print("  1.    ( )")
        console.print("  2.    ")
        console.print("  3.   ")
        console.print("  4.  /")
        console.print("  5. ")
    else:
        print("\nRAG   ")
        print("\n:")
        print("  1.    ( )")
        print("  2.    ")
        print("  3.   ")
        print("  4.  /")
        print("  5. ")


def main():
    """ """
    #  
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    #  
    tester = InteractiveRAGTester(db_config)
    
    try:
        while True:
            show_menu()
            choice = input("\n (1-5): ").strip()
            
            if choice == '1':
                #    ( )
                query = input("\n  : ").strip()
                if not query:
                    print(" .")
                    continue
                
                detailed = input("  ? (y/n): ").strip().lower() == 'y'
                
                if RICH_AVAILABLE:
                    with console.status("[bold green] ...") as status:
                        comparison_result = tester.compare_searches(query)
                else:
                    print(" ...")
                    comparison_result = tester.compare_searches(query)
                
                tester.display_results(comparison_result, detailed=detailed)
                
                #  
                test_history.append(comparison_result)
                
                save = input("\n ? (y/n): ").strip().lower() == 'y'
                if save:
                    tester.save_result(comparison_result)
            
            elif choice == '2':
                #    
                query = input("\n  : ").strip()
                if not query:
                    print(" .")
                    continue
                
                if RICH_AVAILABLE:
                    with console.status("[bold green]   ...") as status:
                        result = tester.test_multi_stage_search(query)
                else:
                    print("   ...")
                    result = tester.test_multi_stage_search(query)
                
                if RICH_AVAILABLE:
                    console.print(f"\n[bold] :[/bold]")
                    console.print(f"  : {result['count']}")
                    console.print(f" : {result['elapsed_time']:.2f}")
                    console.print(f"Stage 1 - : {result['stage1_law']}")
                    console.print(f"Stage 1 - : {result['stage1_criteria']}")
                    console.print(f"Stage 2: {result['stage2']}")
                    console.print(f"Stage 3: {result['stage3']}")
                else:
                    print(f"\n :")
                    print(f"  : {result['count']}")
                    print(f" : {result['elapsed_time']:.2f}")
                    print(f"Stage 1 - : {result['stage1_law']}")
                    print(f"Stage 1 - : {result['stage1_criteria']}")
                    print(f"Stage 2: {result['stage2']}")
                    print(f"Stage 3: {result['stage3']}")
            
            elif choice == '3':
                #   
                if not test_history:
                    if RICH_AVAILABLE:
                        console.print("[yellow] .[/yellow]")
                    else:
                        print(" .")
                    continue
                
                if RICH_AVAILABLE:
                    console.print(f"\n[bold] ({len(test_history)}):[/bold]")
                    for i, result in enumerate(test_history, 1):
                        console.print(f"{i}. {result['query'][:50]}...")
                        console.print(f"   : {result['single']['count']}, "
                                    f": {result['multi']['count']}")
                else:
                    print(f"\n ({len(test_history)}):")
                    for i, result in enumerate(test_history, 1):
                        print(f"{i}. {result['query'][:50]}...")
                        print(f"   : {result['single']['count']}, "
                              f": {result['multi']['count']}")
            
            elif choice == '4':
                #  /
                if not test_history:
                    if RICH_AVAILABLE:
                        console.print("[yellow]  .[/yellow]")
                    else:
                        print("  .")
                    continue
                
                print("\n :")
                print("  1. JSON  ( )")
                print("  2. CSV  ( )")
                
                save_choice = input(" (1-2): ").strip()
                
                if save_choice == '1':
                    for result in test_history:
                        tester.save_result(result)
                elif save_choice == '2':
                    output_file = input("CSV  (: rag_test_comparison.csv): ").strip()
                    if not output_file:
                        output_file = "rag_test_comparison.csv"
                    tester.export_to_csv(test_history, output_file)
            
            elif choice == '5':
                # 
                if RICH_AVAILABLE:
                    console.print("[bold green] .[/bold green]")
                else:
                    print(" .")
                break
            
            else:
                if RICH_AVAILABLE:
                    console.print("[red] .[/red]")
                else:
                    print(" .")
    
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print("\n[yellow] .[/yellow]")
        else:
            print("\n .")
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red] : {e}[/bold red]")
        else:
            print(f" : {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.close()


if __name__ == "__main__":
    main()
