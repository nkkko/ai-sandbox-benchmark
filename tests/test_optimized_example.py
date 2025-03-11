"""
Example of an optimized test using the sandbox utilities.

This test demonstrates how to use the sandbox_utils module to reduce code duplication.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_optimized_example():
    """
    Example test that demonstrates the optimized test structure.

    This test performs a simple matrix multiplication benchmark using numpy.
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
def run_matrix_benchmark():
    # Create matrices and perform operations
    import numpy as np
    size = 1000
    matrix_a = np.random.random((size, size))
    matrix_b = np.random.random((size, size))

    # Perform matrix multiplication
    result = np.dot(matrix_a, matrix_b)

    return f"Matrix multiplication completed: {size}x{size} matrices"

# Ensure required packages are installed
ensure_packages(["numpy"])

# Execute the benchmark
test_result = run_matrix_benchmark()

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