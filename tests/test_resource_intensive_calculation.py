"""
Test that performs resource-intensive calculations to stress test the sandbox.

This test runs multiple CPU, memory, and disk I/O intensive tasks concurrently
to measure how the sandbox environment handles high resource utilization.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_resource_intensive_calculation():
    """
    Performs resource-intensive calculations to stress test the sandbox.
    
    This test runs multiple intensive tasks simultaneously:
    - CPU-intensive prime number calculations and factorial computations
    - Memory-intensive list operations with large data structures
    - Disk I/O intensive file read/write operations
    
    All tasks run concurrently to maximize resource utilization.
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=False,  # Can run multiple times
    )
    
    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=True,  # Need timing for benchmark
        include_results=True,  # Need results formatting
        include_packages=False  # No packages needed for this test
    )
    
    # Define the test-specific code
    test_code = """
import hashlib
import os
import random
import string
import tempfile
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

# Detect available resources and scale accordingly
def get_optimal_resources():
    # Detect CPU cores and scale worker count
    try:
        import psutil
        cpu_count = psutil.cpu_count(logical=False) or 2
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)
        
        # Scale based on available resources
        workers = min(6, max(2, cpu_count - 1))  # At least 2, at most 6
        
        # Scale down task iterations based on available memory
        memory_scale = max(0.3, min(1.0, available_gb / 4))  # Scale between 30-100% based on 4GB reference
        
        return {
            'workers': workers,
            'memory_scale': memory_scale,
            'cpu_count': cpu_count,
            'available_memory_gb': available_gb
        }
    except ImportError:
        # Fallback to conservative defaults if psutil not available
        return {
            'workers': 4,
            'memory_scale': 0.5,
            'cpu_count': multiprocessing.cpu_count(),
            'available_memory_gb': 2.0
        }

# Get resource configuration
resources = get_optimal_resources()
print(f"Detected resources: {resources['cpu_count']} CPUs, {resources['available_memory_gb']:.2f}GB available memory")
print(f"Using {resources['workers']} workers, scaling memory-intensive tasks to {resources['memory_scale']*100:.0f}%")

#################
# CPU-intensive task (Adaptive range based on resources)
def cpu_intensive_task():
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True

    current_hash = "0"
    # Adjust range based on available resources
    range_start = 10000
    range_end = int(10000 + 15000 * resources['memory_scale'])
    print(f"CPU task range: {range_start} to {range_end}")
    
    for i in range(range_start, range_end):
        if is_prime(i):
            current_hash = hashlib.sha256((current_hash + str(i)).encode()).hexdigest()
    return current_hash

# Alternative CPU-intensive task (Adaptive computations based on resources)
def alternative_cpu_task():
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    result = 0
    # Adjust range based on available resources
    range_start = 50
    range_end = int(50 + 20 * resources['memory_scale'])
    range_end = min(range_end, 70)  # Cap at 70 to prevent stack overflows
    print(f"Factorial task range: {range_start} to {range_end}")
    
    for i in range(range_start, range_end):
        fact = factorial(i)
        result = int(str(result) + str(fact % 1000000))
    return hashlib.sha256(str(result).encode()).hexdigest()

#################
# Memory-intensive task (Adaptive data size based on resources)
def memory_intensive_task():
    base_size = 10000
    size = int(base_size * resources['memory_scale'])  # Scale size based on available memory
    iterations = int(1000 * resources['memory_scale'])  # Scale iterations based on available memory
    
    print(f"Memory task parameters: size={size}, iterations={iterations}")
    
    try:
        lists = []
        for i in range(iterations):
            if i % 100 == 0:  # Check and release memory periodically
                if len(lists) > 300:
                    # Keep only every 3rd list to reduce memory pressure
                    lists = lists[::3]
            
            new_list = list(range(i, i + size))
            reversed_list = list(reversed(new_list))
            sorted_list = sorted(new_list, reverse=True)
            lists.extend([new_list, reversed_list, sorted_list])
        
        result = 0
        for lst in lists:
            result += sum(lst[::2])
        return result
    except MemoryError:
        # Graceful degradation on memory errors
        print("Memory allocation limit reached - scaling down")
        return "Memory test scaled down due to resource constraints"

#################
# HDD-intensive task (Adaptive file size based on resources)
def hdd_intensive_task():
    # Scale file size based on available resources
    base_chunk_size = 1 * 1024 * 1024  # 1MB base chunk
    chunk_size = int(base_chunk_size * resources['memory_scale'])
    iterations = int(10 * resources['memory_scale'])
    
    print(f"Disk I/O task parameters: chunk_size={chunk_size/1024/1024:.2f}MB, iterations={iterations}")
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        file_path = os.path.join(tmpdirname, "test_disk.txt")
        # Generate data chunk sized appropriately for the environment
        data_chunk = ''.join(random.choices(string.ascii_letters + string.digits, k=chunk_size))
        try:
            with open(file_path, "w") as f:
                for _ in range(iterations):
                    f.write(data_chunk)
        except IOError as e:
            return f"File write error: {e}"

        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha.update(chunk)
        except IOError as e:
            return f"File read error: {e}"
        return sha.hexdigest()

#################
# Running multiple tasks concurrently with adaptive worker count.
def run_resource_intensive_tests():
    tasks = []
    # Scale number of workers and task instances based on available resources
    instance_count = max(1, min(2, int(resources['cpu_count'] / 2)))
    worker_count = resources['workers']
    
    print(f"Running {instance_count} instances of each task with {worker_count} workers")
    
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for _ in range(instance_count):
            tasks.append(executor.submit(cpu_intensive_task))
            tasks.append(executor.submit(alternative_cpu_task))
            tasks.append(executor.submit(memory_intensive_task))
            tasks.append(executor.submit(hdd_intensive_task))

        completed = 0
        failed = 0
        
        for future in as_completed(tasks):
            try:
                result = future.result(timeout=300)  # Add timeout to prevent hanging
                completed += 1
                # For CPU and disk I/O tasks, print a partial hash.
                if isinstance(result, str) and len(result) > 20:
                    print(f"Task {completed}/{len(tasks)} completed: {result[:20]}...")
                else:
                    print(f"Task {completed}/{len(tasks)} completed: {result}")
            except Exception as e:
                failed += 1
                print(f"Task failed: {str(e)}")
        
        print(f"All tasks completed. Success: {completed}, Failed: {failed}")

@benchmark_timer
def timed_test():
    run_resource_intensive_tests()
    return "Completed resource intensive calculations"

# Run the benchmark
test_result = timed_test()

# Print the results using the utility function
print_benchmark_results(test_result)
"""

    # Combine the utilities and test code
    full_code = f"{utils_code}\n\n{test_code}"

    # Return the test configuration and code
    return {
        "config": config,
        "code": full_code
    }