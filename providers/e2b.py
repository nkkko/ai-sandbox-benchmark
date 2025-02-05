# providers/e2b.py

import time, asyncio, logging
from e2b_code_interpreter import Sandbox
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

async def execute(code: str):
    metrics = EnhancedTimingMetrics()
    try:
        start = time.time()
        sandbox = Sandbox()
        metrics.add_metric("Workspace Creation", time.time() - start)

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