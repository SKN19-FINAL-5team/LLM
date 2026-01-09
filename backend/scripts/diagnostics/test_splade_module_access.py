"""
SPLADE      
torch , sentence-transformers,      
"""

import sys
import os
from pathlib import Path

#    
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_torch():
    """torch   CUDA """
    print("=" * 80)
    print("1. PyTorch ")
    print("=" * 80)
    try:
        import torch
        version = torch.__version__
        print(f" torch : {version}")
        
        #  
        try:
            major, minor = map(int, version.split('.')[:2])
            if major < 2 or (major == 2 and minor < 6):
                print(f"  torch  2.6  (: {version})")
                print("   SPLADE    torch.load      .")
                return False, version
            else:
                print(f" torch  2.6  (: {version})")
                return True, version
        except:
            print(f"  torch   : {version}")
            return False, version
        
    except ImportError:
        print(" torch  .")
        return False, None

def test_cuda():
    """CUDA    """
    print("\n" + "=" * 80)
    print("2. CUDA ")
    print("=" * 80)
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"CUDA  : {cuda_available}")
        
        if cuda_available:
            print(f"CUDA : {torch.version.cuda}")
            print(f"GPU : {torch.cuda.device_count()}")
            if torch.cuda.device_count() > 0:
                print(f"GPU : {torch.cuda.get_device_name(0)}")
        else:
            print("  GPU   . CPU  .")
        
        return cuda_available
    except ImportError:
        print(" torch   CUDA   .")
        return False

def test_sentence_transformers():
    """sentence-transformers  """
    print("\n" + "=" * 80)
    print("3. sentence-transformers ")
    print("=" * 80)
    try:
        import sentence_transformers
        version = sentence_transformers.__version__
        print(f" sentence-transformers : {version}")
        
        #  
        try:
            major = int(version.split('.')[0])
            if major < 5:
                print(f"  sentence-transformers  5.0.0  (: {version})")
                print("   SparseEncoder   .")
                return False, version
            else:
                print(f" sentence-transformers  5.0.0  (: {version})")
                return True, version
        except:
            print(f"    : {version}")
            return False, version
    except ImportError:
        print(" sentence-transformers  .")
        return False, None

def test_sparse_encoder():
    """SparseEncoder import """
    print("\n" + "=" * 80)
    print("4. SparseEncoder Import ")
    print("=" * 80)
    try:
        from sentence_transformers import SparseEncoder
        print(" SparseEncoder import ")
        return True
    except ImportError as e:
        print(f" SparseEncoder import : {e}")
        return False
    except Exception as e:
        print(f" SparseEncoder import : {e}")
        return False

def test_transformers():
    """transformers  """
    print("\n" + "=" * 80)
    print("5. transformers ")
    print("=" * 80)
    try:
        import transformers
        version = transformers.__version__
        print(f" transformers : {version}")
        
        # PreTrainedModel import 
        try:
            from transformers import PreTrainedModel
            print(" PreTrainedModel import ")
            return True, version
        except ImportError as e:
            print(f" PreTrainedModel import : {e}")
            print("   transformers    .")
            return False, version
    except ImportError:
        print(" transformers  .")
        return False, None

def test_api_server():
    """API   """
    print("\n" + "=" * 80)
    print("6. SPLADE API   ")
    print("=" * 80)
    try:
        import requests
        from dotenv import load_dotenv
        
        #   
        backend_dir = Path(__file__).parent.parent
        env_file = backend_dir / '.env'
        if env_file.exists():
            load_dotenv(env_file)
        
        api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
        print(f"API URL: {api_url}")
        
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f" API    ({api_url})")
                data = response.json()
                print(f"   : {data.get('status', 'unknown')}")
                print(f"   : {data.get('device', 'unknown')}")
                return True
            else:
                print(f"  API    ( : {response.status_code})")
                return False
        except requests.exceptions.RequestException as e:
            print(f"  API   : {e}")
            print("   SSH    .")
            return False
    except ImportError:
        print("  requests   API   .")
        return None

def test_model_load():
    """     (   )"""
    print("\n" + "=" * 80)
    print("7.     ")
    print("=" * 80)
    
    # torch  
    torch_ok, torch_version = test_torch()
    if not torch_ok:
        print("  torch  2.6      .")
        print("       .")
        return False
    
    # SparseEncoder 
    if not test_sparse_encoder():
        print("  SparseEncoder      .")
        return False
    
    # HuggingFace  
    from dotenv import load_dotenv
    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file)
    
    HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')
    if not HF_TOKEN:
        print("  HF_TOKEN  .")
        print("        .")
    else:
        print(" HF_TOKEN  .")
    
    print("    (   )")
    return True

def main():
    """  """
    print("\n" + "=" * 80)
    print("SPLADE     ")
    print("=" * 80)
    print()
    
    results = {
        'torch': False,
        'cuda': False,
        'sentence_transformers': False,
        'sparse_encoder': False,
        'transformers': False,
        'api_server': None,
        'model_load': False
    }
    
    # 1. torch 
    results['torch'], torch_version = test_torch()
    
    # 2. CUDA 
    results['cuda'] = test_cuda()
    
    # 3. sentence-transformers 
    results['sentence_transformers'], st_version = test_sentence_transformers()
    
    # 4. SparseEncoder 
    results['sparse_encoder'] = test_sparse_encoder()
    
    # 5. transformers 
    results['transformers'], tf_version = test_transformers()
    
    # 6. API  
    results['api_server'] = test_api_server()
    
    # 7.     
    results['model_load'] = test_model_load()
    
    #  
    print("\n" + "=" * 80)
    print("  ")
    print("=" * 80)
    
    print(f"\n :")
    if results['torch']:
        print(f"  - torch ({torch_version})")
    if results['sentence_transformers']:
        print(f"  - sentence-transformers ({st_version})")
    if results['sparse_encoder']:
        print("  - SparseEncoder import")
    if results['transformers']:
        print(f"  - transformers ({tf_version})")
    if results['cuda']:
        print("  - CUDA  ")
    if results['api_server']:
        print("  - API  ")
    if results['model_load']:
        print("  -   ")
    
    print(f"\n  :")
    if not results['torch']:
        print("  - torch  2.6  (   )")
    if not results['sentence_transformers']:
        print("  - sentence-transformers  5.0.0  (SparseEncoder  )")
    if not results['sparse_encoder']:
        print("  - SparseEncoder import ")
    if not results['transformers']:
        print("  - transformers  ")
    if not results['cuda']:
        print("  - CUDA   (CPU  )")
    if results['api_server'] is False:
        print("  - API    (   )")
    if not results['model_load']:
        print("  -   ")
    
    #  
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    
    if not results['torch']:
        print("\n1. torch :")
        print("   pip install --upgrade torch>=2.6")
    
    if not results['sentence_transformers']:
        print("\n2. sentence-transformers :")
        print("   pip install --upgrade sentence-transformers>=5.0.0")
    
    if results['api_server'] is False:
        print("\n3. API  :")
        print("   - RunPod SPLADE API  ")
        print("   -  SSH  : ssh -L 8001:localhost:8000 [user]@[host] -p [port]")
        print("   -   torch>=2.6    ")
    
    if results['model_load']:
        print("\n SPLADE    !")
    else:
        print("\n  SPLADE    .")
        print("      .")
    
    return results

if __name__ == "__main__":
    main()
