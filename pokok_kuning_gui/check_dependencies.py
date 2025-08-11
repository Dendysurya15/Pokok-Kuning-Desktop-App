#!/usr/bin/env python3
"""
Script untuk memverifikasi semua dependencies sebelum build
"""

import sys
import importlib
import subprocess

# List of required packages
REQUIRED_PACKAGES = [
    'PyQt5',
    'ultralytics', 
    'numpy',
    'PIL',
    'cv2',
    'geojson',
    'shapely',
    'fastkml',
    'geopandas',
    'tqdm',
    'torch',
    'torchvision',
]

def check_package(package_name):
    """Check if a package is installed and importable"""
    try:
        importlib.import_module(package_name)
        print(f"✅ {package_name} - OK")
        return True
    except ImportError as e:
        print(f"❌ {package_name} - MISSING ({e})")
        return False

def get_package_version(package_name):
    """Get version of installed package"""
    try:
        module = importlib.import_module(package_name)
        if hasattr(module, '__version__'):
            return module.__version__
        else:
            return "version unknown"
    except:
        return "not installed"

def install_missing_packages():
    """Install missing packages"""
    print("\nInstalling missing packages...")
    result = subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ All packages installed successfully")
        return True
    else:
        print(f"❌ Installation failed: {result.stderr}")
        return False

def main():
    print("🔍 Checking dependencies for Pokok Kuning Desktop App...")
    print("=" * 60)
    
    missing_packages = []
    
    # Check each required package
    for package in REQUIRED_PACKAGES:
        if not check_package(package):
            missing_packages.append(package)
    
    print("\n📋 Package Versions:")
    print("-" * 40)
    for package in REQUIRED_PACKAGES:
        version = get_package_version(package)
        print(f"{package}: {version}")
    
    # Summary
    print("\n📊 Summary:")
    print("-" * 40)
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        
        # Ask user if they want to install missing packages
        response = input("\nDo you want to install missing packages? (y/n): ")
        if response.lower() in ['y', 'yes']:
            if install_missing_packages():
                print("\n✅ All dependencies are now ready!")
                print("You can now run: python build_exe.py")
            else:
                print("\n❌ Failed to install dependencies")
                return False
        else:
            print("\n⚠️  Please install missing packages before building")
            print("Run: pip install -r requirements.txt")
            return False
    else:
        print("✅ All required packages are installed!")
        print("You can now run: python build_exe.py")
    
    # Check PyInstaller
    print("\n🔧 Checking build tools:")
    print("-" * 40)
    if check_package('PyInstaller'):
        print("✅ PyInstaller is ready")
    else:
        print("⚠️  PyInstaller not found - will be installed during build")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
