import asyncio
from daytona_sdk import Daytona, CreateWorkspaceParams, DaytonaConfig
from typing import List
import os
from concurrent.futures import ThreadPoolExecutor
import time

config=DaytonaConfig(
    api_key=str(os.getenv("DAYTONA_API_KEY")),
    server_url=str(os.getenv("DAYTONA_SERVER_URL")),
    target="eu"
)

async def run_workspace_flow(executor: ThreadPoolExecutor) -> None:
    daytona = Daytona(config=config)
    loop = asyncio.get_running_loop()
    start_time = time.time()
    workspace_id = None

    params = CreateWorkspaceParams(
        language="python"
    )

    try:
        # Run create in executor to make it non-blocking
        create_start = time.time()
        workspace = await loop.run_in_executor(
            executor,
            daytona.create,
            params
        )
        create_duration = time.time() - create_start
        workspace_id = workspace.id
        print(f"Created workspace: {workspace.id} (took {create_duration:.2f}s)")

        # Run set_labels in executor
        # labels_start = time.time()
        # await loop.run_in_executor(
        #     executor,
        #     workspace.set_labels,
        #     {"public": True}
        # )
        # labels_duration = time.time() - labels_start
        # print(f"Set labels for {workspace.id} (took {labels_duration:.2f}s)")

        # Run exec in executor
        exec_start = time.time()
        response = await loop.run_in_executor(
            executor,
            workspace.process.exec,
            'ls'
        )
        exec_duration = time.time() - exec_start

        if response.exit_code != 0:
            print(f"Error in workspace {workspace.id}: {response.exit_code} {response.result} (took {exec_duration:.2f}s)")
        else:
            print(f"Success in workspace {workspace.id}: {response.result} (took {exec_duration:.2f}s)")

    except Exception as e:
        print(f"Error occurred for workspace {workspace_id}: {str(e)}")

    finally:
        # Cleanup
        try:
            cleanup_start = time.time()
            await loop.run_in_executor(
                executor,
                daytona.remove,
                workspace
            )
            cleanup_duration = time.time() - cleanup_start
            print(f"Removed workspace: {workspace.id} (took {cleanup_duration:.2f}s)")
        except Exception as e:
            print(f"Error during cleanup for workspace {workspace_id}: {str(e)}")

        total_duration = time.time() - start_time
        print(f"Total flow duration for workspace {workspace_id}: {total_duration:.2f}s")

async def main(num_concurrent: int):
    total_start = time.time()
    print(f"Starting {num_concurrent} concurrent workspace flows")

    # Create a ThreadPoolExecutor with max_workers set to num_concurrent
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        # Create a list of tasks
        tasks: List[asyncio.Task] = []
        for _ in range(num_concurrent):
            task = asyncio.create_task(run_workspace_flow(executor))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    total_duration = time.time() - total_start
    print(f"All workspace flows completed in {total_duration:.2f}s")

if __name__ == "__main__":
    NUM_CONCURRENT = 200  # Change this number to run more or fewer concurrent flows

    # Run the async main function
    asyncio.run(main(NUM_CONCURRENT))