# providers/daytona.py

import time, os, asyncio, logging
from concurrent.futures import ThreadPoolExecutor
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

async def execute(code: str, executor: ThreadPoolExecutor, target_region: str):
    metrics = EnhancedTimingMetrics()
    loop = asyncio.get_running_loop()
    workspace = None
    daytona = None
    try:
        logger.info("Creating Daytona workspace...")
        start = time.time()
        config = DaytonaConfig(
            api_key=str(os.getenv("DAYTONA_API_KEY")),
            server_url=str(os.getenv("DAYTONA_SERVER_URL")),
            target=target_region
        )
        daytona = Daytona(config=config)
        params = CreateWorkspaceParams(language="python")
        workspace = await loop.run_in_executor(executor, daytona.create, params)
        logger.info(f"Workspace created: {workspace.id}")
        metrics.add_metric("Workspace Creation", time.time() - start)

        logger.info("Executing code in Daytona...")
        start = time.time()
        response = await loop.run_in_executor(executor, workspace.process.code_run, code)
        logger.info(f"Code execution completed in workspace {workspace.id}: {response}")
        metrics.add_metric("Code Execution", time.time() - start)
        return response.result, metrics

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"Daytona execution error: {str(e)}")
        raise

    finally:
        if workspace and daytona:
            start = time.time()
            try:
                logger.info(f"Cleaning up Daytona workspace: {workspace.id}...")
                await loop.run_in_executor(executor, daytona.remove, workspace)
                logger.info("Daytona cleanup completed")
                metrics.add_metric("Cleanup", time.time() - start)
            except Exception as e:
                logger.error(f"Daytona cleanup error for workspace {workspace.id}: {str(e)}")
                metrics.add_error(f"Cleanup error: {str(e)}")