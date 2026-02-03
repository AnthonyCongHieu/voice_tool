"""
Download minimal CUDA 12.x DLLs needed for GPU acceleration
This downloads only the required DLLs (~50MB) instead of full CUDA Toolkit (~3GB)
"""
import os
import sys
import urllib.request
from pathlib import Path

# CUDA DLLs download URLs (NVIDIA redistributables)
# These are direct links to minimal DLL packages
CUDA_DLLS = {
    # cuBLAS - Required for GPU matrix operations
    "cublas64_12.dll": "https://developer.download.nvidia.com/compute/cuda/redist/libcublas/windows-x86_64/libcublas-windows-x86_64-12.1.3.1-archive.zip",
    
    # CUDA Runtime - Required for GPU operations
    "cudart64_12.dll": "https://developer.download.nvidia.com/compute/cuda/redist/cuda_runtime/windows-x86_64/cuda_runtime-windows-x86_64-12.1.105-archive.zip",
}

# Manual download guide for all required DLLs
MANUAL_GUIDE = """
================================================================
CUDA DLL Manual Download Guide
================================================================

Since automatic download requires extracting from archives, 
please follow these steps to get the DLLs:

OPTION 1: Download from PyTorch Wheels (Easiest)
------------------------------------------------
1. Download this pre-built CUDA DLL package:
   https://github.com/Purfview/whisper-standalone-win/releases
   
2. Extract and copy these DLLs to cuda_dlls folder:
   - cublas64_12.dll
   - cublasLt64_12.dll  
   - cudart64_12.dll

OPTION 2: Extract from NVIDIA CUDA Toolkit Installer
-----------------------------------------------------
1. Download NVIDIA CUDA 12.1 Toolkit:
   https://developer.nvidia.com/cuda-12-1-0-download-archive
   
2. Run installer but ONLY select "Developer > Libraries"
   (Uncheck everything else to save space)
   
3. After install, copy DLLs from:
   C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.1\\bin\\
   
   To: cuda_dlls\\ in this project folder
   
4. You can uninstall CUDA Toolkit after copying DLLs

OPTION 3: Use Existing PyTorch CUDA Installation
-------------------------------------------------
If you have PyTorch with CUDA already installed, copy from:
   <python>\\Lib\\site-packages\\torch\\lib\\

Required DLLs (Total ~50MB):
  - cublas64_12.dll      (~120MB - cuBLAS library)
  - cublasLt64_12.dll    (~120MB - cuBLAS LT library)  
  - cudart64_12.dll      (~0.5MB - CUDA runtime)

Optional (for better performance):
  - cudnn64_9.dll        (~700MB - cuDNN library)
  - nvrtc64_120_0.dll    (~30MB - Runtime compiler)

================================================================
After getting the DLLs, place them in: cuda_dlls\\
Then run: build.bat to rebuild with CUDA support
================================================================
"""

def create_cuda_folder():
    """Create cuda_dlls folder if not exists"""
    cuda_dir = Path("cuda_dlls")
    if not cuda_dir.exists():
        cuda_dir.mkdir()
        print(f"[OK] Created folder: {cuda_dir}")
    else:
        print(f"[OK] Folder exists: {cuda_dir}")
    return cuda_dir

def check_existing_dlls(cuda_dir):
    """Check if DLLs already exist"""
    required_dlls = ["cublas64_12.dll", "cublasLt64_12.dll", "cudart64_12.dll"]
    found = []
    
    for dll in required_dlls:
        dll_path = cuda_dir / dll
        if dll_path.exists():
            size_mb = dll_path.stat().st_size / (1024 * 1024)
            found.append(dll)
            print(f"  [OK] Found: {dll} ({size_mb:.1f} MB)")
        else:
            print(f"  [MISS] Not found: {dll}")
    
    return len(found), len(required_dlls)

def main():
    print("=" * 60)
    print("  CUDA DLL Downloader for Voice AI Pro")
    print("=" * 60)
    print()
    
    # Create folder
    cuda_dir = create_cuda_folder()
    
    print()
    print("[INFO] Checking for existing DLLs...")
    found_count, total_count = check_existing_dlls(cuda_dir)
    
    print()
    if found_count == total_count:
        print(f"[SUCCESS] All {total_count} required DLLs found!")
        print()
        print("Next step: Run build.bat to rebuild with CUDA support")
        return 0
    
    print(f"[INFO] Found {found_count}/{total_count} required DLLs")
    print()
    
    # Show manual guide
    print(MANUAL_GUIDE)
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
