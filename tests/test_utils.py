import time
import json
import sys
import subprocess
import os
import site
from importlib import invalidate_caches
from typing import Dict, Any, List, Callable, Optional, Union

def benchmark_timer(func):
    """
    Decorator that times the execution of a function and returns both the result and timing.

    Args:
        func: The function to time

    Returns:
        A dictionary containing the function result and execution time in milliseconds
    """
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

def ensure_packages(packages: List[str], verbose: bool = True) -> bool:
    """
    Ensures that the specified packages are installed.

    Args:
        packages: List of package names to install
        verbose: Whether to print verbose output

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"Installing packages: {', '.join(packages)}...")

    try:
        # Install packages
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--verbose" if verbose else "", *packages
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

def print_benchmark_results(test_result: Dict[str, Any], additional_metrics: Optional[Dict[str, Any]] = None):
    """
    Prints benchmark results in a standardized format that can be parsed by the benchmark framework.

    Args:
        test_result: Dictionary containing test results with at least "execution_time_ms"
        additional_metrics: Optional additional metrics to include in the output
    """
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
    print("\n\n--- BENCHMARK TIMING DATA ---")
    print(json.dumps(metrics_data))
    print("--- END BENCHMARK TIMING DATA ---")

def create_test_config(
    env_vars: List[str] = None,
    single_run: bool = False,
    packages: List[str] = None,
    is_info_test: bool = False
) -> Dict[str, Any]:
    """
    Creates a standardized test configuration dictionary.

    Args:
        env_vars: List of environment variables needed by the test
        single_run: Whether the test should only be run once
        packages: List of packages required by the test
        is_info_test: Whether this is an informational test rather than a performance test

    Returns:
        A dictionary containing the test configuration
    """
    config = {
        "env_vars": env_vars or [],
        "single_run": single_run,
    }

    if packages:
        config["packages"] = packages

    return config

# Note: Not a test - this is a utility function
def wrap_test(
    test_func: Callable,
    config: Dict[str, Any] = None,
    is_info_test: bool = False
) -> Callable:
    """
    Wraps a test function to provide standard configuration.

    Args:
        test_func: The test function to wrap
        config: Optional configuration dictionary
        is_info_test: Whether this is an informational test

    Returns:
        A wrapped test function that returns the proper format
    """
    def wrapper():
        # Set attributes on the function
        if is_info_test:
            test_func.is_info_test = True

        # Use provided config or create default
        test_config = config or create_test_config()

        # Get the test code
        code = test_func()

        # Return in the standard format
        return {
            "config": test_config,
            "code": code
        }

    # Copy attributes from the original function
    wrapper.__name__ = test_func.__name__
    wrapper.__doc__ = test_func.__doc__

    return wrapper