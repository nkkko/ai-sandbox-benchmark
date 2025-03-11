"""
Utility functions for the AI Sandbox Benchmark providers.
"""
import importlib
import re
import sys
from typing import List, Set, Optional, Dict, Any

def is_standard_library(module_name: str) -> bool:
    """
    Check if a module is part of the Python standard library.
    
    Args:
        module_name: The name of the module to check
        
    Returns:
        bool: True if the module is part of the standard library, False otherwise
    """
    # Standard approach to detect standard library modules
    try:
        path = getattr(importlib.import_module(module_name), "__file__", "")
        return path and ("site-packages" not in path and "dist-packages" not in path)
    except (ImportError, AttributeError):
        # If import fails, we'll assume it's not a standard library
        return False

def extract_imports(code: str) -> Set[str]:
    """
    Extract import module names from Python code.
    
    Args:
        code: The Python code to scan for imports
        
    Returns:
        Set[str]: A set of imported module names
    """
    imports = set()
    
    # Check for base64 encoded content
    base64_pattern = r'__import__\("base64"\)\.b64decode\("([^"]+)"\)'
    base64_matches = re.findall(base64_pattern, code)
    
    # Decode any base64 content and extract imports from it too
    for match in base64_matches:
        try:
            import base64
            decoded_code = base64.b64decode(match).decode('utf-8')
            # Recursively extract imports from the decoded content
            decoded_imports = extract_imports(decoded_code)
            imports.update(decoded_imports)
        except Exception as e:
            print(f"Warning: Failed to decode base64 content: {e}")
    
    # This regex pattern captures both 'import x' and 'from x import y' style imports
    pattern = r'^(?:from|import)\s+([a-zA-Z0-9_]+)'
    
    for line in code.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            imports.add(match.group(1))
    
    return imports

def check_and_install_dependencies(
    code: str,
    provider_context: Optional[Dict[str, Any]] = None,
    always_install: Optional[List[str]] = None
) -> List[str]:
    """
    Check for dependencies in the code and install missing packages.
    
    Args:
        code: The Python code to analyze
        provider_context: Optional provider-specific context for customization
        always_install: List of packages to always install regardless of imports
        
    Returns:
        List[str]: List of packages that were installed
    """
    import subprocess
    
    installed_packages = []
    
    # Install packages that should always be available
    if always_install:
        for package in always_install:
            try:
                importlib.import_module(package)
                print(f"Package {package} is already installed.")
            except ImportError:
                print(f"Installing required package: {package}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                installed_packages.append(package)
    
    # Extract imports from the code
    imports = extract_imports(code)
    
    # Filter out standard library modules
    third_party_modules = {
        module for module in imports if not is_standard_library(module)
    }
    
    # Check each third-party module and install if missing
    for module in third_party_modules:
        try:
            importlib.import_module(module)
            print(f"Module {module} is already installed.")
        except ImportError:
            print(f"Installing missing dependency: {module}")
            # Use pip to install the package
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])
            installed_packages.append(module)
    
    return installed_packages