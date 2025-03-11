# providers/modal.py

import time, asyncio, logging, os, inspect
from typing import Dict, Any
import modal
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

async def execute(code: str, env_vars: Dict[str, str] = None):
    metrics = EnhancedTimingMetrics()
    try:
        logger.info("Creating Modal sandbox...")
        start = time.time()

        # Create a function in Modal that will execute our code
        # Use the approach from the original implementation but incorporate sandbox concepts
        @modal.function(
            image=modal.Image.debian_slim().pip_install("numpy", "pandas"),
            secrets=[modal.Secret.from_dict({k: v for k, v in (env_vars or {}).items()})] if env_vars else None
        )
        def run_code_in_modal():
            import sys
            import subprocess
            import os
            import tempfile
            
            # Set up environment variables inside the function
            if env_vars:
                for k, v in env_vars.items():
                    os.environ[k] = v
            
            # Write code to a file
            with open("/tmp/code.py", "w") as f:
                f.write(code)
            
            # Create a container-like sandbox environment
            # This simulates the sandbox behavior within the Modal function
            os.makedirs("/sandbox", exist_ok=True)
            
            # Run the code and capture output
            result = subprocess.run(
                [sys.executable, "/tmp/code.py"],
                capture_output=True,
                text=True,
                cwd="/sandbox"  # Run in the sandbox directory
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        
        # Run the Modal function
        logger.info("Running code in Modal...")
        metrics.add_metric("Workspace Creation", time.time() - start)
        
        start_exec = time.time()
        result = run_code_in_modal.call()
        metrics.add_metric("Code Execution", time.time() - start_exec)
        
        # Extract the output
        if isinstance(result, dict) and "stdout" in result:
            output = result["stdout"]
            if result.get("stderr"):
                logger.info(f"Stderr from Modal execution: {result['stderr']}")
        else:
            output = str(result)
        
        return output, metrics

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"Modal execution error: {str(e)}")
        raise