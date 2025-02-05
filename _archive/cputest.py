import multiprocessing
import time
import os
from concurrent.futures import ProcessPoolExecutor
import math
import tempfile
import random
import json
import array

def generate_large_data(size_mb):
    """Generate large data to fill RAM using efficient array storage"""
    num_elements = int((size_mb * 1024 * 1024) / 8)
    arr = array.array('d', [0.0]) * num_elements
    for i in range(num_elements):
        arr[i] = random.random()
    return arr

def cpu_ram_disk_intensive_task(args):
    """Combined CPU, RAM, and disk intensive task"""
    iterations, core_num, ram_mb, temp_dir = args

    try:
        os.sched_setaffinity(0, {core_num})
    except AttributeError:
        pass

    start_time = time.time()
    result = 0
    temp_file = os.path.join(temp_dir, f'process_{core_num}_data.tmp')

    try:
        # RAM intensive part
        large_data = generate_large_data(ram_mb)

        # CPU intensive calculations
        for i in range(iterations):
            # More intensive mathematical operations
            for j in range(2000):
                x = i * j
                result += math.sqrt((x ** 2) + math.exp(math.sin(x)))
                result += math.cos(math.atan2(x, x+1) if x != 0 else 1)

                # Replace prime check with more math operations
                for _ in range(10):
                    result += math.log(abs(x) + 1) * math.tanh(x+1)

            # RAM manipulation
            if i % 50 == 0:
                idx = i % len(large_data)
                large_data[idx] = result * random.random()

            # Disk I/O
            if i % 200 == 0:
                data_to_write = {
                    'iteration': i,
                    'result': result,
                    'data': large_data[:20000].tolist()  # Write more data
                }
                with open(temp_file, 'a') as f:
                    json.dump(data_to_write, f)
                    f.write('\n')

                # Read verification
                with open(temp_file, 'r') as f:
                    f.seek(0)
                    for line in f:
                        pass  # Simple read verification

    except Exception as e:
        return {'core': core_num, 'time': 0, 'error': str(e)}
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    end_time = time.time()
    return {
        'core': core_num,
        'time': end_time - start_time,
        'result': result
    }

def main():
    # Configuration
    num_cores = multiprocessing.cpu_count()
    iterations = 8000  # Increased CPU workload
    ram_per_core_mb = 500  # MB of RAM per core

    print(f"Starting stress test with {num_cores} cores, {iterations} iterations/core, {ram_per_core_mb}MB RAM/core")

    temp_dir = tempfile.mkdtemp()

    try:
        args = [(iterations, core_num, ram_per_core_mb, temp_dir)
                for core_num in range(num_cores)]

        total_start_time = time.time()

        with ProcessPoolExecutor(max_workers=num_cores) as executor:
            results = list(executor.map(cpu_ram_disk_intensive_task, args))

        total_time = time.time() - total_start_time

        print("\nResults:")
        total = 0
        for result in results:
            t = result.get('time', 0)
            total += t
            print(f"Core {result['core']}: {t:.2f}s",
                  f"Error: {result['error']}" if 'error' in result else "")

        print(f"\nTotal: {total_time:.2f}s | Avg/core: {total/len(results):.2f}s")

    finally:
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except:
            pass

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")