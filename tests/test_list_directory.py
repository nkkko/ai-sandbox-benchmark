"""
Test that lists directory contents using the bash ls command.

This is a simple test to measure the performance of directory listing operations
and to verify access to basic filesystem operations.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_list_directory():
    """
    List directory contents using bash ls command instead of Python.
    
    This test executes a simple 'ls -la /home' command and measures its execution time.
    It serves as a basic test of filesystem access and performance.
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
import subprocess

@benchmark_timer
def run_test():
    # Run the ls command in the home directory
    result = subprocess.run(['ls', '-la', '/home'], capture_output=True, text=True)
    return result.stdout

# Execute the test and get results with timing
test_result = run_test()

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