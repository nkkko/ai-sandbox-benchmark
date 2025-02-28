def test_container_stability():
    # This test should only run once per provider
    test_container_stability.single_run = True
    return """import time
import os
import signal
import threading
import queue
import psutil
import datetime
import json
import sys
from concurrent.futures import ThreadPoolExecutor
import resource

# Configuration
DURATION = 300  # Test duration in seconds (5 minutes)
MEASUREMENT_INTERVAL = 5  # Measure resource usage every 5 seconds
MAX_CPU_LOAD = 0.75  # Target CPU load for stress test (75%)
MEMORY_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks for memory test
DISK_IO_SIZE = 50 * 1024 * 1024  # 50MB for disk I/O test

class ResourceMonitor:
    def __init__(self, interval=1):
        self.interval = interval
        self.process = psutil.Process(os.getpid())
        self.stop_flag = threading.Event()
        self.measurements = []
        self.measurement_thread = None
        self.results_queue = queue.Queue()
    
    def measure_resources(self):
        try:
            timestamp = datetime.datetime.now().isoformat()
            
            # CPU measurements
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # Memory measurements
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # Disk measurements
            io_counters = psutil.disk_io_counters()
            
            # System-wide measurements
            system_cpu = psutil.cpu_percent(interval=0.1)
            system_memory = psutil.virtual_memory()
            
            # Get resource limits
            max_open_files = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            current_open_files = len(self.process.open_files())
            
            # System load average (not available on Windows)
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
            
            measurement = {
                'timestamp': timestamp,
                'cpu': {
                    'process_percent': cpu_percent,
                    'system_percent': system_cpu
                },
                'memory': {
                    'rss': memory_info.rss,
                    'vms': memory_info.vms,
                    'percent': memory_percent,
                    'system_percent': system_memory.percent,
                    'system_available': system_memory.available
                },
                'disk': {
                    'read_count': io_counters.read_count if io_counters else 0,
                    'write_count': io_counters.write_count if io_counters else 0,
                    'read_bytes': io_counters.read_bytes if io_counters else 0,
                    'write_bytes': io_counters.write_bytes if io_counters else 0
                },
                'files': {
                    'open_files': current_open_files,
                    'max_files': max_open_files
                },
                'system': {
                    'load_avg_1min': load_avg[0],
                    'load_avg_5min': load_avg[1],
                    'load_avg_15min': load_avg[2]
                }
            }
            
            return measurement
            
        except Exception as e:
            return {'error': str(e), 'timestamp': datetime.datetime.now().isoformat()}
    
    def monitoring_loop(self):
        start_time = time.time()
        last_measure_time = start_time
        
        while not self.stop_flag.is_set():
            current_time = time.time()
            
            # Check if it's time to measure
            if current_time - last_measure_time >= self.interval:
                measurement = self.measure_resources()
                self.measurements.append(measurement)
                self.results_queue.put(measurement)
                last_measure_time = current_time
            
            # Sleep a short time to prevent maxing out CPU
            time.sleep(0.1)
    
    def start(self):
        if self.measurement_thread is None or not self.measurement_thread.is_alive():
            self.stop_flag.clear()
            self.measurement_thread = threading.Thread(target=self.monitoring_loop)
            self.measurement_thread.daemon = True
            self.measurement_thread.start()
    
    def stop(self):
        if self.measurement_thread and self.measurement_thread.is_alive():
            self.stop_flag.set()
            self.measurement_thread.join(timeout=5)
    
    def get_statistics(self):
        if not self.measurements:
            return {"error": "No measurements collected"}
        
        # CPU statistics
        cpu_values = [m['cpu']['process_percent'] for m in self.measurements if 'cpu' in m]
        system_cpu_values = [m['cpu']['system_percent'] for m in self.measurements if 'cpu' in m]
        
        # Memory statistics
        rss_values = [m['memory']['rss'] for m in self.measurements if 'memory' in m]
        percent_values = [m['memory']['percent'] for m in self.measurements if 'memory' in m]
        
        # Calculate statistics
        stats = {
            "cpu": {
                "min": min(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0
            },
            "system_cpu": {
                "min": min(system_cpu_values) if system_cpu_values else 0,
                "max": max(system_cpu_values) if system_cpu_values else 0,
                "avg": sum(system_cpu_values) / len(system_cpu_values) if system_cpu_values else 0
            },
            "memory_rss": {
                "min": min(rss_values) if rss_values else 0,
                "max": max(rss_values) if rss_values else 0,
                "avg": sum(rss_values) / len(rss_values) if rss_values else 0,
                "peak": max(rss_values) if rss_values else 0,
                "end": rss_values[-1] if rss_values else 0
            },
            "memory_percent": {
                "min": min(percent_values) if percent_values else 0,
                "max": max(percent_values) if percent_values else 0,
                "avg": sum(percent_values) / len(percent_values) if percent_values else 0
            },
            "measurements_count": len(self.measurements),
            "duration": self.measurements[-1]['timestamp'] if self.measurements else None
        }
        
        return stats

def cpu_load_generator(target_load, duration):
    """Generate CPU load targeting a specific percentage for a duration"""
    print(f"Starting CPU load test targeting {target_load*100:.0f}% for {duration}s")
    end_time = time.time() + duration
    
    # Function to keep a core busy
    def cpu_intensive_task():
        while time.time() < end_time:
            # Busy work to load CPU
            _ = [i**2 for i in range(10000)]
    
    # Function to sleep and maintain target load
    def controlled_cpu_load():
        while time.time() < end_time:
            start_cycle = time.time()
            
            # Do busy work for target_load portion of a second
            busy_end = start_cycle + target_load
            while time.time() < busy_end and time.time() < end_time:
                _ = [i**2 for i in range(1000)]
            
            # Sleep for the remainder
            sleep_time = 1.0 - (time.time() - start_cycle)
            if sleep_time > 0 and time.time() < end_time:
                time.sleep(sleep_time)
    
    # Launch threads based on CPU cores
    threads = []
    num_cores = psutil.cpu_count(logical=True)
    
    for _ in range(num_cores):
        thread = threading.Thread(target=controlled_cpu_load)
        thread.daemon = True
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"CPU load test completed")

def memory_pressure_test(duration, chunk_size):
    """Test memory allocation and de-allocation under pressure"""
    print(f"Starting memory pressure test for {duration}s")
    end_time = time.time() + duration
    memory_chunks = []
    
    try:
        while time.time() < end_time:
            # Allocate memory in chunks
            memory_chunks.append(bytearray(chunk_size))
            
            # Periodically release some memory to simulate real usage patterns
            if len(memory_chunks) % 10 == 0:
                # Release half the chunks
                chunk_count = len(memory_chunks)
                for _ in range(chunk_count // 2):
                    if memory_chunks:
                        memory_chunks.pop()
                
                # Sleep a bit to give system time to reclaim
                time.sleep(0.1)
            
            # Small sleep to prevent tight loop
            time.sleep(0.01)
    
    except MemoryError:
        print("Memory allocation limit reached - test stopped early")
    
    # Clear all memory chunks
    memory_chunks.clear()
    print(f"Memory pressure test completed")

def disk_io_test(duration, file_size):
    """Test disk I/O operations under sustained load"""
    print(f"Starting disk I/O test for {duration}s")
    end_time = time.time() + duration
    
    # Create a temporary file
    temp_file_path = os.path.join(os.path.dirname(__file__), "temp_io_test.bin")
    
    try:
        bytes_written = 0
        bytes_read = 0
        cycles = 0
        
        while time.time() < end_time:
            # Write data
            with open(temp_file_path, "wb") as f:
                data = os.urandom(file_size)
                f.write(data)
                bytes_written += len(data)
            
            # Read data
            with open(temp_file_path, "rb") as f:
                data = f.read()
                bytes_read += len(data)
            
            cycles += 1
            
            # Sleep briefly to prevent tight loop
            time.sleep(0.1)
        
        print(f"Disk I/O test completed: {cycles} cycles, {bytes_written / (1024*1024):.2f} MB written, {bytes_read / (1024*1024):.2f} MB read")
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def combined_stability_test():
    """Run multiple tests in parallel to test overall container stability"""
    print(f"Starting combined stability test for {DURATION}s")
    
    # Set up resource monitoring
    monitor = ResourceMonitor(interval=MEASUREMENT_INTERVAL)
    monitor.start()
    
    # Use thread pool to run tests concurrently
    with ThreadPoolExecutor(max_workers=3) as executor:
        cpu_future = executor.submit(cpu_load_generator, MAX_CPU_LOAD, DURATION)
        memory_future = executor.submit(memory_pressure_test, DURATION, MEMORY_CHUNK_SIZE)
        disk_future = executor.submit(disk_io_test, DURATION, DISK_IO_SIZE)
        
        # Wait for all tests to complete
        for future in [cpu_future, memory_future, disk_future]:
            try:
                future.result()
            except Exception as e:
                print(f"Test failed with error: {e}")
    
    # Stop monitoring
    monitor.stop()
    
    # Calculate statistics
    statistics = monitor.get_statistics()
    
    # Print results
    print("\\n=== Container Stability Test Results ===")
    print(f"Test duration: {DURATION} seconds")
    print(f"Measurements taken: {statistics['measurements_count']}")
    
    print("\\nCPU Usage:")
    print(f"  Min: {statistics['cpu']['min']:.2f}%")
    print(f"  Max: {statistics['cpu']['max']:.2f}%")
    print(f"  Avg: {statistics['cpu']['avg']:.2f}%")
    
    print("\\nMemory Usage:")
    print(f"  Min: {statistics['memory_rss']['min'] / (1024*1024):.2f} MB")
    print(f"  Max: {statistics['memory_rss']['max'] / (1024*1024):.2f} MB")
    print(f"  Avg: {statistics['memory_rss']['avg'] / (1024*1024):.2f} MB")
    print(f"  Peak: {statistics['memory_rss']['peak'] / (1024*1024):.2f} MB")
    
    print("\\nMemory Percentage:")
    print(f"  Min: {statistics['memory_percent']['min']:.2f}%")
    print(f"  Max: {statistics['memory_percent']['max']:.2f}%")
    print(f"  Avg: {statistics['memory_percent']['avg']:.2f}%")
    
    # Return results as JSON
    results = {
        "test_duration": DURATION,
        "measurements": statistics['measurements_count'],
        "cpu": statistics['cpu'],
        "system_cpu": statistics['system_cpu'],
        "memory_mb": {
            "min": statistics['memory_rss']['min'] / (1024*1024),
            "max": statistics['memory_rss']['max'] / (1024*1024),
            "avg": statistics['memory_rss']['avg'] / (1024*1024),
            "peak": statistics['memory_rss']['peak'] / (1024*1024)
        },
        "memory_percent": statistics['memory_percent'],
        "detailed_measurements": monitor.measurements[-10:]  # Include last 10 measurements
    }
    
    print("\\nTest completed successfully")
    return results

# Run the combined stability test
combined_stability_test()
"""