def test_resource_intensive_calculation():
    return """import hashlib
from concurrent.futures import ThreadPoolExecutor
import random

def cpu_intensive_task():
    # Prime number calculation and hash computation
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True

    # Find primes and calculate hashes
    current_hash = '0'  # Initialize with a string
    for i in range(10000, 15000):
        if is_prime(i):
            current_hash = hashlib.sha256((current_hash + str(i)).encode()).hexdigest()
    return current_hash

def memory_intensive_task():
    # Create large lists and perform operations
    size = 15000
    lists = []
    for i in range(1000):
        # Create and manipulate lists
        new_list = list(range(i, i + size))
        reversed_list = list(reversed(new_list))
        sorted_list = sorted(new_list, reverse=True)
        lists.append(new_list)
        lists.append(reversed_list)
        lists.append(sorted_list)

    # Perform operations on lists
    result = 0
    for lst in lists:
        result += sum(lst[::2])  # Sum every second element
    return result

def alternative_cpu_task():
    # Calculate factorial and its hash
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    result = 0
    for i in range(50, 60):
        fact = factorial(i)
        result = int(str(result) + str(fact % 1000000))
    return hashlib.sha256(str(result).encode()).hexdigest()

# Run CPU and memory intensive tasks in parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    future_cpu1 = executor.submit(cpu_intensive_task)
    future_memory = executor.submit(memory_intensive_task)
    future_cpu2 = executor.submit(alternative_cpu_task)

    cpu_result1 = future_cpu1.result()
    memory_result = future_memory.result()
    cpu_result2 = future_cpu2.result()

print(f"CPU Task 1 Result (Prime numbers + SHA-256): {cpu_result1[:20]}...")
print(f"Memory Task Result (List operations sum): {memory_result}")
print(f"CPU Task 2 Result (Factorial + SHA-256): {cpu_result2[:20]}...")
"""
