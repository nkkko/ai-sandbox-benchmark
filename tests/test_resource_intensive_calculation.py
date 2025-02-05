def test_resource_intensive_calculation():
    return """import hashlib
import os
import random
import string
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

#################
# CPU-intensive task (Increased range)
def cpu_intensive_task():
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True

    current_hash = "0"
    # Increase the range to apply more load.
    for i in range(10000, 25000):
        if is_prime(i):
            current_hash = hashlib.sha256((current_hash + str(i)).encode()).hexdigest()
    return current_hash

# Alternative CPU-intensive task (Increased computations)
def alternative_cpu_task():
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    result = 0
    # Increase range to compute more factorials.
    for i in range(50, 70):
        fact = factorial(i)
        result = int(str(result) + str(fact % 1000000))
    return hashlib.sha256(str(result).encode()).hexdigest()

#################
# Memory-intensive task (Increase data size)
def memory_intensive_task():
    size = 20000  # increased size of each list
    lists = []
    # Increase number of iterations to create more data in memory
    for i in range(1500):
        new_list = list(range(i, i + size))
        reversed_list = list(reversed(new_list))
        sorted_list = sorted(new_list, reverse=True)
        lists.extend([new_list, reversed_list, sorted_list])
    result = 0
    for lst in lists:
        result += sum(lst[::2])
    return result

#################
# HDD-intensive task (Write a larger file)
def hdd_intensive_task():
    with tempfile.TemporaryDirectory() as tmpdirname:
        file_path = os.path.join(tmpdirname, "test_disk.txt")
        # Increase file size by generating a 2MB chunk and writing it 10 times (20MB total)
        data_chunk = ''.join(random.choices(string.ascii_letters + string.digits, k=2 * 1024 * 1024))
        try:
            with open(file_path, "w") as f:
                for _ in range(10):
                    f.write(data_chunk)
        except IOError as e:
            return f"File write error: {e}"

        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha.update(chunk)
        except IOError as e:
            return f"File read error: {e}"
        return sha.hexdigest()

#################
# Running multiple tasks concurrently to further increase load.
def run_resource_intensive_tests():
    tasks = []
    # Increase the number of tasks: 3 instances of each task.
    with ThreadPoolExecutor(max_workers=12) as executor:
        for _ in range(3):
            tasks.append(executor.submit(cpu_intensive_task))
            tasks.append(executor.submit(alternative_cpu_task))
            tasks.append(executor.submit(memory_intensive_task))
            tasks.append(executor.submit(hdd_intensive_task))

        for future in as_completed(tasks):
            result = future.result()
            # For CPU and disk I/O tasks, print a partial hash.
            if isinstance(result, str) and len(result) > 20:
                print(result[:20] + "...")
            else:
                print(result)

if __name__ == "__main__":
    run_resource_intensive_tests()
"""
