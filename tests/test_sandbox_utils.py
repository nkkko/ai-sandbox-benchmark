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

    # Handle the case where test_result might be None or missing keys
    # This fixes the TypeError issue in database_operations test
    if not test_result or "execution_time_ms" not in test_result:
        print("Warning: Invalid test result format")
        print(f'Execution Time: N/A')
        
        # Prepare metrics data with default values
        metrics_data = {"internal_execution_time_ms": 0}
        
        # Add any additional metrics
        if additional_metrics:
            metrics_data.update(additional_metrics)
            
        # Print timing in a standardized JSON format that can be parsed by the benchmark
        print("\\n\\n--- BENCHMARK TIMING DATA ---")
        print(json.dumps(metrics_data))
        print("--- END BENCHMARK TIMING DATA ---")
        return

    # Regular case - test_result contains expected data
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
import time

def ensure_packages(packages, verbose=True, max_retries=3):
    if verbose:
        print(f"Installing packages: {', '.join(packages)}...")

    for attempt in range(max_retries):
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
                print(f"Error installing packages (attempt {attempt+1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff (1s, 2s, 4s)
                backoff_time = 2**attempt
                if verbose:
                    print(f"Retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)
            else:
                if verbose:
                    print(f"Failed to install packages after {max_retries} attempts")
                return False
"""

# Template for resource detection
RESOURCE_DETECTION_TEMPLATE = """
def detect_resource_constraints():
    '''Detects available system resources and returns constraint information.'''
    try:
        import psutil
        import multiprocessing
        
        # Get CPU information
        cpu_count = psutil.cpu_count(logical=False) or multiprocessing.cpu_count()
        
        # Get memory information
        mem = psutil.virtual_memory()
        total_memory_gb = mem.total / (1024**3)
        available_memory_gb = mem.available / (1024**3)
        
        # Determine if we're in a constrained environment
        is_constrained = (cpu_count < 2 or available_memory_gb < 1.0)
        
        print(f"System resources: {cpu_count} CPUs, {available_memory_gb:.2f}GB/{total_memory_gb:.2f}GB memory available")
        
        # Calculate a resource scale factor (0.3-1.0) based on available memory
        resource_scale = max(0.3, min(1.0, available_memory_gb / 4))
        
        return {
            "cpu_count": cpu_count,
            "total_memory_gb": total_memory_gb,
            "available_memory_gb": available_memory_gb,
            "is_constrained": is_constrained,
            "resource_scale": resource_scale
        }
    except ImportError:
        # If psutil isn't available, return conservative defaults
        print("Unable to detect system resources (psutil not available)")
        return {
            "cpu_count": 2,
            "total_memory_gb": 4.0,
            "available_memory_gb": 2.0,
            "is_constrained": True,
            "resource_scale": 0.5
        }
    except Exception as e:
        print(f"Error detecting system resources: {e}")
        return {
            "cpu_count": 2,
            "total_memory_gb": 4.0,
            "available_memory_gb": 2.0,
            "is_constrained": True,
            "resource_scale": 0.5,
            "error": str(e)
        }
"""

# Complete sandbox utilities template
SANDBOX_UTILS_TEMPLATE = f"""
{BENCHMARK_TIMER_TEMPLATE}

{PRINT_RESULTS_TEMPLATE}

{PACKAGE_INSTALL_TEMPLATE}

{RESOURCE_DETECTION_TEMPLATE}
"""

def get_sandbox_utils(include_timer=True, include_results=True, include_packages=True, include_resource_detection=True):
    """
    Returns a string containing the requested utility functions for use in sandbox code.

    Args:
        include_timer: Whether to include the benchmark timer decorator
        include_results: Whether to include the results printing function
        include_packages: Whether to include the package installation function
        include_resource_detection: Whether to include resource detection utilities

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
        
    if include_resource_detection:
        utils.append(RESOURCE_DETECTION_TEMPLATE)

    return "\n".join(utils)