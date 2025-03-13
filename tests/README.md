# Optimized Test Framework

This directory contains benchmark tests for evaluating sandbox environments. The tests have been optimized to reduce code duplication and improve maintainability.

## Test Structure

Each test follows a standard structure:

1. A function named `test_*` that returns a dictionary with:
   - `config`: Test configuration (environment variables, single run flag, etc.)
   - `code`: The actual code to run in the sandbox

## Utility Modules

### `test_utils.py`

Contains utilities for test creation and configuration:

- `benchmark_timer`: Decorator for timing function execution
- `ensure_packages`: Function to install required packages
- `print_benchmark_results`: Function to print benchmark results in a standardized format
- `create_test_config`: Function to create a standardized test configuration
- `wrap_test`: Decorator for wrapping test functions with standard configuration

### `test_sandbox_utils.py`

Contains utilities that can be embedded directly in sandbox code:

- `BENCHMARK_TIMER_TEMPLATE`: Template for the benchmark timer decorator
- `PRINT_RESULTS_TEMPLATE`: Template for printing benchmark results
- `PACKAGE_INSTALL_TEMPLATE`: Template for package installation
- `get_sandbox_utils()`: Function to get a combination of utility templates

## Creating a New Test

### Basic Approach

```python
from tests.test_utils import create_test_config

def test_my_benchmark():
    """
    Description of what this test measures.
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # List any environment variables needed
        single_run=False,  # Set to True if test should only run once per benchmark
        packages=["numpy"],  # List required packages
    )

    # Return the test configuration and code
    return {
        "config": config,
        "code": """
# Your test code here
import time
import json

# ... rest of your test code ...

# Print timing in a standardized JSON format
print("\\n\\n--- BENCHMARK TIMING DATA ---")
print(json.dumps({"internal_execution_time_ms": execution_time_ms}))
print("--- END BENCHMARK TIMING DATA ---")
"""
    }
```

### Optimized Approach

```python
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_optimized_example():
    """
    Description of what this test measures.
    """
    # Define test configuration
    config = create_test_config(
        packages=["numpy"],
        single_run=False
    )

    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=True,
        include_results=True,
        include_packages=True
    )

    # Define the test-specific code
    test_code = """
# Define the benchmark function
@benchmark_timer
def run_benchmark():
    # Your benchmark code here
    return "Benchmark completed"

# Ensure required packages are installed
ensure_packages(["numpy"])

# Execute the benchmark
test_result = run_benchmark()

# Print the results
print_benchmark_results(test_result)
"""

    # Combine the utilities and test code
    full_code = f"{utils_code}\n\n{test_code}"

    # Return the test configuration and code
    return {
        "config": config,
        "code": full_code
    }
```

## Test Types

### Performance Tests

Performance tests measure execution time and should include:

- A clear description of what is being measured
- Standardized timing using the `benchmark_timer` decorator
- Output in the standardized format for the benchmark framework

### Information Tests

Information tests gather system information and should:

- Set `is_info_test = True` in the configuration
- Set `single_run = True` in the configuration
- Focus on gathering and reporting information rather than timing

## Best Practices

1. **Use the utility modules** to reduce code duplication
2. **Include clear documentation** in the test function docstring
3. **Specify required packages** in the test configuration
4. **Use standardized timing** with the `benchmark_timer` decorator
5. **Output results in the standardized format** for the benchmark framework
6. **Handle package installation** gracefully with try/except blocks
7. **Minimize redundant code** by using the utility functions