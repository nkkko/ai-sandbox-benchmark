"""
Utilities for use directly in sandbox code.

This module contains utilities that can be embedded directly in the sandbox code
to provide consistent functionality across tests.
"""

# Template for the benchmark timer decorator
BENCHMARK_TIMER_TEMPLATE = """
import time

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
"""

# Template for printing benchmark results
PRINT_RESULTS_TEMPLATE = """
import json

def print_benchmark_results(test_result, additional_metrics=None):
    # Print the standard output
    if "result" in test_result:
        print(test_result["result"])

    # Print timing summary
    print(f'Execution Time: {test_result["execution_time_ms"] / 1000:.2f}s')

    # Prepare metrics data
    metrics_data = {"internal_execution_time_ms": test_result["execution_time_ms"]}

    # Add any additional metrics
    if additional_metrics:
        metrics_data.update(additional_metrics)

    # Print timing in a standardized JSON format that can be parsed by the benchmark
    print("\\n\\n--- BENCHMARK TIMING DATA ---")
    print(json.dumps(metrics_data))
    print("--- END BENCHMARK TIMING DATA ---")
"""

# Template for package installation
PACKAGE_INSTALL_TEMPLATE = """
import sys
import subprocess
import site
from importlib import invalidate_caches

def ensure_packages(packages, verbose=True):
    if verbose:
        print(f"Installing packages: {', '.join(packages)}...")

    try:
        # Install packages
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--verbose" if verbose else "", *packages
        ])

        # Force a refresh of the sys.path to find newly installed packages
        invalidate_caches()

        # Add site-packages to system path if needed
        site_packages = site.getsitepackages()[0]
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)

        if verbose:
            print(f"Python path: {sys.path}")
            print(f"Successfully installed: {', '.join(packages)}")

        return True
    except Exception as e:
        if verbose:
            print(f"Error installing packages: {e}")
        return False
"""

# Complete sandbox utilities template
SANDBOX_UTILS_TEMPLATE = f"""
{BENCHMARK_TIMER_TEMPLATE}

{PRINT_RESULTS_TEMPLATE}

{PACKAGE_INSTALL_TEMPLATE}
"""

def get_sandbox_utils(include_timer=True, include_results=True, include_packages=True):
    """
    Returns a string containing the requested utility functions for use in sandbox code.

    Args:
        include_timer: Whether to include the benchmark timer decorator
        include_results: Whether to include the results printing function
        include_packages: Whether to include the package installation function

    Returns:
        A string containing the requested utility functions
    """
    utils = []

    if include_timer:
        utils.append(BENCHMARK_TIMER_TEMPLATE)

    if include_results:
        utils.append(PRINT_RESULTS_TEMPLATE)

    if include_packages:
        utils.append(PACKAGE_INSTALL_TEMPLATE)

    return "\n".join(utils)