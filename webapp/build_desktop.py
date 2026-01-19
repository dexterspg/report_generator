#!/usr/bin/env python3
"""
Build script for CTR Mapper Desktop Application (Combined Version)

This script creates a standalone executable using PyInstaller from the webapp code.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """Clean previous build artifacts"""
    print("Cleaning previous build artifacts...")
    
    # Remove build directories
    for dir_name in ['build', 'dist', '__pycache__']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Removed {dir_name}/")
    
    # Remove spec file
    spec_file = 'app.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Removed {spec_file}")


def ensure_frontend_built():
    """Ensure frontend is built"""
    frontend_dist = Path("../frontend-dist")
    if not frontend_dist.exists():
        print("Frontend not built. Building now...")
        try:
            subprocess.run(["npm", "run", "build"], cwd="../frontend-vue", check=True)
            print("✓ Frontend built successfully")
        except subprocess.CalledProcessError:
            print("✗ Failed to build frontend. Please run 'npm run build' in frontend-vue/")
            return False
    return True


def create_executable():
    """Create the executable using PyInstaller"""
    print("Creating executable with PyInstaller...")
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onedir',                         # Create directory distribution (better compatibility)
        '--console',                        # Show console window for debugging
        '--name=CTR_Mapper',               # Executable name
        '--add-data=../frontend-dist;frontend-dist',  # Include frontend
        '--add-data=services;services',     # Include services
        '--add-data=models;models',         # Include models
        '--hidden-import=pandas',           # Ensure pandas is included
        '--hidden-import=openpyxl',         # Ensure openpyxl is included
        '--hidden-import=numpy',            # Ensure numpy is included
        '--hidden-import=fastapi',          # Ensure fastapi is included
        '--hidden-import=uvicorn',          # Ensure uvicorn is included
        '--hidden-import=pydantic',         # Ensure pydantic is included
        '--hidden-import=uvicorn.workers',  # Include uvicorn workers
        '--hidden-import=uvicorn.protocols', # Include uvicorn protocols
        '--hidden-import=uvicorn.lifespan',  # Include uvicorn lifespan
        '--hidden-import=multipart',        # For file uploads
        '--hidden-import=starlette',        # FastAPI dependency
        '--hidden-import=email_validator',  # Pydantic dependency
        '--collect-all=fastapi',            # Collect all fastapi modules
        '--collect-all=uvicorn',            # Collect all uvicorn modules
        '--collect-all=pydantic',           # Collect all pydantic modules
        '--collect-all=starlette',          # Collect all starlette modules
        '--collect-all=pandas',             # Collect all pandas modules
        '--collect-all=openpyxl',           # Collect all openpyxl modules
        '--collect-all=numpy',              # Collect all numpy modules
        '--noconfirm',                      # Don't ask for confirmation
        '--clean',                          # Clean cache
        'app.py',                           # Main script
        '--',                               # Pass arguments to script
        '--desktop'                         # Run in desktop mode
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Executable created successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error creating executable: {e}")
        return False
    except FileNotFoundError:
        print("✗ PyInstaller not found. Please install it with: pip install pyinstaller")
        return False


def create_installer_package():
    """Create installer package structure"""
    print("Creating installer package...")
    
    # Create package directory
    package_dir = 'CTR_Mapper_Desktop_Package'
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    
    os.makedirs(package_dir)
    
    # Copy executable directory
    if os.path.exists('dist/CTR_Mapper'):
        shutil.copytree('dist/CTR_Mapper', os.path.join(package_dir, 'CTR_Mapper'))
    else:
        print("✗ Executable directory not found in dist/")
        return False
    
    # Create README
    readme_content = """
CTR Mapper Desktop Application
==============================

Installation:
1. Extract this folder to your desired location
2. Navigate to the CTR_Mapper folder
3. Run CTR_Mapper.exe

Usage:
- The application will open in your default web browser
- Upload your Excel files through the web interface
- Download the processed poliza ledger files

Features:
- Self-contained: No need to install Python or dependencies
- Local processing: Your files stay on your computer
- Same interface as the web version
- Automatic cleanup of temporary files

Requirements:
- Windows 10 or later
- Microsoft Visual C++ Redistributable (usually already installed)
- No additional software installation required

Troubleshooting:
- If the application doesn't start, try running as administrator
- Make sure Windows Defender or antivirus isn't blocking the executable
- If you get a "missing DLL" error, install Microsoft Visual C++ Redistributable
- For file upload errors, check that the Excel file is not password-protected

Support:
- For technical support, contact your system administrator
"""
    
    with open(os.path.join(package_dir, 'README.txt'), 'w') as f:
        f.write(readme_content)
    
    print(f"✓ Package created in {package_dir}/")
    return True


def main():
    """Main build process"""
    print("=" * 60)
    print("CTR Mapper Desktop Build Script (Combined Version)")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('backend/app.py'):
        print("✗ backend/app.py not found. Please run this script from the webapp/ directory")
        return 1
    
    # Change to backend directory for PyInstaller
    os.chdir('backend')
    
    # Check if frontend is built
    if not ensure_frontend_built():
        return 1
    
    # Check if required dependencies are installed
    try:
        import PyInstaller
    except ImportError:
        print("✗ PyInstaller not installed. Installing...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        except subprocess.CalledProcessError:
            print("✗ Failed to install PyInstaller")
            return 1
    
    # Build process
    try:
        clean_build()
        
        if not create_executable():
            return 1
        
        if not create_installer_package():
            return 1
        
        print("\n" + "=" * 60)
        print("✓ Build completed successfully!")
        print("✓ Executable: dist/CTR_Mapper/")
        print("✓ Package: CTR_Mapper_Desktop_Package/")
        print("\nTo test:")
        print("  python app.py --desktop")
        print("\nTo distribute:")
        print("  Zip the CTR_Mapper_Desktop_Package folder")
        print("  Recipients need to extract and run CTR_Mapper/CTR_Mapper.exe")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n✗ Build interrupted by user")
        return 1
    except Exception as e:
        print(f"✗ Build failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())