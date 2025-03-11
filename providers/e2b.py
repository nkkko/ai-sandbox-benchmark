# providers/e2b.py

import time, asyncio, logging, os
from typing import Dict, Any
from e2b_code_interpreter import Sandbox
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

async def execute(code: str, env_vars: Dict[str, str] = None):
    metrics = EnhancedTimingMetrics()
    try:
        start = time.time()
        sandbox = Sandbox()
        metrics.add_metric("Workspace Creation", time.time() - start)

        # Pass environment variables to the sandbox
        if env_vars and len(env_vars) > 0:
            env_var_code = "import os;\n"
            for key, value in env_vars.items():
                logger.info(f"Setting {key} in E2B sandbox")
                env_var_code += f"os.environ['{key}'] = '{value}';\n"
            
            sandbox.run_code(env_var_code)
        
        # Check and install dependencies
        logger.info("Checking for dependencies in code...")
        dependency_checker = """
import re, sys, subprocess

def extract_imports(code):
    # Extract all import statements
    import_pattern = re.compile(r'^(?:from|import)\s+([a-zA-Z0-9_]+)', re.MULTILINE)
    return set(import_pattern.findall(code))

def check_and_install_dependencies(code):
    # Get all imports
    imports = extract_imports(code)
    
    # Skip standard library modules
    std_lib_modules = set(sys.modules.keys()) & imports
    third_party_modules = imports - std_lib_modules
    
    for module in third_party_modules:
        try:
            __import__(module)
            print(f"✓ Module '{module}' is already installed")
        except ImportError:
            print(f"⚠ Module '{module}' not found, installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", module])
                print(f"✓ Successfully installed '{module}'")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to install '{module}': {str(e)}")

# The code string is passed in quotes to the function
check_and_install_dependencies('''{code_str}''')
"""
        # Replace {code_str} with the actual code, escaping any quotes
        dependency_installer = dependency_checker.replace("{code_str}", code.replace("'", "\\'"))
        sandbox.run_code(dependency_installer)

        start = time.time()
        execution = sandbox.run_code(code)
        metrics.add_metric("Code Execution", time.time() - start)

        return execution.logs, metrics

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"e2b execution error: {str(e)}")
        raise

    finally:
        try:
            start = time.time()
            sandbox.kill()
        except Exception as e:
            logger.error(f"e2b cleanup error: {str(e)}")
        metrics.add_metric("Cleanup", time.time() - start)