"""
Template for creating new benchmark tests.

This template demonstrates how to create a new test using the test_utils module.
"""
from tests.test_utils import (
    benchmark_timer,
    ensure_packages,
    print_benchmark_results,
    create_test_config
)

def test_template():
    """
    Template test function that demonstrates the recommended test structure.

    This is a docstring that should describe what the test does and what it measures.
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # List any environment variables needed
        single_run=False,  # Set to True if test should only run once per benchmark
        packages=["numpy"],  # List required packages
        is_info_test=False  # Set to True for informational tests (not performance)
    )

    # Return the test configuration and code
    return {
        "config": config,
        "code": """
# Import the test utilities directly in the code that will run in the sandbox
import time
import json

# Standardized timing decorator
def benchmark_timer(func):
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
            "execution_time_ms": execution_time * 1000  # Convert to milliseconds
        }

    return wrapper

# Install any required packages
try:
    import numpy as np
    print("Successfully imported numpy")
except ImportError:
    print("Installing numpy...")
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"])
    import numpy as np

# Define the benchmark function
@benchmark_timer
def run_benchmark():
    # Create a large array and perform operations
    arr = np.random.random((1000, 1000))
    for _ in range(10):
        np.dot(arr, arr.T)
    return "Benchmark completed successfully"

# Execute the benchmark
test_result = run_benchmark()

# Print the standard output
print(test_result["result"])
print(f'Execution Time: {test_result["execution_time_ms"] / 1000:.2f}s')

# Print timing in a standardized JSON format that can be parsed by the benchmark
print("\\n\\n--- BENCHMARK TIMING DATA ---")
print(json.dumps({"internal_execution_time_ms": test_result["execution_time_ms"]}))
print("--- END BENCHMARK TIMING DATA ---")
"""
    }