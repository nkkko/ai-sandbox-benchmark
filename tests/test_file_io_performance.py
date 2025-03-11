"""
Test that measures file I/O performance by reading and writing various file types.

This test evaluates the sandbox environment's file system performance by measuring
read and write speeds for binary, JSON, and CSV files of different sizes.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_file_io_performance():
    """
    Measures file I/O performance by reading and writing various file types.
    
    This test evaluates:
    - Binary file read/write performance for different file sizes
    - JSON file read/write performance with different record counts
    - CSV file read/write performance with different record counts
    - Concurrent file operations performance
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=True,  # Only need to run once per benchmark session
    )
    
    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=False,  # We'll handle timing manually in this test
        include_results=False,  # We'll format results manually
        include_packages=False  # No external packages needed
    )
    
    # Define the test-specific code
    test_code = """
import os
import time
import json
import csv
import tempfile
import random
from concurrent.futures import ThreadPoolExecutor

# Configure test parameters
FILE_SIZES = [1, 10, 100]  # File sizes in MB
NUM_FILES = 5  # Number of files per size
CONCURRENT_OPERATIONS = 3  # Number of concurrent file operations

def generate_random_data(size_mb):
    # Generate random string data of specified size in MB
    # Generate random bytes (1 MB = 1,048,576 bytes)
    return os.urandom(size_mb * 1024 * 1024)

def write_binary_file(file_path, data):
    # Write binary data to a file and measure performance
    start_time = time.time()
    with open(file_path, 'wb') as f:
        f.write(data)
    elapsed = time.time() - start_time
    return elapsed, len(data)

def read_binary_file(file_path):
    # Read binary data from a file and measure performance
    start_time = time.time()
    with open(file_path, 'rb') as f:
        data = f.read()
    elapsed = time.time() - start_time
    return elapsed, len(data)

def write_json_file(file_path, num_records):
    # Generate and write JSON data to a file
    # Create sample data
    data = []
    for i in range(num_records):
        record = {
            'id': i,
            'name': f'Item {i}',
            'value': random.random() * 1000,
            'tags': [f'tag{j}' for j in range(random.randint(1, 5))],
            'properties': {
                'color': random.choice(['red', 'green', 'blue', 'yellow']),
                'size': random.choice(['small', 'medium', 'large']),
                'active': random.choice([True, False])
            }
        }
        data.append(record)
    
    # Write JSON file
    start_time = time.time()
    with open(file_path, 'w') as f:
        json.dump(data, f)
    elapsed = time.time() - start_time
    
    return elapsed, len(data)

def read_json_file(file_path):
    # Read and parse JSON data from a file
    start_time = time.time()
    with open(file_path, 'r') as f:
        data = json.load(f)
    elapsed = time.time() - start_time
    
    return elapsed, len(data)

def write_csv_file(file_path, num_records):
    # Generate and write CSV data to a file
    # Create sample data
    headers = ['id', 'name', 'value', 'category', 'active']
    rows = []
    for i in range(num_records):
        row = [
            i,
            f'Product {i}',
            round(random.random() * 1000, 2),
            random.choice(['A', 'B', 'C', 'D']),
            random.choice(['Yes', 'No'])
        ]
        rows.append(row)
    
    # Write CSV file
    start_time = time.time()
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    elapsed = time.time() - start_time
    
    return elapsed, len(rows)

def read_csv_file(file_path):
    # Read and parse CSV data from a file
    start_time = time.time()
    rows = []
    with open(file_path, 'r', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip header
        for row in reader:
            rows.append(row)
    elapsed = time.time() - start_time
    
    return elapsed, len(rows)

def concurrent_file_operations(operation_func, file_paths):
    # Run file operations concurrently
    results = []
    with ThreadPoolExecutor(max_workers=CONCURRENT_OPERATIONS) as executor:
        future_to_file = {executor.submit(operation_func, file_path): file_path for file_path in file_paths}
        for future in future_to_file:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Operation failed: {e}")
    return results

def run_file_io_tests():
    # Run all file I/O performance tests
    results = {
        'binary': {'write': {}, 'read': {}},
        'json': {'write': {}, 'read': {}},
        'csv': {'write': {}, 'read': {}},
        'concurrent': {'write': {}, 'read': {}}
    }
    
    print("\\n=== File I/O Performance Tests ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test binary file operations
        print("\\n1. Testing Binary File I/O")
        for size_mb in FILE_SIZES:
            binary_files = []
            binary_write_times = []
            
            # Generate and write binary files
            for i in range(NUM_FILES):
                file_path = os.path.join(temp_dir, f'binary_{size_mb}mb_{i}.bin')
                data = generate_random_data(size_mb)
                elapsed, data_size = write_binary_file(file_path, data)
                binary_files.append(file_path)
                binary_write_times.append(elapsed)
                print(f"  - Wrote {size_mb}MB binary file in {elapsed:.4f}s ({data_size / elapsed / 1024 / 1024:.2f} MB/s)")
            
            # Read binary files
            binary_read_times = []
            for file_path in binary_files:
                elapsed, data_size = read_binary_file(file_path)
                binary_read_times.append(elapsed)
                print(f"  - Read {size_mb}MB binary file in {elapsed:.4f}s ({data_size / elapsed / 1024 / 1024:.2f} MB/s)")
            
            # Store results
            results['binary']['write'][size_mb] = sum(binary_write_times) / len(binary_write_times)
            results['binary']['read'][size_mb] = sum(binary_read_times) / len(binary_read_times)
        
        # Test JSON file operations
        print("\\n2. Testing JSON File I/O")
        json_sizes = [1000, 10000, 100000]  # Number of records
        for num_records in json_sizes:
            json_files = []
            json_write_times = []
            
            # Generate and write JSON files
            for i in range(NUM_FILES):
                file_path = os.path.join(temp_dir, f'data_{num_records}_{i}.json')
                elapsed, records = write_json_file(file_path, num_records)
                json_files.append(file_path)
                json_write_times.append(elapsed)
                print(f"  - Wrote JSON file with {records} records in {elapsed:.4f}s")
            
            # Read JSON files
            json_read_times = []
            for file_path in json_files:
                elapsed, records = read_json_file(file_path)
                json_read_times.append(elapsed)
                print(f"  - Read JSON file with {records} records in {elapsed:.4f}s")
            
            # Store results
            results['json']['write'][num_records] = sum(json_write_times) / len(json_write_times)
            results['json']['read'][num_records] = sum(json_read_times) / len(json_read_times)
        
        # Test CSV file operations
        print("\\n3. Testing CSV File I/O")
        csv_sizes = [1000, 10000, 100000]  # Number of records
        for num_records in csv_sizes:
            csv_files = []
            csv_write_times = []
            
            # Generate and write CSV files
            for i in range(NUM_FILES):
                file_path = os.path.join(temp_dir, f'data_{num_records}_{i}.csv')
                elapsed, records = write_csv_file(file_path, num_records)
                csv_files.append(file_path)
                csv_write_times.append(elapsed)
                print(f"  - Wrote CSV file with {records} records in {elapsed:.4f}s")
            
            # Read CSV files
            csv_read_times = []
            for file_path in csv_files:
                elapsed, records = read_csv_file(file_path)
                csv_read_times.append(elapsed)
                print(f"  - Read CSV file with {records} records in {elapsed:.4f}s")
            
            # Store results
            results['csv']['write'][num_records] = sum(csv_write_times) / len(csv_write_times)
            results['csv']['read'][num_records] = sum(csv_read_times) / len(csv_read_times)
        
        # Test concurrent file operations
        print("\\n4. Testing Concurrent File Operations")
        # Test concurrent binary write
        concurrent_files = []
        for i in range(CONCURRENT_OPERATIONS):
            file_path = os.path.join(temp_dir, f'concurrent_binary_{i}.bin')
            concurrent_files.append(file_path)
        
        data = generate_random_data(10)  # 10MB for each file
        start_time = time.time()
        concurrent_file_operations(lambda fp: write_binary_file(fp, data), concurrent_files)
        concurrent_write_time = time.time() - start_time
        print(f"  - Wrote {CONCURRENT_OPERATIONS} binary files concurrently in {concurrent_write_time:.4f}s")
        
        # Test concurrent binary read
        start_time = time.time()
        concurrent_file_operations(read_binary_file, concurrent_files)
        concurrent_read_time = time.time() - start_time
        print(f"  - Read {CONCURRENT_OPERATIONS} binary files concurrently in {concurrent_read_time:.4f}s")
        
        # Store results
        results['concurrent']['write']['10mb'] = concurrent_write_time
        results['concurrent']['read']['10mb'] = concurrent_read_time
    
    # Print summary
    print("\\n=== File I/O Performance Summary ===")
    print("Binary File Operations:")
    for size_mb in FILE_SIZES:
        write_speed = size_mb / results['binary']['write'][size_mb]
        read_speed = size_mb / results['binary']['read'][size_mb]
        print(f"  - {size_mb}MB: Write: {write_speed:.2f} MB/s, Read: {read_speed:.2f} MB/s")
    
    print("\\nJSON File Operations:")
    for size in json_sizes:
        print(f"  - {size} records: Write: {results['json']['write'][size]:.4f}s, Read: {results['json']['read'][size]:.4f}s")
    
    print("\\nCSV File Operations:")
    for size in csv_sizes:
        print(f"  - {size} records: Write: {results['csv']['write'][size]:.4f}s, Read: {results['csv']['read'][size]:.4f}s")
    
    print("\\nConcurrent File Operations:")
    print(f"  - {CONCURRENT_OPERATIONS} files (10MB each): Write: {results['concurrent']['write']['10mb']:.4f}s, Read: {results['concurrent']['read']['10mb']:.4f}s")
    
    return results

# Run the file I/O tests
results = run_file_io_tests()

# Record timing information for benchmark
# Use the average of binary file read/write times for the medium size (10MB)
binary_write_time = results['binary']['write'].get(10, 0) * 1000  # Convert to ms
binary_read_time = results['binary']['read'].get(10, 0) * 1000    # Convert to ms
avg_binary_time = (binary_write_time + binary_read_time) / 2

print("\\n\\n--- BENCHMARK TIMING DATA ---")
print(json.dumps({
    "internal_execution_time_ms": avg_binary_time
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