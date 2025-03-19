#!/usr/bin/env python3

"""
Test to demonstrate Daytona API limitations with concurrent requests.
This script creates workspaces in both sequential and concurrent patterns
to demonstrate the performance difference.

Usage:
   python test_daytona_concurrency.py
"""

import os
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from daytona_sdk import Daytona, DaytonaConfig, CreateSandboxParams

# Load environment variables
load_dotenv()

# Global configuration
USE_STAGE = os.getenv("USE_DAYTONA_STAGE", "false").lower() == "true"

# Use the appropriate Daytona environment based on the flag
if USE_STAGE:
    DAYTONA_API_KEY = os.getenv("DAYTONA_STAGE_API_KEY")
    DAYTONA_SERVER_URL = os.getenv("DAYTONA_STAGE_SERVER_URL", "https://stage.daytona.work/api")
    print("Using Daytona STAGING environment")
else:
    DAYTONA_API_KEY = os.getenv("DAYTONA_API_KEY")
    DAYTONA_SERVER_URL = os.getenv("DAYTONA_SERVER_URL", "https://app.daytona.io/api")
    print("Using Daytona PRODUCTION environment")
TARGET_REGION = "eu"  # Change as needed
NUM_WORKSPACES = 5    # Number of workspaces to create in each test
IMAGE = ""

# Helper functions for prettier output
def print_header(text):
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80)

def print_result(name, times):
    avg_time = statistics.mean(times)
    if len(times) > 1:
        std_dev = statistics.stdev(times)
        print(f"  {name:<20}: {avg_time:.2f}s ± {std_dev:.2f}s")
    else:
        print(f"  {name:<20}: {avg_time:.2f}s")

# Create a Daytona client
def create_daytona_client():
    if not DAYTONA_API_KEY:
        env_var = "DAYTONA_STAGE_API_KEY" if USE_STAGE else "DAYTONA_API_KEY"
        raise ValueError(f"{env_var} environment variable not set")

    config = DaytonaConfig(
        api_key=DAYTONA_API_KEY,
        server_url=DAYTONA_SERVER_URL,
        target=TARGET_REGION
    )
    return Daytona(config=config)

# Function to create a single workspace and measure time
async def create_workspace(client, executor, index):
    print(f"Creating workspace {index+1}/{NUM_WORKSPACES}...")
    start_time = time.time()

    params = CreateSandboxParams(
        image=IMAGE,
        language="python"
    )

    try:
        # Create workspace
        loop = asyncio.get_running_loop()
        workspace = await loop.run_in_executor(executor, client.create, params)
        workspace_id = workspace.id
        creation_time = time.time() - start_time
        print(f"  Workspace {index+1} created in {creation_time:.2f}s: {workspace_id}")

        # Clean up
        await loop.run_in_executor(executor, client.remove, workspace)
        print(f"  Workspace {index+1} removed")

        return creation_time
    except Exception as e:
        print(f"  Error creating workspace {index+1}: {str(e)}")
        return None

# Function to list workspaces and measure time
async def list_workspaces(client, executor):
    print("Listing workspaces to warm up pool...")
    start_time = time.time()

    try:
        # List workspaces
        loop = asyncio.get_running_loop()
        workspaces = await loop.run_in_executor(executor, client.list)
        list_time = time.time() - start_time
        print(f"  Listed {len(workspaces)} workspaces in {list_time:.2f}s")

        return list_time, len(workspaces)
    except Exception as e:
        print(f"  Error listing workspaces: {str(e)}")
        return None, 0

# Test 1: Sequential workspace creation
async def test_sequential():
    print_header("TEST 1: SEQUENTIAL WORKSPACE CREATION")
    print("Creating workspaces one at a time...")

    client = create_daytona_client()
    times = []

    with ThreadPoolExecutor(max_workers=1) as executor:
        for i in range(NUM_WORKSPACES):
            time_taken = await create_workspace(client, executor, i)
            if time_taken:
                times.append(time_taken)

    return times

# Test 2: Concurrent workspace creation
async def test_concurrent():
    print_header("TEST 2: CONCURRENT WORKSPACE CREATION")
    print(f"Creating {NUM_WORKSPACES} workspaces concurrently...")

    client = create_daytona_client()
    tasks = []

    with ThreadPoolExecutor(max_workers=NUM_WORKSPACES) as executor:
        for i in range(NUM_WORKSPACES):
            task = asyncio.create_task(create_workspace(client, executor, i))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

    return [t for t in results if t is not None]

# Test 3: Independent clients concurrent creation
async def test_independent_concurrent():
    print_header("TEST 3: CONCURRENT CREATION WITH INDEPENDENT CLIENTS")
    print(f"Creating {NUM_WORKSPACES} workspaces concurrently with separate clients...")

    tasks = []

    with ThreadPoolExecutor(max_workers=NUM_WORKSPACES) as executor:
        for i in range(NUM_WORKSPACES):
            # Create a new client for each workspace
            client = create_daytona_client()
            task = asyncio.create_task(create_workspace(client, executor, i))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

    return [t for t in results if t is not None]

# Test 4: Sequential with warm pool
async def test_sequential_with_warmup():
    print_header("TEST 4: SEQUENTIAL WITH WARM POOL")
    print("Creating workspaces one at a time after warming up the pool...")

    client = create_daytona_client()
    times = []

    with ThreadPoolExecutor(max_workers=1) as executor:
        # First, list workspaces to warm up the pool
        await list_workspaces(client, executor)

        # Now create workspaces
        for i in range(NUM_WORKSPACES):
            time_taken = await create_workspace(client, executor, i)
            if time_taken:
                times.append(time_taken)

    return times

# Main function
async def main():
    print_header("DAYTONA API CONCURRENCY TEST")

    # Test 1: Sequential
    sequential_times = await test_sequential()

    # Wait a moment between tests
    print("\nWaiting 5 seconds before next test...")
    await asyncio.sleep(5)

    # Test 2: Concurrent with shared client
    concurrent_times = await test_concurrent()

    # Wait a moment between tests
    print("\nWaiting 5 seconds before next test...")
    await asyncio.sleep(5)

    # Test 3: Concurrent with independent clients
    independent_times = await test_independent_concurrent()

    # Wait a moment between tests
    print("\nWaiting 5 seconds before next test...")
    await asyncio.sleep(5)

    # Test 4: Sequential with warm pool
    warmup_times = await test_sequential_with_warmup()

    # Print summary
    print_header("RESULTS SUMMARY")
    print_result("Sequential", sequential_times)
    print_result("Concurrent", concurrent_times)
    print_result("Independent", independent_times)
    print_result("With Warm Pool", warmup_times)

    # Calculate performance factors
    if sequential_times:
        avg_sequential = statistics.mean(sequential_times)

        if concurrent_times:
            slowdown = statistics.mean(concurrent_times) / avg_sequential
            print(f"\nConcurrent slowdown factor: {slowdown:.2f}x")

        if independent_times:
            ind_slowdown = statistics.mean(independent_times) / avg_sequential
            print(f"Independent clients slowdown factor: {ind_slowdown:.2f}x")

        if warmup_times:
            warmup_improvement = avg_sequential / statistics.mean(warmup_times)
            print(f"Warm pool speedup factor: {warmup_improvement:.2f}x")

if __name__ == "__main__":
    asyncio.run(main())