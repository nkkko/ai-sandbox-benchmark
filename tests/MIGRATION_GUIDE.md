# Test Migration Guide

This guide explains how to migrate existing tests to use the new optimized test framework.

## Migration Steps

1. **Add imports** for the utility modules:
   ```python
   from tests.test_utils import create_test_config
   from tests.test_sandbox_utils import get_sandbox_utils
   ```

2. **Replace the config dictionary** with a call to `create_test_config()`:
   ```python
   # Old approach
   config = {
       "env_vars": [],
       "single_run": False,
       "packages": ["numpy", "scipy"]
   }

   # New approach
   config = create_test_config(
       env_vars=[],
       single_run=False,
       packages=["numpy", "scipy"]
   )
   ```

3. **Get the sandbox utilities code** using `get_sandbox_utils()`:
   ```python
   utils_code = get_sandbox_utils(
       include_timer=True,
       include_results=True,
       include_packages=True  # Set to True if you need package installation
   )
   ```

4. **Extract the test-specific code** from your existing test:
   - Remove the benchmark timer decorator implementation
   - Remove the package installation code
   - Remove the results printing code
   - Keep only the test-specific logic

5. **Combine the utilities and test code**:
   ```python
   full_code = f"{utils_code}\n\n{test_code}"
   ```

6. **Return the test configuration and code**:
   ```python
   return {
       "config": config,
       "code": full_code
   }
   ```

## Example: Before and After

### Before Migration

```python
def test_calculate_primes():
    # Test configuration
    config = {
        "env_vars": [],  # No env vars needed
        "single_run": False,  # Can run multiple times
    }

    return {
        "config": config,
        "code": """
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

@benchmark_timer
def calculate_primes():
    primes = []
    num = 2
    while len(primes) < 10:
        is_prime = True
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
        num += 1
    prime_sum = sum(primes)
    prime_avg = prime_sum / len(primes)
    return f"Primes: {primes}\\nSum: {prime_sum}\\nAverage: {prime_avg}"

# Execute the test and get results with timing
test_result = calculate_primes()

# Print the standard output
print(test_result["result"])

# Print timing in a standardized JSON format that can be parsed by the benchmark
print("\\n\\n--- BENCHMARK TIMING DATA ---")
print(json.dumps({"internal_execution_time_ms": test_result["execution_time_ms"]}))
print("--- END BENCHMARK TIMING DATA ---")
"""
    }
```

### After Migration

```python
"""
Test that calculates prime numbers to benchmark basic computation performance.

This test measures the performance of a simple algorithm to find prime numbers,
which is CPU-bound and doesn't require any external dependencies.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_calculate_primes():
    """
    Test that calculates prime numbers to benchmark basic computation performance.

    This test finds the first 10 prime numbers and calculates their sum and average.
    It's a simple CPU-bound test that doesn't require any external dependencies.
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=False,  # Can run multiple times
    )

    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=True,
        include_results=True,
        include_packages=False  # No packages needed for this test
    )

    # Define the test-specific code
    test_code = """
@benchmark_timer
def calculate_primes():
    primes = []
    num = 2
    while len(primes) < 10:
        is_prime = True
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
        num += 1
    prime_sum = sum(primes)
    prime_avg = prime_sum / len(primes)
    return f"Primes: {primes}\\nSum: {prime_sum}\\nAverage: {prime_avg}"

# Execute the test and get results with timing
test_result = calculate_primes()

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
```

## Migration Checklist

- [ ] Add imports for utility modules
- [ ] Replace config dictionary with `create_test_config()`
- [ ] Get sandbox utilities code with `get_sandbox_utils()`
- [ ] Extract test-specific code
- [ ] Use `benchmark_timer` decorator from utilities
- [ ] Use `ensure_packages()` for package installation
- [ ] Use `print_benchmark_results()` for output
- [ ] Combine utilities and test code
- [ ] Add proper docstrings
- [ ] Set `is_info_test=True` for information tests

## Tips for Specific Test Types

### Performance Tests

For performance tests, include:
- `include_timer=True` in `get_sandbox_utils()`
- `include_results=True` in `get_sandbox_utils()`
- Use the `@benchmark_timer` decorator for your test function
- Call `print_benchmark_results(test_result)` to print results

### Information Tests

For information tests:
- Set `is_info_test=True` in `create_test_config()`
- Set `single_run=True` in `create_test_config()`
- You may not need timing, so use `include_timer=False`
- You may not need results formatting, so use `include_results=False`

### Tests with Package Dependencies

For tests that require external packages:
- Specify packages in `create_test_config(packages=["package1", "package2"])`
- Use `include_packages=True` in `get_sandbox_utils()`
- Call `ensure_packages(["package1", "package2"])` in your test code