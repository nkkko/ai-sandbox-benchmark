# providers/modal.py

import time
import logging
from typing import Dict
import modal
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

# Define the image with necessary packages at global scope
image = modal.Image.debian_slim().pip_install(
    "numpy", 
    "pandas", 
    "scipy",  # Required for FFT tests
    "matplotlib",
    "requests",
    "psutil"
)


async def execute(code: str, env_vars: Dict[str, str] = None):
    metrics = EnhancedTimingMetrics()
    sandbox = None
    try:
        logger.info("Creating Modal sandbox...")
        start = time.time()

        # Look up or create an app as required by Modal
        app = modal.App.lookup(
            "sandbox-execution",
            create_if_missing=True
        )

        # Create secrets for environment variables if provided
        secrets = None
        if env_vars:
            env_dict = {k: v for k, v in env_vars.items()}
            secrets = [modal.Secret.from_dict(env_dict)]

        # Create a sandbox with the app and image
        sandbox = modal.Sandbox.create(
            app=app,
            image=image,
            secrets=secrets
        )

        # Write the code to a file inside the sandbox
        logger.info("Writing code to sandbox...")

        # Create directory and write the code file directly in the sandbox
        mkdir_cmd = sandbox.exec("mkdir", "-p", "/sandbox")
        mkdir_cmd.wait()

        # Write the Python code to a file in the sandbox
        write_cmd = sandbox.exec(
            "bash",
            "-c",
            f'cat > /sandbox/code.py << \'EOL\'\n{code}\nEOL'
        )
        write_cmd.wait()

        # Track setup time
        metrics.add_metric("Workspace Creation", time.time() - start)

        # Execute the code
        logger.info("Running code in Modal sandbox...")
        start_exec = time.time()
        process = sandbox.exec("python", "/sandbox/code.py")

        # Collect output
        stdout_data = process.stdout.read()
        stderr_data = process.stderr.read()

        # Record execution time
        metrics.add_metric("Code Execution", time.time() - start_exec)

        # Combine outputs if needed
        output = stdout_data
        if stderr_data:
            logger.info(f"Stderr from Modal execution: {stderr_data}")

        return output, metrics

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"Modal execution error: {str(e)}")
        raise
    finally:
        # Clean up the sandbox
        if sandbox:
            start_cleanup = time.time()
            sandbox.terminate()
            metrics.add_metric("Cleanup", time.time() - start_cleanup)