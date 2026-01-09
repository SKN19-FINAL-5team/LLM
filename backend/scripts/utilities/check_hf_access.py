"""
HuggingFace   
naver/splade-v3     
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

#   
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = Path(__file__).parent.parent.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# HuggingFace  
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')


def check_hf_access():
    """HuggingFace   """
    print("=" * 80)
    print("HuggingFace  ")
    print("=" * 80)
    
    model_name = "naver/splade-v3"
    print(f"\n : {model_name}")
    
    #  
    if HF_TOKEN:
        print(f" HF_TOKEN    (: {len(HF_TOKEN)})")
        os.environ['HF_TOKEN'] = HF_TOKEN
    else:
        print("  HF_TOKEN   ")
        print("       (   )")
    
    # transformers  
    try:
        from transformers import AutoModelForMaskedLM, AutoTokenizer
        print(" transformers  ")
    except ImportError:
        print(" transformers   .")
        print("   : pip install transformers torch")
        return False
    
    #   
    print(f"\n    ...")
    try:
        from transformers import AutoTokenizer
        
        #    ()
        print("  1.   ...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            token=HF_TOKEN if HF_TOKEN else None
        )
        print("     !")
        
        #  
        test_text = " 750 "
        tokens = tokenizer(test_text, return_tensors="pt")
        print(f"      ( : {tokens['input_ids'].shape[1]})")
        
        #   
        print("\n  2.   ...")
        try:
            from huggingface_hub import model_info
            info = model_info(model_name, token=HF_TOKEN if HF_TOKEN else None)
            print(f"    :")
            print(f"     - ID: {info.id}")
            print(f"     -  : {info.private == False}")
            if hasattr(info, 'tags'):
                print(f"     - : {', '.join(info.tags[:5])}")
        except ImportError:
            print("    huggingface_hub  (  )")
        except Exception as e:
            print(f"      : {e}")
        
        #     ()
        print("\n  3.     ()...")
        try:
            import torch
            from transformers import AutoModelForMaskedLM
            
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"     : {device}")
            
            model = AutoModelForMaskedLM.from_pretrained(
                model_name,
                token=HF_TOKEN if HF_TOKEN else None
            )
            model.to(device)
            model.eval()
            print("     !")
            
            #   
            print("  4.  ...")
            with torch.no_grad():
                inputs = tokenizer(test_text, return_tensors="pt").to(device)
                outputs = model(**inputs)
                print(f"      ( shape: {outputs.logits.shape})")
            
            print("\n" + "=" * 80)
            print(" HuggingFace   !")
            print("=" * 80)
            if not HF_TOKEN:
                print("\n :     ( ).")
            return True
            
        except Exception as e:
            print(f"      : {e}")
            if "401" in str(e) or "Unauthorized" in str(e):
                print("\n  :  .")
                print("\n  :")
                print("  1. HuggingFace  : https://huggingface.co/join")
                print("  2.  : Settings > Access Tokens > New token")
                print("  3. .env  : HF_TOKEN=your_token_here")
                return False
            else:
                print(f"\n    : {e}")
                print("          .")
                return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n  : {error_msg}")
        
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("\n  :  .")
            print("\n  :")
            print("  1. HuggingFace  : https://huggingface.co/join")
            print("  2.  : Settings > Access Tokens > New token")
            print("  3. .env  : HF_TOKEN=your_token_here")
            return False
        elif "404" in error_msg or "not found" in error_msg.lower():
            print("\n    .")
            print(f"    : {model_name}")
            return False
        else:
            print(f"\n    : {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = check_hf_access()
    sys.exit(0 if success else 1)
