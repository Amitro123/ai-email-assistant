"""
Pre-submission tests to verify all components work correctly.
Run this before creating the ZIP file.
"""

import os
import sys
from pathlib import Path


def check_file_exists(filepath, required=True):
    """Check if file exists"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {filepath}")
    return exists


def check_file_not_exists(filepath):
    """Check if file does NOT exist (security)"""
    exists = os.path.exists(filepath)
    status = "✅" if not exists else "❌ REMOVE THIS!"
    print(f"{status} {filepath}")
    return not exists


def check_imports():
    """Verify required packages are installed"""
    print("\n📦 Checking Python packages...")
    required = [
        'google.auth',
        'googleapiclient',
        'openai',
        'dotenv',
        'reflex'
    ]
    
    all_good = True
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Run: pip install -r requirements.txt")
            all_good = False
    
    return all_good


def main():
    print("=" * 60)
    print("🔍 PRE-SUBMISSION VERIFICATION")
    print("=" * 60)
    
    # Check required files
    print("\n✅ Required Files:")
    required_files = [
        'main.py',
        'gmail_handler.py',
        'llm_handler.py',
        'config.py',
        'web_ui.py',
        'rxconfig.py',
        'requirements.txt',
        'README.md',
        '.env.example',
        '.gitignore'
    ]
    
    all_required = all(check_file_exists(f) for f in required_files)
    
    # Check files that MUST NOT exist
    print("\n❌ Files That MUST NOT Be Present:")
    forbidden_files = [
        'credentials.json',
        'token.json',
        '.env'
    ]
    
    no_forbidden = all(check_file_not_exists(f) for f in forbidden_files)
    
    # Check directories that should not exist
    print("\n📁 Directories That Should Be Removed:")
    forbidden_dirs = [
        'venv',
        '__pycache__',
        '.web',
        'assets'
    ]
    
    no_forbidden_dirs = all(check_file_not_exists(d) for d in forbidden_dirs)
    
    # Check packages
    packages_ok = check_imports()
    
    # Final verdict
    print("\n" + "=" * 60)
    if all_required and no_forbidden and no_forbidden_dirs and packages_ok:
        print("✅ ALL CHECKS PASSED - READY FOR SUBMISSION!")
    else:
        print("❌ SOME CHECKS FAILED - FIX ISSUES BEFORE SUBMISSION")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
