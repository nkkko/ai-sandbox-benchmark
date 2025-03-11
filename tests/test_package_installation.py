"""
Test that measures the performance of Python package installation.

This test evaluates how quickly different types of packages can be installed
and imported in the sandbox environment.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_package_installation():
    """
    Measures the performance of Python package installation.
    
    This test:
    - Installs both simple and complex Python packages
    - Times the installation process
    - Verifies successful installation by importing packages
    - Measures import time
    - Reports summary statistics
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=True,  # Only need to run once per benchmark session
    )
    
    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=True,  # Need timing for benchmark
        include_results=True,  # Need results formatting
        include_packages=False  # We'll handle package installation manually
    )
    
    # Define the test-specific code
    test_code = """
import time
import subprocess
import sys

def install_package(package_name):
    start_time = time.time()
    print(f"Installing {package_name}...")
    
    try:
        # Use subprocess to run pip install
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--quiet"])
        elapsed = time.time() - start_time
        print(f"Successfully installed {package_name} in {elapsed:.2f} seconds")
        return True, elapsed
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"Failed to install {package_name}: {e}")
        return False, elapsed

def test_import(package_name, import_name=None):
    if import_name is None:
        import_name = package_name
    
    start_time = time.time()
    try:
        # Dynamic import
        __import__(import_name)
        elapsed = time.time() - start_time
        print(f"Successfully imported {import_name} in {elapsed:.4f} seconds")
        return True, elapsed
    except ImportError as e:
        elapsed = time.time() - start_time
        print(f"Failed to import {import_name}: {e}")
        return False, elapsed

def run_package_tests():
    results = {}
    
    # Simple packages
    simple_packages = [
        ("requests", "requests"),
        ("pyyaml", "yaml"),
        ("python-dateutil", "dateutil"),
    ]
    
    # Packages with complex dependencies or compilation requirements
    complex_packages = [
        ("matplotlib", "matplotlib"),
        ("pandas", "pandas"),
        ("scikit-learn", "sklearn"),
    ]
    
    # Test simple packages
    print("\\n=== Testing Simple Package Installation ===")
    for pkg, import_name in simple_packages:
        install_success, install_time = install_package(pkg)
        if install_success:
            import_success, import_time = test_import(import_name)
            results[pkg] = {
                "type": "simple",
                "install_time": install_time,
                "import_time": import_time if import_success else None,
                "success": import_success
            }
    
    # Test complex packages
    print("\\n=== Testing Complex Package Installation ===")
    for pkg, import_name in complex_packages:
        install_success, install_time = install_package(pkg)
        if install_success:
            import_success, import_time = test_import(import_name)
            results[pkg] = {
                "type": "complex",
                "install_time": install_time,
                "import_time": import_time if import_success else None,
                "success": import_success
            }
    
    # Report summary
    print("\\n=== Package Installation Summary ===")
    print(f"{'Package':<20} {'Type':<10} {'Install Time':<15} {'Import Time':<15} {'Success':<10}")
    print("-" * 70)
    
    for pkg, data in results.items():
        install_time_str = f"{data['install_time']:.2f}s" if data['install_time'] else "N/A"
        import_time_str = f"{data['import_time']:.4f}s" if data['import_time'] else "N/A"
        success_str = "✓" if data['success'] else "✗"
        
        print(f"{pkg:<20} {data['type']:<10} {install_time_str:<15} {import_time_str:<15} {success_str:<10}")
    
    # Calculate averages
    simple_install_times = [data['install_time'] for pkg, data in results.items() 
                           if data['type'] == 'simple' and data['install_time']]
    complex_install_times = [data['install_time'] for pkg, data in results.items() 
                            if data['type'] == 'complex' and data['install_time']]
    
    if simple_install_times:
        avg_simple = sum(simple_install_times) / len(simple_install_times)
        print(f"\\nAverage simple package install time: {avg_simple:.2f}s")
    
    if complex_install_times:
        avg_complex = sum(complex_install_times) / len(complex_install_times)
        print(f"Average complex package install time: {avg_complex:.2f}s")
    
    # Return a score based on installation speed and success rate
    success_count = sum(1 for data in results.values() if data['success'])
    success_rate = success_count / len(results) if results else 0
    
    return results

@benchmark_timer
def timed_test():
    return run_package_tests()

# Run the benchmark
test_result = timed_test()

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