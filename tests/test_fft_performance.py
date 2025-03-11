def test_fft_performance():
    return """import numpy as np
from scipy import fft
import time

def run_fft_benchmark():
    t = time.time()
    [fft.fft2(np.random.random((10000, 10000))) for _ in range(2)]
    elapsed = time.time() - t
    return f'FFT Performance Time: {elapsed:.2f}s'

print(run_fft_benchmark())
"""