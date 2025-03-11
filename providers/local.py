# providers/local.py

import time
import asyncio
import logging
import os
import sys
import subprocess
import tempfile
from typing import Dict, Any, List, Tuple, Optional, Union
from metrics import BenchmarkTimingMetrics
from providers.utils import extract_imports, check_and_install_dependencies

logger = logging.getLogger(__name__)

# Create logging helpers with provider prefix
def log_info(message):
    logger.info(f"[Local] {message}")

def log_error(message):
    logger.error(f"[Local] {message}")

def log_warning(message):
    logger.warning(f"[Local] {message}")

async def execute(code: str, env_vars: Dict[str, str] = None) -> Tuple[str, BenchmarkTimingMetrics]:
    """
    Execute code locally using subprocess and capture results.
    
    Args:
        code: The Python code to execute or a dict with code and config
        env_vars: Environment variables to set during execution
    
    Returns:
        Tuple[str, BenchmarkTimingMetrics]: Execution result and performance metrics
    """
    metrics = BenchmarkTimingMetrics()
    temp_file = None
    process = None
    
    try:
        # Extract test configuration if available
        test_config = {}
        try:
            # Check if we're passed a code_config dictionary directly
            if isinstance(code, dict) and 'code' in code and 'config' in code:
                # New format with config
                test_config = code.get('config', {})
                # Update code to be just the code string
                code = code['code']
        except Exception as e:
            log_error(f"Error extracting test configuration: {e}")
        
        # Get packages from test configuration if available
        if test_config and 'packages' in test_config:
            log_info(f"Using packages from test config: {test_config['packages']}")
            always_install_packages = test_config['packages']
        else:
            # Default packages if not specified in config
            always_install_packages = [
                'numpy',  # Required for FFT tests
                'scipy',  # Required for FFT tests
            ]
        
        # Check and install dependencies
        log_info("Checking for dependencies in code...")
        start = time.time()
        installed_packages = check_and_install_dependencies(
            code,
            always_install=always_install_packages
        )
        metrics.add_metric("Dependency Installation", time.time() - start)
        
        # Create a temporary file to store the code
        start = time.time()
        temp_file = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
        temp_file.write(code.encode('utf-8'))
        temp_file.close()
        metrics.add_metric("Environment Setup", time.time() - start)
        
        # Prepare environment variables
        execution_env = os.environ.copy()
        if env_vars:
            execution_env.update(env_vars)
        
        # Execute the code
        start = time.time()
        log_info(f"Executing code from {temp_file.name}")
        process = subprocess.Popen(
            [sys.executable, temp_file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=execution_env,
            text=True
        )
        
        stdout, stderr = process.communicate()
        execution_time = time.time() - start
        metrics.add_metric("Code Execution", execution_time)
        
        # Check if execution was successful
        if process.returncode != 0:
            log_error(f"Execution failed with return code {process.returncode}")
            metrics.add_error(f"Execution failed with return code {process.returncode}: {stderr}")
            return f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}", metrics
        
        log_info(f"Execution completed in {execution_time:.2f}s")
        return stdout, metrics
    
    except Exception as e:
        metrics.add_error(str(e))
        log_error(f"Execution error: {str(e)}")
        return f"Error: {str(e)}", metrics
    
    finally:
        # Cleanup
        start = time.time()
        try:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                log_info(f"Removed temporary file {temp_file.name}")
        except Exception as cleanup_err:
            log_error(f"Cleanup error: {str(cleanup_err)}")
        metrics.add_metric("Cleanup", time.time() - start)