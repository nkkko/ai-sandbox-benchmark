# providers/codesandbox.py

import time, logging, requests, os
from typing import Dict, Any
from metrics import BenchmarkTimingMetrics

logger = logging.getLogger(__name__)

# Create logging helpers with provider prefix
def log_info(message):
    logger.info(f"[CodeSandbox] {message}")

def log_error(message):
    logger.error(f"[CodeSandbox] {message}")

def log_warning(message):
    logger.warning(f"[CodeSandbox] {message}")

async def execute(code: str, env_vars: Dict[str, str] = None):
    metrics = BenchmarkTimingMetrics()
    try:
        log_info("Sending request...")
        start = time.time()
        
        # Extract test configuration if available
        test_config = {}
        original_code = code
        try:
            # Check if we're passed a code_config dictionary directly
            if isinstance(code, dict) and 'code' in code and 'config' in code:
                # New format with config
                test_config = code.get('config', {})
                # Update code to be just the code string
                code = code['code']
        except Exception as e:
            log_info(f"Error extracting test configuration: {e}")
        
        # Include environment variables in the request if provided
        request_data = {'code': code}
        if env_vars and len(env_vars) > 0:
            request_data['env_vars'] = env_vars
            log_info(f"Passing {len(env_vars)} environment variables")
            
        # Add test configuration to request if available
        if test_config:
            request_data['test_config'] = test_config
            log_info(f"Passing test configuration to CodeSandbox service")
            
        response = requests.post(
            'http://localhost:3000/execute',
            json=request_data,
            timeout=60
        )
        log_info(f"Response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        log_info("Execution completed")

        # Convert and add metrics:
        for key, value in result['metrics'].items():
            # Mapping metric names as done in the original code.
            mapping = {
                'workspaceCreation': 'Workspace Creation',
                'setupTime': 'Setup Time',
                'codeExecution': 'Code Execution',
                'cleanup': 'Cleanup'
            }
            metrics.add_metric(mapping[key], value / 1000)

        return result['output'], metrics

    except requests.exceptions.ConnectionError:
        error_msg = "Failed to connect to server. Is it running?"
        log_error(error_msg)
        metrics.add_error(error_msg)
        raise

    except Exception as e:
        metrics.add_error(str(e))
        log_error(f"Execution error: {str(e)}")
        raise