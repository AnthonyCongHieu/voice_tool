"""
Helper script to locate CUDA DLL files for bundling with PyInstaller
"""
import os
import sys
from pathlib import Path

def find_cuda_dlls():
    """Find CUDA DLL files in PyTorch installation"""
    cuda_dlls = []
    
    try:
        import torch
        torch_lib_path = Path(torch.__file__).parent / "lib"
        
        if not torch_lib_path.exists():
            print(f"[WARN] PyTorch lib directory not found: {torch_lib_path}")
            return cuda_dlls
        
        print(f"[INFO] Searching for CUDA DLLs in: {torch_lib_path}")
        
        # Required CUDA DLL files for GPU acceleration
        required_dlls = [
            "cublas64_12.dll",
            "cublasLt64_12.dll",
            "cudnn64_9.dll",
            "cudnn_ops64_9.dll", 
            "cudnn_cnn64_9.dll",
            "cudart64_12.dll",
            "nvrtc64_120_0.dll",
            "nvrtc-builtins64_120.dll"
        ]
        
        for dll_name in required_dlls:
            dll_path = torch_lib_path / dll_name
            if dll_path.exists():
                size_mb = dll_path.stat().st_size / (1024 * 1024)
                cuda_dlls.append((str(dll_path), '.'))
                print(f"  [OK] Found: {dll_name} ({size_mb:.2f} MB)")
            else:
                print(f"  [SKIP] Missing: {dll_name}")

        
        print(f"\n[INFO] Total DLLs found: {len(cuda_dlls)}")
        
    except ImportError:
        print("[ERROR] PyTorch not installed")
    except Exception as e:
        print(f"[ERROR] Failed to locate CUDA DLLs: {e}")
    
    return cuda_dlls

if __name__ == "__main__":
    dlls = find_cuda_dlls()
    
    if dlls:
        print("\n[SUCCESS] CUDA DLLs ready for bundling")
        print("\nPyInstaller binaries format:")
        print("binaries = [")
        for dll_path, dest in dlls:
            print(f"    (r'{dll_path}', '{dest}'),")
        print("]")
    else:
        print("\n[WARN] No CUDA DLLs found - GPU acceleration may not work")
        sys.exit(1)
