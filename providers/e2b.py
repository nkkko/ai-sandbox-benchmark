# providers/e2b.py

import time, asyncio, logging, os
from typing import Dict, Any, List
from e2b_code_interpreter import Sandbox
from metrics import EnhancedTimingMetrics
from providers.utils import extract_imports, check_and_install_dependencies

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
        # Use the centralized dependency installation utility
        dependency_checker = f"""
import sys
from providers.utils import check_and_install_dependencies

# The code is passed in with triple quotes to handle any internal quotes
installed_packages = check_and_install_dependencies(
    '''{code.replace("'", "\\'")}'''
)
print(f"Installed packages: {{installed_packages}}")
"""
        sandbox.run_code(dependency_checker)

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