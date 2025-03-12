def test_fft_multiprocessing_performance():
    """Tests FFT performance using multiprocessing for parallel computation."""
    # Test configuration
    config = {
        "env_vars": [],  # No env vars needed
        "single_run": False,  # Can run multiple times
        "packages": ["numpy", "scipy", "psutil"]  # Required packages
    }

    code = """
import sys
import json
import time
import os
import multiprocessing
from multiprocessing import Pool
import psutil

# Ensure we have the needed dependencies
try:
    import numpy as np
    from scipy import fft
    print("Successfully imported numpy and scipy")
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "scipy", "psutil"])

    # Force a refresh of the sys.path to find newly installed packages
    import site
    from importlib import invalidate_caches
    invalidate_caches()

    # Add site-packages to system path if needed
    site_packages = site.getsitepackages()[0]
    if site_packages not in sys.path:
        sys.path.insert(0, site_packages)

    # Now import the packages
    import numpy as np
    from scipy import fft
    print("Successfully imported numpy and scipy after installation")

# Get system info
print("=== System Information ===")
num_cores = multiprocessing.cpu_count()
print(f"Number of CPU cores: {num_cores}")

# Get memory info
mem_info = psutil.virtual_memory()
total_memory_gb = mem_info.total / (1024**3)
available_memory_gb = mem_info.available / (1024**3)
print(f"Total memory: {total_memory_gb:.2f} GB")
print(f"Available memory: {available_memory_gb:.2f} GB")
print("=========================")


MATRIX_SIZE = 10000  # Larger for systems with plenty of memory
MAX_RUNTIME = 180  # 3 minutes max runtime to avoid timeouts
NUM_ITERATIONS = 3  # Number of FFT calculations to perform sequentially

print(f"Using matrix size: {MATRIX_SIZE}x{MATRIX_SIZE}")
print(f"Running {NUM_ITERATIONS} iterations")

start_time_global = time.time()

# Define the FFT worker function to be executed in parallel
def fft_worker(args):
    # Worker function that performs FFT on a matrix of specified size
    matrix_size, iteration = args
    # Generate a random matrix of the specified size
    matrix = np.random.random((matrix_size, matrix_size))
    # Perform FFT calculation
    result = fft.fft2(matrix)
    return f"FFT calculation #{iteration+1} completed successfully"

# Standardized timing decorator
def benchmark_timer(func):
    # Decorator that measures and returns execution time of a function
    def wrapper(*args, **kwargs):
        # Start timer
        start_time = time.time()

        # Run the function
        result = func(*args, **kwargs)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Return both the result and the timing
        return {
            "result": result,
            "execution_time_ms": execution_time * 1000  # Convert to ms
        }

    return wrapper

@benchmark_timer
def run_fft_benchmark_sequential():
    # Run FFT calculations sequentially
    # Check if we've exceeded our maximum runtime
    if time.time() - start_time_global > MAX_RUNTIME:
        return "Skipped sequential FFT due to time constraints"

    results = []
    for i in range(NUM_ITERATIONS):
        print(f"Running sequential FFT iteration {i+1}/{NUM_ITERATIONS}")
        matrix = np.random.random((MATRIX_SIZE, MATRIX_SIZE))
        result = fft.fft2(matrix)
        results.append(f"Sequential FFT #{i+1} completed")

    return f"Completed {NUM_ITERATIONS} sequential FFT calculations"

@benchmark_timer
def run_fft_benchmark_parallel():
    # Run FFT calculations in parallel using multiprocessing
    # Check if we've exceeded our maximum runtime
    if time.time() - start_time_global > MAX_RUNTIME:
        return "Skipped parallel FFT due to time constraints"

    # Determine optimal number of processes to use (leave one core free for system)
    num_processes = max(1, multiprocessing.cpu_count() - 1)
    print(f"Using {num_processes} CPU cores for parallel processing")

    # Create a multiprocessing pool with the start method appropriate for the platform
    try:
        # Prepare data - we'll do NUM_ITERATIONS FFT calculations in parallel
        tasks = [(MATRIX_SIZE, i) for i in range(NUM_ITERATIONS)]

        # Create pool with appropriate start method
        if sys.platform == 'darwin':  # macOS
            ctx = multiprocessing.get_context('fork')
        else:
            ctx = multiprocessing.get_context()

        with ctx.Pool(processes=num_processes) as pool:
            # Execute FFT calculations in parallel
            results = pool.map(fft_worker, tasks)

        return f"Completed {NUM_ITERATIONS} parallel FFT calculations on {num_processes} cores"
    except Exception as e:
        print(f"Error in parallel execution: {str(e)}")
        return f"Error in parallel execution: {str(e)}"

print(f"Starting benchmarks with {MATRIX_SIZE}x{MATRIX_SIZE} matrices...")

# Execute both benchmarks for comparison
print("Running sequential benchmark...")
sequential_result = run_fft_benchmark_sequential()
print(f"Sequential FFT Performance: {sequential_result['result']}")
if "Skipped" not in sequential_result['result'] and "Error" not in sequential_result['result']:
    print(f"Sequential FFT Time: {sequential_result['execution_time_ms'] / 1000:.2f}s")

# Execute the parallel benchmark
print("\\nRunning parallel benchmark...")
parallel_result = run_fft_benchmark_parallel()
print(f"Parallel FFT Performance: {parallel_result['result']}")
if "Skipped" not in parallel_result['result'] and "Error" not in parallel_result['result']:
    print(f"Parallel FFT Time: {parallel_result['execution_time_ms'] / 1000:.2f}s")

# Calculate speedup if both benchmarks completed successfully
valid_results = (
    "Skipped" not in sequential_result['result'] and
    "Skipped" not in parallel_result['result'] and
    "Error" not in sequential_result['result'] and
    "Error" not in parallel_result['result']
)

if valid_results:
    speedup = sequential_result['execution_time_ms'] / parallel_result['execution_time_ms']
    print(f"\\nSpeedup factor: {speedup:.2f}x")
    efficiency = speedup / max(1, multiprocessing.cpu_count() - 1)
    print(f"Parallel efficiency: {efficiency:.2f} ({efficiency*100:.1f}%)")
else:
    speedup = 0
    efficiency = 0
    print("\\nSpeedup calculation skipped due to execution errors or timing constraints")

# Print timing in a standardized JSON format for benchmark parsing
print("\\n\\n--- BENCHMARK TIMING DATA ---")
benchmark_data = {
    "sequential_execution_time_ms": (
        sequential_result["execution_time_ms"]
        if valid_results else 0
    ),
    "parallel_execution_time_ms": (
        parallel_result["execution_time_ms"]
        if valid_results else 0
    ),
    "speedup_factor": speedup,
    "parallel_efficiency": efficiency,
    "num_cores_used": max(1, multiprocessing.cpu_count() - 1),
    "internal_execution_time_ms": (
        parallel_result["execution_time_ms"]
        if valid_results else 0
    ),
    "matrix_size": MATRIX_SIZE,
    "num_iterations": NUM_ITERATIONS,
    "total_memory_gb": total_memory_gb,
    "available_memory_gb": available_memory_gb
}
print(json.dumps(benchmark_data))
print("--- END BENCHMARK TIMING DATA ---")
"""

    return {
        "config": config,
        "code": code
    }