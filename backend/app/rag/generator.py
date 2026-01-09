"""
RAG Generator Module
   LLM    
"""

import os
from typing import List, Dict
from openai import OpenAI


class RAGGenerator:
    """   LLM   """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Args:
            api_key: OpenAI API  (:  )
            model:  LLM  
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
    def format_context(self, chunks: List[Dict]) -> str:
        """
          LLM    
        
        Args:
            chunks:   
            
        Returns:
              
        """
        if not chunks:
            return "    ."
        
        context_parts = []
        
        for idx, chunk in enumerate(chunks, 1):
            case_info = f"[ {idx}]"
            if chunk.get('case_no'):
                case_info += f" : {chunk['case_no']}"
            if chunk.get('decision_date'):
                case_info += f", : {chunk['decision_date']}"
            if chunk.get('agency'):
                agency_name = {
                    'kca': '',
                    'ecmc': '',
                    'kcdrc': ''
                }.get(chunk['agency'], chunk['agency'])
                case_info += f", : {agency_name}"
            
            chunk_type_name = {
                'decision': '()',
                'parties_claim': '( )',
                'judgment': '( )'
            }.get(chunk['chunk_type'], chunk['chunk_type'])
            
            context_parts.append(
                f"{case_info}\n"
                f"[{chunk_type_name}]\n"
                f"{chunk['text']}\n"
                f"(: {chunk.get('similarity', 0):.3f})\n"
            )
        
        return "\n".join(context_parts)
    
    def generate_answer(
        self, 
        query: str, 
        chunks: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Dict:
        """
            
        
        Args:
            query:  
            chunks:   
            temperature: LLM   (0~1,  )
            max_tokens:    
            
        Returns:
                
        """
        #  
        context = self.format_context(chunks)
        
        #  
        system_prompt = """     . 
 " "        .

**  :**
1.       .
2.       .
3.   ,  ,    .
4.     .
5.     ,  "      " ."""

        #  
        user_prompt = f"""[ ]
{context}

[ ]
{query}

       ."""

        # LLM 
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            return {
                'answer': answer,
                'model': self.model,
                'chunks_used': len(chunks),
                'context': context,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {
                'answer': f"    : {str(e)}",
                'model': self.model,
                'chunks_used': len(chunks),
                'context': context,
                'error': str(e)
            }
    
    def generate_answer_stream(
        self, 
        query: str, 
        chunks: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 1000
    ):
        """
            ( )
        
        Args:
            query:  
            chunks:   
            temperature: LLM  
            max_tokens:    
            
        Yields:
              
        """
        context = self.format_context(chunks)
        
        system_prompt = """     . 
 " "        .

**  :**
1.       .
2.       .
3.   ,  ,    .
4.     ."""

        user_prompt = f"""[ ]
{context}

[ ]
{query}

       ."""

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n[]     : {str(e)}"
    
    def format_multi_method_context(self, method_results: Dict) -> str:
        """
            LLM    
        
        Args:
            method_results: MultiMethodRetriever.search_all_methods() 
        
        Returns:
              
        """
        context_parts = []
        
        for method_name, method_data in method_results.get('methods', {}).items():
            if not method_data.get('success', False):
                continue
            
            results = method_data.get('results', [])
            if not results:
                continue
            
            context_parts.append(f"\n{'='*80}")
            context_parts.append(f"[{method_name.upper()}  ]")
            context_parts.append(f"  : {len(results)}")
            context_parts.append(f" : {method_data.get('elapsed_time', 0):.3f}")
            context_parts.append(f"{'='*80}\n")
            
            for idx, result in enumerate(results[:5], 1):  #  5 
                case_info = f"[{method_name.upper()}  {idx}]"
                if result.get('case_no'):
                    case_info += f" : {result['case_no']}"
                if result.get('decision_date'):
                    case_info += f", : {result['decision_date']}"
                if result.get('agency'):
                    agency_name = {
                        'kca': '',
                        'ecmc': '',
                        'kcdrc': ''
                    }.get(result['agency'], result['agency'])
                    case_info += f", : {agency_name}"
                
                chunk_type_name = {
                    'decision': '()',
                    'parties_claim': '( )',
                    'judgment': '( )'
                }.get(result.get('chunk_type', ''), result.get('chunk_type', 'N/A'))
                
                score = result.get('score', 0.0)
                source = result.get('source', 'N/A')
                
                context_parts.append(
                    f"{case_info}\n"
                    f": {source},  : {chunk_type_name}\n"
                    f": {score:.4f}\n"
                    f": {result.get('text', '')[:500]}\n"
                )
        
        if not context_parts:
            return "    ."
        
        return "\n".join(context_parts)
    
    def generate_comparative_answer(
        self,
        query: str,
        method_results: Dict,
        temperature: float = 0.3,
        max_tokens: int = 1500
    ) -> Dict:
        """
                
        
        Args:
            query:  
            method_results: MultiMethodRetriever.search_all_methods() 
            temperature: LLM  
            max_tokens:    
        
        Returns:
                
        """
        #  
        context = self.format_multi_method_context(method_results)
        
        #   
        method_summary = []
        for method_name, method_data in method_results.get('methods', {}).items():
            if method_data.get('success', False):
                method_summary.append(
                    f"- {method_name.upper()}: {method_data.get('count', 0)}  "
                    f"({method_data.get('elapsed_time', 0):.3f})"
                )
            else:
                method_summary.append(
                    f"- {method_name.upper()}:  ({method_data.get('error', 'Unknown error')})"
                )
        
        method_summary_text = "\n".join(method_summary)
        
        #  
        system_prompt = """     . 
 " "   (cosine similarity, BM25, SPLADE, hybrid search)    .

**  :**
1.           .
2.       .
3.       .
4.       .
5.   ,  ,    .
6.     .
7.          .
8.     ,  "      " .

** :**
1.      
2.       
3.    ( ,  )"""

        #  
        user_prompt = f"""[  ]
{method_summary_text}

[ ]
{context}

[ ]
{query}

         ,     ."""

        # LLM 
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            return {
                'answer': answer,
                'model': self.model,
                'query': query,
                'methods_used': list(method_results.get('methods', {}).keys()),
                'total_results': sum(
                    m.get('count', 0) 
                    for m in method_results.get('methods', {}).values()
                ),
                'context': context,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {
                'answer': f"    : {str(e)}",
                'model': self.model,
                'query': query,
                'methods_used': list(method_results.get('methods', {}).keys()),
                'total_results': 0,
                'context': context,
                'error': str(e)
            }