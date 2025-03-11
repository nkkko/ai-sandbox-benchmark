"""
Test that measures Python startup time for various import scenarios.

This test evaluates how quickly Python starts up in the sandbox under different
conditions, including with standard libraries and popular packages.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_startup_time():
    """
    Measures Python startup time for various import scenarios.
    
    This test:
    - Measures basic Python interpreter startup time
    - Tests startup with various standard library imports
    - Evaluates startup time for scientific libraries (NumPy, Pandas)
    - Checks startup time for ML/AI libraries (TensorFlow, PyTorch)
    - Tests web framework and database library startup times
    - Reports comprehensive timing information
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=True,  # Only run once per benchmark session
        is_info_test=True  # This is more of an informational test
    )
    
    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=False,  # We'll handle timing manually in this test
        include_results=False,  # We'll format results manually
        include_packages=False  # We don't need to install packages for this test itself
    )
    
    # Define the test-specific code
    test_code = """
import time
import os
import sys
import subprocess
import platform
import json
from datetime import datetime

def measure_python_startup():
    # Measure basic Python interpreter startup time
    start_time = time.time()
    # Run a minimal Python program
    subprocess.run([sys.executable, "-c", "print('hello')"], 
                   stdout=subprocess.PIPE, 
                   stderr=subprocess.PIPE)
    end_time = time.time()
    return end_time - start_time

def measure_python_with_imports():
    # Measure Python startup with common imports
    script = '''
import sys
import os
import time
import json
import random
import math
import datetime
import re
import collections
import itertools
print('Imports completed')
'''
    start_time = time.time()
    subprocess.run([sys.executable, "-c", script],
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)
    end_time = time.time()
    return end_time - start_time

def measure_numpy_startup():
    # Measure startup time with NumPy import
    script = '''
try:
    import numpy as np
    print(f"NumPy version: {np.__version__}")
except ImportError:
    print("NumPy not installed")
'''
    start_time = time.time()
    result = subprocess.run([sys.executable, "-c", script],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    end_time = time.time()
    output = result.stdout.decode()
    error = result.stderr.decode()
    
    if "not installed" in output:
        return None, "NumPy not installed"
    if result.returncode != 0:
        return None, error
    return end_time - start_time, output

def measure_pandas_startup():
    # Measure startup time with Pandas import
    script = '''
try:
    import pandas as pd
    print(f"Pandas version: {pd.__version__}")
except ImportError:
    print("Pandas not installed")
'''
    start_time = time.time()
    result = subprocess.run([sys.executable, "-c", script],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    end_time = time.time()
    output = result.stdout.decode()
    error = result.stderr.decode()
    
    if "not installed" in output:
        return None, "Pandas not installed"
    if result.returncode != 0:
        return None, error
    return end_time - start_time, output

def measure_tensorflow_startup():
    # Measure startup time with TensorFlow import
    script = '''
try:
    import tensorflow as tf
    print(f"TensorFlow version: {tf.__version__}")
except ImportError:
    print("TensorFlow not installed")
'''
    start_time = time.time()
    result = subprocess.run([sys.executable, "-c", script],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    end_time = time.time()
    output = result.stdout.decode()
    error = result.stderr.decode()
    
    if "not installed" in output:
        return None, "TensorFlow not installed"
    if result.returncode != 0:
        return None, error
    return end_time - start_time, output

def measure_pytorch_startup():
    # Measure startup time with PyTorch import
    script = '''
try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
except ImportError:
    print("PyTorch not installed")
'''
    start_time = time.time()
    result = subprocess.run([sys.executable, "-c", script],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    end_time = time.time()
    output = result.stdout.decode()
    error = result.stderr.decode()
    
    if "not installed" in output:
        return None, "PyTorch not installed"
    if result.returncode != 0:
        return None, error
    return end_time - start_time, output

def measure_web_framework_startup():
    # Measure startup time with a web framework (Flask)
    script = '''
try:
    import flask
    print(f"Flask version: {flask.__version__}")
except ImportError:
    print("Flask not installed")
'''
    start_time = time.time()
    result = subprocess.run([sys.executable, "-c", script],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    end_time = time.time()
    output = result.stdout.decode()
    error = result.stderr.decode()
    
    if "not installed" in output:
        return None, "Flask not installed"
    if result.returncode != 0:
        return None, error
    return end_time - start_time, output

def measure_database_startup():
    # Measure startup time with database library (SQLAlchemy)
    script = '''
try:
    import sqlalchemy
    print(f"SQLAlchemy version: {sqlalchemy.__version__}")
except ImportError:
    print("SQLAlchemy not installed")
'''
    start_time = time.time()
    result = subprocess.run([sys.executable, "-c", script],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    end_time = time.time()
    output = result.stdout.decode()
    error = result.stderr.decode()
    
    if "not installed" in output:
        return None, "SQLAlchemy not installed"
    if result.returncode != 0:
        return None, error
    return end_time - start_time, output

def measure_virtual_env_activation():
    # Test if we're in a virtual environment and measure activation impact
    is_venv = sys.prefix != sys.base_prefix
    venv_path = sys.prefix if is_venv else None
    
    return {
        "in_virtual_env": is_venv,
        "virtual_env_path": venv_path
    }

def get_system_info():
    # Gather system information
    return {
        "platform": platform.platform(),
        "python_version": sys.version,
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "timestamp": datetime.now().isoformat()
    }

def run_startup_time_tests():
    print("\\n=== Startup Time Benchmark ===")
    print("Measuring various startup scenarios...")
    
    # Collect results
    results = {}
    
    # Get system info
    system_info = get_system_info()
    results["system_info"] = system_info
    print(f"\\nSystem Information:")
    print(f"  Platform: {system_info['platform']}")
    print(f"  Python: {system_info['python_version'].split()[0]}")
    print(f"  Processor: {system_info['processor']}")
    print(f"  CPU cores: {system_info['cpu_count']}")
    
    # Check virtual environment
    venv_info = measure_virtual_env_activation()
    results["virtual_environment"] = venv_info
    if venv_info["in_virtual_env"]:
        print(f"\\nRunning in virtual environment: {venv_info['virtual_env_path']}")
    else:
        print(f"\\nRunning in system Python (not in a virtual environment)")
    
    # Basic Python startup
    print("\\n1. Basic Python Startup")
    basic_time = measure_python_startup()
    results["basic_python"] = basic_time
    print(f"  Python interpreter startup time: {basic_time:.4f}s")
    
    # Python with standard imports
    std_imports_time = measure_python_with_imports()
    results["standard_imports"] = std_imports_time
    print(f"  Python with standard imports: {std_imports_time:.4f}s")
    
    # NumPy startup
    print("\\n2. Scientific Libraries Startup")
    numpy_result = measure_numpy_startup()
    if isinstance(numpy_result, tuple):
        numpy_time, numpy_output = numpy_result
        results["numpy"] = {"time": numpy_time, "version": numpy_output.strip()}
        print(f"  NumPy import time: {numpy_time:.4f}s - {numpy_output.strip()}")
    else:
        results["numpy"] = {"error": numpy_result}
        print(f"  NumPy import failed: {numpy_result}")
    
    # Pandas startup
    pandas_result = measure_pandas_startup()
    if isinstance(pandas_result, tuple):
        pandas_time, pandas_output = pandas_result
        results["pandas"] = {"time": pandas_time, "version": pandas_output.strip()}
        print(f"  Pandas import time: {pandas_time:.4f}s - {pandas_output.strip()}")
    else:
        results["pandas"] = {"error": pandas_result}
        print(f"  Pandas import failed: {pandas_result}")
    
    # ML/AI libraries
    print("\\n3. ML/AI Libraries Startup")
    
    # TensorFlow startup
    tf_result = measure_tensorflow_startup()
    if isinstance(tf_result, tuple):
        tf_time, tf_output = tf_result
        if tf_time is not None:
            results["tensorflow"] = {"time": tf_time, "version": tf_output.strip()}
            print(f"  TensorFlow import time: {tf_time:.4f}s - {tf_output.strip()}")
        else:
            results["tensorflow"] = {"error": tf_output}
            print(f"  TensorFlow: {tf_output}")
    else:
        results["tensorflow"] = {"error": tf_result}
        print(f"  TensorFlow import failed: {tf_result}")
    
    # PyTorch startup
    torch_result = measure_pytorch_startup()
    if isinstance(torch_result, tuple):
        torch_time, torch_output = torch_result
        if torch_time is not None:
            results["pytorch"] = {"time": torch_time, "version": torch_output.strip()}
            print(f"  PyTorch import time: {torch_time:.4f}s - {torch_output.strip()}")
        else:
            results["pytorch"] = {"error": torch_output}
            print(f"  PyTorch: {torch_output}")
    else:
        results["pytorch"] = {"error": torch_result}
        print(f"  PyTorch import failed: {torch_result}")
    
    # Web framework startup
    print("\\n4. Web Framework Startup")
    flask_result = measure_web_framework_startup()
    if isinstance(flask_result, tuple):
        flask_time, flask_output = flask_result
        if flask_time is not None:
            results["flask"] = {"time": flask_time, "version": flask_output.strip()}
            print(f"  Flask import time: {flask_time:.4f}s - {flask_output.strip()}")
        else:
            results["flask"] = {"error": flask_output}
            print(f"  Flask: {flask_output}")
    else:
        results["flask"] = {"error": flask_result}
        print(f"  Flask import failed: {flask_result}")
    
    # Database library startup
    print("\\n5. Database Library Startup")
    db_result = measure_database_startup()
    if isinstance(db_result, tuple):
        db_time, db_output = db_result
        if db_time is not None:
            results["sqlalchemy"] = {"time": db_time, "version": db_output.strip()}
            print(f"  SQLAlchemy import time: {db_time:.4f}s - {db_output.strip()}")
        else:
            results["sqlalchemy"] = {"error": db_output}
            print(f"  SQLAlchemy: {db_output}")
    else:
        results["sqlalchemy"] = {"error": db_result}
        print(f"  SQLAlchemy import failed: {db_result}")
    
    # Summary
    print("\\n=== Startup Time Summary ===")
    print(f"Basic Python: {results.get('basic_python', 'N/A'):.4f}s")
    print(f"With standard imports: {results.get('standard_imports', 'N/A'):.4f}s")
    
    # Calculate averages for scientific libraries
    sci_libs = []
    if 'numpy' in results and isinstance(results['numpy'], dict) and 'time' in results['numpy']:
        sci_libs.append(results['numpy']['time'])
    if 'pandas' in results and isinstance(results['pandas'], dict) and 'time' in results['pandas']:
        sci_libs.append(results['pandas']['time'])
    
    if sci_libs:
        avg_sci_time = sum(sci_libs) / len(sci_libs)
        print(f"Average scientific library import: {avg_sci_time:.4f}s")
    
    # Calculate averages for ML/AI libraries
    ml_libs = []
    if 'tensorflow' in results and isinstance(results['tensorflow'], dict) and 'time' in results['tensorflow']:
        ml_libs.append(results['tensorflow']['time'])
    if 'pytorch' in results and isinstance(results['pytorch'], dict) and 'time' in results['pytorch']:
        ml_libs.append(results['pytorch']['time'])
    
    if ml_libs:
        avg_ml_time = sum(ml_libs) / len(ml_libs)
        print(f"Average ML/AI library import: {avg_ml_time:.4f}s")
    
    # Export results as JSON
    try:
        results_str = json.dumps(results, indent=2, default=str)
        print(f"\\nResults as JSON:\\n{results_str}")
    except Exception as e:
        print(f"Could not serialize results to JSON: {e}")
    
    return results

# Run the startup time tests
results = run_startup_time_tests()

# Record timing information for benchmark
print("\\n\\n--- BENCHMARK TIMING DATA ---")
print(json.dumps({
    "internal_execution_time_ms": results.get('standard_imports', 0) * 1000  # Use standard imports time as the benchmark
}))
print("--- END BENCHMARK TIMING DATA ---")
"""

    # Combine the utilities and test code
    full_code = f"{utils_code}\n\n{test_code}"

    # Return the test configuration and code
    return {
        "config": config,
        "code": full_code
    }