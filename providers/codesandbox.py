# providers/codesandbox.py

import time, logging, requests, os
from typing import Dict, Any
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

async def execute(code: str, env_vars: Dict[str, str] = None):
    metrics = EnhancedTimingMetrics()
    try:
        logger.info("Sending request to CodeSandbox...")
        start = time.time()
        
        # Include environment variables in the request if provided
        request_data = {'code': code}
        if env_vars and len(env_vars) > 0:
            request_data['env_vars'] = env_vars
            logger.info(f"Passing {len(env_vars)} environment variables to CodeSandbox")
            
        response = requests.post(
            'http://localhost:3000/execute',
            json=request_data,
            timeout=60
        )
        logger.info(f"CodeSandbox response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        logger.info("CodeSandbox execution completed")

        # Convert and add metrics:
        for key, value in result['metrics'].items():
            # Mapping metric names as done in the original code.
            mapping = {
                'workspaceCreation': 'Workspace Creation',
                'codeExecution': 'Code Execution',
                'cleanup': 'Cleanup'
            }
            metrics.add_metric(mapping[key], value / 1000)

        return result['output'], metrics

    except requests.exceptions.ConnectionError:
        error_msg = "Failed to connect to CodeSandbox server. Is it running?"
        logger.error(error_msg)
        metrics.add_error(error_msg)
        raise

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"CodeSandbox execution error: {str(e)}")
        raise