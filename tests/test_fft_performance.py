"""
Test that measures the performance of Fast Fourier Transform operations.

This test creates large random matrices and performs FFT operations on them,
which is computationally intensive and depends on numpy and scipy.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_fft_performance():
    """
    Test that measures the performance of Fast Fourier Transform operations.
    
    This test creates large random matrices and performs FFT operations on them.
    It uses numpy and scipy for high-performance numerical computations.
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=False,  # Can run multiple times
        packages=["numpy", "scipy"]  # Required packages
    )

    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=True,
        include_results=True,
        include_packages=True  # We need package installation for numpy and scipy
    )

    # Define the test-specific code
    test_code = """
# Ensure required packages are installed
ensure_packages(["numpy", "scipy"])

# Import the required packages
import numpy as np
from scipy import fft

@benchmark_timer
def run_fft_benchmark():
    [fft.fft2(np.random.random((10000, 10000))) for _ in range(2)]
    return "FFT calculations completed successfully"

# Execute the benchmark
test_result = run_fft_benchmark()

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