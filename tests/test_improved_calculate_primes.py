"""
Improved version of the calculate primes test using the test_utils module.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_improved_calculate_primes():
    """
    Test that calculates prime numbers to benchmark basic computation performance.

    This test measures the performance of a simple algorithm to find prime numbers,
    which is CPU-bound and doesn't require any external dependencies.
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
def calculate_primes(limit=1000):
    # Calculate prime numbers up to the specified limit
    primes = []
    for num in range(2, limit + 1):
        is_prime = True
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)

    # Calculate some statistics
    prime_count = len(primes)
    prime_sum = sum(primes)
    prime_avg = prime_sum / prime_count if prime_count > 0 else 0

    return f"Found {prime_count} primes up to {limit}\\nSum: {prime_sum}\\nAverage: {prime_avg:.2f}"

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