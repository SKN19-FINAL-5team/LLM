#!/usr/bin/env python3
"""
SPLADE    
RunPod API         
"""

import os
import sys
from dotenv import load_dotenv

#    
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_api_server():
    """RunPod API   """
    print("=" * 60)
    print("1. RunPod API   ")
    print("=" * 60)
    
    try:
        import requests
        api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
        print(f"   API URL: {api_url}")
        
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"     !")
                print(f"   : {response.json()}")
                return True
            else:
                print(f"      ( : {response.status_code})")
                return False
        except requests.exceptions.ConnectionError:
            print(f"     : Connection refused")
            print(f"    SSH    :")
            print(f"      ssh -L 8001:localhost:8000 root@[IP] -p [] -N")
            return False
        except requests.exceptions.Timeout:
            print(f"      ")
            return False
        except Exception as e:
            print(f"    : {e}")
            return False
    except ImportError:
        print("     requests  : pip install requests")
        return False


def check_local_mode():
    """    """
    print("\n" + "=" * 60)
    print("2.     ")
    print("=" * 60)
    
    try:
        import torch
        torch_version = torch.__version__
        print(f"   PyTorch : {torch_version}")
        
        #  
        try:
            major, minor = map(int, torch_version.split('.')[:2])
            if major < 2 or (major == 2 and minor < 6):
                print(f"    torch  2.6 ")
                print(f"    : pip install --upgrade torch>=2.6")
                return False
            else:
                print(f"    torch  OK")
        except:
            print(f"     torch   ")
        
        # CUDA 
        cuda_available = torch.cuda.is_available()
        print(f"   CUDA  : {cuda_available}")
        if cuda_available:
            print(f"   GPU : {torch.cuda.device_count()}")
            print(f"   GPU : {torch.cuda.get_device_name(0)}")
        
        #  import 
        try:
            from splade.test_splade_naver import NaverSPLADEDBRetriever
            print(f"    NaverSPLADEDBRetriever import ")
            return True
        except ImportError as e:
            print(f"    NaverSPLADEDBRetriever import : {e}")
            return False
        except Exception as e:
            error_str = str(e)
            if "torch.load" in error_str or "torch>=2.6" in error_str:
                print(f"    torch  : {error_str}")
                return False
            else:
                print(f"       : {e}")
                return False
                
    except ImportError:
        print("    torch  ")
        return False


def check_environment():
    """  """
    print("\n" + "=" * 60)
    print("3.   ")
    print("=" * 60)
    
    load_dotenv()
    
    api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
    print(f"   SPLADE_API_URL: {api_url}")
    
    hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')
    if hf_token:
        print(f"   HF_TOKEN: {'' if hf_token else '  '} (: {len(hf_token) if hf_token else 0})")
    else:
        print(f"   HF_TOKEN:   ")
        print(f"       , RunPod API  ")


def check_modules():
    """  """
    print("\n" + "=" * 60)
    print("4.   ")
    print("=" * 60)
    
    modules = [
        ('requests', 'requests'),
        ('torch', 'torch'),
        ('sentence_transformers', 'sentence-transformers'),
        ('transformers', 'transformers'),
    ]
    
    for module_name, package_name in modules:
        try:
            __import__(module_name)
            print(f"    {package_name}")
        except ImportError:
            print(f"    {package_name} ( : pip install {package_name})")


def main():
    """  """
    print("\n" + "=" * 60)
    print("SPLADE   ")
    print("=" * 60)
    print()
    
    #   
    load_dotenv()
    
    #   
    api_ok = check_api_server()
    local_ok = check_local_mode()
    check_environment()
    check_modules()
    
    #  
    print("\n" + "=" * 60)
    print(" ")
    print("=" * 60)
    
    if api_ok:
        print(" RunPod API   ")
        print("       SPLADE .")
    elif local_ok:
        print("  RunPod API   ,    ")
        print("         SPLADE .")
        print("   (GPU     )")
    else:
        print(" SPLADE  ")
        print("\n :")
        if not api_ok:
            print("   1. SSH  :")
            print("      ssh -L 8001:localhost:8000 root@[RunPod_IP] -p [] -N")
            print("   2. RunPod API   :")
            print("      curl http://localhost:8000/health")
        if not local_ok:
            print("   3. torch  (   ):")
            print("      pip install --upgrade torch>=2.6")
    
    print()


if __name__ == "__main__":
    main()
