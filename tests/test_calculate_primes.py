def test_calculate_primes():
    return """def calculate_primes():
    primes = []
    num = 2
    while len(primes) < 10:
        is_prime = True
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
        num += 1
    prime_sum = sum(primes)
    prime_avg = prime_sum / len(primes)
    return f"Primes: {primes}\\nSum: {prime_sum}\\nAverage: {prime_avg}"

print(calculate_primes())
"""