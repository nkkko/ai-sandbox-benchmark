# providers/modal.py

import time, asyncio, logging
import modal
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

async def execute(code: str):
    metrics = EnhancedTimingMetrics()
    sandbox = None
    app = None
    try:
        logger.info("Creating Modal sandbox...")
        start = time.time()
        app = modal.App.lookup("code-comparison", create_if_missing=True)
        sandbox = modal.Sandbox.create(
            image=modal.Image.debian_slim().pip_install("numpy", "pandas"),
            app=app
        )
        metrics.add_metric("Workspace Creation", time.time() - start)

        logger.info("Executing code in Modal...")
        start = time.time()
        # Write code to a temporary file
        with open("/tmp/modal_code.py", "w") as f:
            f.write(code)
        process = sandbox.exec("python", "/tmp/modal_code.py")
        output = process.stdout.read()
        metrics.add_metric("Code Execution", time.time() - start)
        return output, metrics

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"Modal execution error: {str(e)}")
        raise

    finally:
        if sandbox:
            start = time.time()
            try:
                logger.info("Cleaning up Modal sandbox...")
                sandbox.terminate()
                logger.info("Modal cleanup completed")
                metrics.add_metric("Cleanup", time.time() - start)
            except Exception as e:
                logger.error(f"Modal cleanup error: {str(e)}")
                metrics.add_error(f"Cleanup error: {str(e)}")