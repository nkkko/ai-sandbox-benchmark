#!/usr/bin/env python3
import asyncio
import os
import time
import logging
import argparse
import importlib
import inspect
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from termcolor import colored
from tabulate import tabulate
import numpy as np
import yaml
from typing import Dict, Any, Callable, List, Tuple, Optional
import requests

# Import EnhancedTimingMetrics from metrics instead of from comparator (avoids circular dependency)
from metrics import EnhancedTimingMetrics, BenchmarkHistory

# Dynamically import all modules in the tests directory
TESTS_DIR = 'tests'
defined_tests = {}
test_id = 1
for filename in os.listdir(TESTS_DIR):
    if filename.endswith('.py') and not filename.startswith('__') and filename != 'test_template.py':
        module_name = filename[:-3]
        module = importlib.import_module(f'{TESTS_DIR}.{module_name}')
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith('test_'):
                defined_tests[test_id] = func
                test_id += 1

# Import providers from separate modules
from providers import daytona, e2b, codesandbox, modal, local

# Map provider names to their corresponding execute() implementations.
# Note: the daytona.execute() requires (code, executor, target_region).
provider_executors = {
    'daytona': daytona.execute,
    'e2b': e2b.execute,
    'codesandbox': codesandbox.execute,
    'modal': modal.execute,
    'local': local.execute
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create logger
logger = logging.getLogger(__name__)

# Create helper function for benchmarking logs
def log_benchmark(message):
    """Log a message with the benchmark prefix."""
    logger.info(f"[Benchmark] {message}")

# Create provider-specific logging helpers
def log_provider(provider, message):
    """Log a message with a specific provider prefix."""
    logger.info(f"[{provider.capitalize()}] {message}")

# Import the metrics classes from metrics.py
from metrics import EnhancedTimingMetrics, BenchmarkTimingMetrics


class SandboxExecutor:
    def __init__(self, warmup_runs: int = 1, measurement_runs: int = 10, num_concurrent_providers: int = 4):
        """Initialize the SandboxExecutor.

        Args:
            warmup_runs: Number of warmup runs to perform before measurement
            measurement_runs: Number of measurement runs to perform
            num_concurrent_providers: Number of providers to run in parallel
        """
        self.warmup_runs = warmup_runs
        self.measurement_runs = measurement_runs
        self.num_concurrent_providers = num_concurrent_providers
        # Store dedicated thread pools for providers that need them
        self.provider_executors = {}
        load_dotenv()
        self.config = self._load_config()
        self._validate_environment()

        log_benchmark(f"Initialized SandboxExecutor with {num_concurrent_providers} concurrent providers, "
                   f"{warmup_runs} warmup runs, and {measurement_runs} measurement runs")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yml file."""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                log_benchmark("Loaded configuration from config.yml")
                return config
            else:
                log_benchmark("config.yml not found, using default configuration")
                return {}
        except Exception as e:
            log_benchmark(f"Error loading config.yml: {e}")
            return {}

    def get_sandbox_env_vars(self) -> Dict[str, str]:
        """Get environment variables that should be passed to sandboxes."""
        env_vars = {}
        try:
            if self.config and 'env_vars' in self.config and 'pass_to_sandbox' in self.config['env_vars']:
                for var_name in self.config['env_vars']['pass_to_sandbox']:
                    if var_name in os.environ:
                        env_vars[var_name] = os.environ[var_name]
                        log_benchmark(f"Will pass {var_name} to sandboxes")
        except Exception as e:
            log_benchmark(f"Error getting sandbox env vars: {e}")
        return env_vars

    def _validate_environment(self):
        # Get selected providers from command line args or use default
        selected_providers = []
        try:
            import sys
            for i, arg in enumerate(sys.argv):
                if arg == '--providers' or arg == '-p':
                    if i + 1 < len(sys.argv):
                        selected_providers = sys.argv[i + 1].split(',')
                        break
        except Exception as e:
            log_benchmark(f"Error getting selected providers from command line: {e}")

        # Required vars for different providers
        provider_required_vars = {
            'daytona': {
                "DAYTONA_API_KEY": "Daytona API key",
                "DAYTONA_SERVER_URL": "Daytona server URL",
            },
            'codesandbox': {
                "CSB_API_KEY": "CodeSandbox API key"
            },
            'e2b': {},
            'modal': {},
            'local': {}
        }

        # Determine which required vars to check based on selected providers
        required_vars = {}
        if not selected_providers or 'local' in selected_providers and len(selected_providers) == 1:
            log_benchmark("Only local provider selected, skipping API key validation")
        else:
            # Add required vars for all selected providers
            for provider in selected_providers:
                if provider in provider_required_vars:
                    required_vars.update(provider_required_vars[provider])

            # If no providers specified, check all required vars
            if not selected_providers:
                for provider_vars in provider_required_vars.values():
                    required_vars.update(provider_vars)

            # Check required vars
            for var, description in required_vars.items():
                value = os.getenv(var)
                if not value:
                    raise ValueError(f"Missing {description} in environment variables: {var}")
                log_benchmark(f"Found {description}")

        # Optional but useful API keys
        optional_vars = {
            "OPENAI_API_KEY": "OpenAI API key",
            "ANTHROPIC_API_KEY": "Anthropic API key"
        }

        # Check for optional API keys
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                log_benchmark(f"Found {description}")
            else:
                log_benchmark(f"Did not find {description}")

    async def _run_single_provider_tests(
        self,
        provider: str,
        tests: Dict[int, Callable],
        single_run_tests: Dict[int, Callable],
        multi_run_tests: Dict[int, Callable],
        measurement_runs: int,
        target_region: str,
        executor: ThreadPoolExecutor
    ) -> List[Tuple[str, int, int, Any]]:
        """
        Run all tests for a single provider sequentially.

        Returns:
            List of tuples (provider, test_id, run_num, result)
        """
        results = []

        # First run single-run tests
        if single_run_tests:
            log_benchmark(f"Running single-run tests for {provider}")
            for test_id, test_func in single_run_tests.items():
                log_benchmark(f"Running test {test_id} for {provider} (single run)")
                result = await self.run_test_on_provider(test_func, provider, executor, target_region)
                results.append((provider, test_id, 1, result))

        # Then run multi-run tests
        if multi_run_tests:
            log_benchmark(f"Running {measurement_runs} measurement runs for {provider}")
            for run in range(measurement_runs):
                run_num = run + 1
                for test_id, test_func in multi_run_tests.items():
                    log_benchmark(f"Running test {test_id}, run {run_num} for {provider}")
                    result = await self.run_test_on_provider(test_func, provider, executor, target_region)
                    results.append((provider, test_id, run_num, result))

        return results

    async def run_test_on_provider(self, test_code_func: Callable, provider: str, executor: ThreadPoolExecutor, target_region: str) -> Tuple[str, Dict[str, Any], Any]:
        metrics = BenchmarkTimingMetrics()
        results = {'metrics': metrics, 'output': None}
        try:
            # Get test code and configuration
            test_data = test_code_func()

            # Handle both old format (string) and new format (dict with config)
            if isinstance(test_data, str):
                # Legacy format - just code as a string
                code = test_data
                # Use default env vars
                env_vars = self.get_sandbox_env_vars()
            else:
                # New format with config
                code = test_data['code']
                config = test_data.get('config', {})

                # Check if this test needs specific env vars
                required_env_vars = config.get('env_vars', [])
                if required_env_vars:
                    # Filter environment variables to only those required by this test
                    env_vars = {}
                    for var_name in required_env_vars:
                        if var_name in os.environ:
                            env_vars[var_name] = os.environ[var_name]
                            log_benchmark(f"Passing {var_name} to {provider} for this test")
                else:
                    # No specific env vars required, pass empty dict
                    env_vars = {}

            log_provider(provider, f"Executing test...")

            if provider == "daytona":
                # Daytona requires additional parameters: executor and target_region.
                output, provider_metrics = await provider_executors[provider](code, executor, target_region, env_vars)
            elif provider == "local":
                # Local provider doesn't need to be awaited as it will use subprocess
                output, provider_metrics = await provider_executors[provider](code, env_vars)
            else:
                output, provider_metrics = await provider_executors[provider](code, env_vars)

            # Ensure the provider metrics are properly handled
            if hasattr(provider_metrics, 'metrics'):
                # Copy all metrics from provider to our results
                for metric_name, metric_values in provider_metrics.metrics.items():
                    if metric_values:
                        if metric_name not in metrics.metrics:
                            metrics.metrics[metric_name] = []
                        metrics.metrics[metric_name].extend(metric_values)

                # Copy any errors from provider to our results
                if hasattr(provider_metrics, 'errors'):
                    for error in provider_metrics.errors:
                        metrics.add_error(error)

            # Extract and add internal timing data from the test output
            if output:
                internal_timing_extracted = metrics.extract_internal_timing(output)
                if internal_timing_extracted:
                    log_provider(provider, f"Extracted internal timing data from test output")

            results['output'] = output
            log_provider(provider, f"Completed execution")
            return provider, results, None
        except Exception as e:
            log_provider(provider, f"Execution error: {str(e)}")
            results['metrics'].add_error(str(e))
            return provider, results, e

    async def run_comparison(self, tests: Dict[int, Callable], providers: List[str], measurement_runs: int, target_region: str) -> Dict[str, Any]:
        overall_results = {}
        log_benchmark("Starting comparison run...")

        # Special handling for Daytona provider
        # Run Daytona tests sequentially before others to avoid thread contention issues
        has_daytona = 'daytona' in providers
        daytona_test_results = {}
        non_daytona_providers = [p for p in providers if p != 'daytona']

        # Determine which tests should run only once based on their configuration
        single_run_tests = {}
        for test_id, test_func in tests.items():
            # Check for both new configuration format and old attribute-based format
            try:
                test_data = test_func()
                if isinstance(test_data, dict) and 'config' in test_data:
                    if test_data['config'].get('single_run', False):
                        single_run_tests[test_id] = test_func
                        log_benchmark(f"Test {test_id} will run only once (from config)")
                elif hasattr(test_func, 'single_run') and test_func.single_run:
                    # Legacy attribute-based configuration
                    single_run_tests[test_id] = test_func
                    log_benchmark(f"Test {test_id} will run only once (from attribute)")
            except Exception as e:
                log_benchmark(f"Error checking test configuration for test {test_id}: {e}")

        # Define multi-run tests as all tests not in single_run_tests
        multi_run_tests = {test_id: func for test_id, func in tests.items()
                          if test_id not in single_run_tests}

        if single_run_tests:
            test_names = ", ".join([f"{test_id}:{func.__name__}" for test_id, func in single_run_tests.items()])
            log_benchmark(f"The following tests will only run once (ignoring measurement_runs): {test_names}")

        # Run warmups fully in parallel across both providers and tests
        if self.warmup_runs > 0:
            log_benchmark(f"Performing {self.warmup_runs} warmup runs in parallel...")

            # Create dedicated thread pools for providers that need them during warmup
            has_daytona = 'daytona' in providers
            if has_daytona:
                self.provider_executors['daytona'] = ThreadPoolExecutor(max_workers=1)
                log_benchmark(f"Created dedicated warmup thread pool for Daytona with 1 worker")

            # Calculate workers for shared warmup executor
            shared_workers = self.num_concurrent_providers * (len(providers) - (1 if has_daytona else 0))
            shared_workers = max(1, shared_workers)  # Ensure at least 1 worker

            # Create a shared thread pool executor for all other providers' warmup runs
            with ThreadPoolExecutor(max_workers=shared_workers) as shared_executor:
                log_benchmark(f"Created shared warmup thread pool with {shared_workers} workers")
                warmup_tasks = []

                for i in range(self.warmup_runs):
                    # Only do warmup runs for multi-run tests
                    for test_id, test_code_func in multi_run_tests.items():
                        for provider in providers:
                            # Each provider now manages its own executors internally
                            warmup_task = asyncio.create_task(
                                self.run_test_on_provider(test_code_func, provider, shared_executor, target_region)
                            )
                            warmup_tasks.append(warmup_task)

                # Run all warmup tasks concurrently and ignore results
                await asyncio.gather(*warmup_tasks, return_exceptions=True)
                log_benchmark("Warmup runs completed")

            # Clean up warmup executors to start fresh for the main run
            for provider, executor in self.provider_executors.items():
                executor.shutdown()
            self.provider_executors.clear()

        # If we have Daytona in the providers list, warm up the pool and run it first sequentially
        # This prevents thread contention issues that seem to affect Daytona more than other providers
        if has_daytona:
            log_benchmark("Running Daytona tests sequentially first to avoid thread contention")
            with ThreadPoolExecutor(max_workers=1) as daytona_executor:
                log_benchmark("Created dedicated Daytona executor with 1 worker")

                # Warm up Daytona's pool before running tests
                log_benchmark("Warming up Daytona pool for better performance")
                try:
                    await daytona.list_workspaces(target_region)
                    log_benchmark("Daytona warm pool activated")
                except Exception as e:
                    log_benchmark(f"Daytona warm pool initialization failed: {str(e)}")

                # Run Daytona tests sequentially
                daytona_results = await self._run_single_provider_tests(
                    'daytona',
                    tests,
                    single_run_tests,
                    multi_run_tests,
                    measurement_runs,
                    target_region,
                    daytona_executor
                )

                # Process results and add them to overall results
                for provider, test_id, run_num, result in daytona_results:
                    test_results = overall_results.setdefault(f"test_{test_id}", {})
                    run_results = test_results.setdefault(f"run_{run_num}", {})

                    if isinstance(result, Exception):
                        log_provider(provider, f"Test {test_id}, Run {run_num}: Execution failed: {str(result)}")
                        run_results[provider] = {'metrics': EnhancedTimingMetrics(), 'output': None, 'error': str(result)}
                    else:
                        p_name, p_results, error = result
                        run_results[p_name] = p_results
                        if error:
                            run_results[p_name]['error'] = str(error)

            log_benchmark("Completed Daytona tests, now running remaining providers")

            # Only create an executor for non-Daytona providers
            providers_for_parallel = non_daytona_providers
        else:
            # No Daytona, use all providers
            providers_for_parallel = providers

        # Skip the shared executor step if no providers remain
        if not providers_for_parallel:
            log_benchmark("No remaining providers to execute")
            return overall_results

        # Create a shared executor for the remaining providers
        # Each provider will manage its own executors internally as needed
        with ThreadPoolExecutor(max_workers=self.num_concurrent_providers * len(providers_for_parallel)) as executor:
            log_benchmark(f"Created shared executor with {self.num_concurrent_providers * len(providers_for_parallel)} workers")

            all_test_tasks = []
            test_task_map = {}  # Maps tasks to metadata (test_id, provider, run_num)

            # Schedule all single-run tests - PROVIDER PARALLEL
            if single_run_tests:
                log_benchmark("Scheduling single-run tests...")
                for test_id, test_code_func in single_run_tests.items():
                    log_benchmark(f"Scheduling test {test_id}: {test_code_func.__name__} (single run)")

                    # Create tasks for all providers in parallel for this test
                    provider_tasks = []
                    for provider in providers_for_parallel:
                        # Each provider now manages its own executors internally
                        task = asyncio.create_task(
                            self.run_test_on_provider(test_code_func, provider, executor, target_region)
                        )
                        provider_tasks.append(task)
                        test_task_map[task] = {
                            'test_id': test_id,
                            'provider': provider,
                            'run_num': 1,
                            'is_single_run': True
                        }

                    all_test_tasks.extend(provider_tasks)

            # Schedule all multi-run tests - PROVIDER PARALLEL
            if multi_run_tests:
                log_benchmark(f"Scheduling {measurement_runs} measurement runs for standard tests...")
                for run in range(measurement_runs):
                    run_num = run + 1
                    for test_id, test_code_func in multi_run_tests.items():
                        # Create tasks for all providers in parallel for this test and run
                        provider_tasks = []
                        for provider in providers_for_parallel:
                            # Each provider now manages its own executors internally
                            task = asyncio.create_task(
                                self.run_test_on_provider(test_code_func, provider, executor, target_region)
                            )
                            provider_tasks.append(task)
                            test_task_map[task] = {
                                'test_id': test_id,
                                'provider': provider,
                                'run_num': run_num,
                                'is_single_run': False
                            }

                        all_test_tasks.extend(provider_tasks)

            # Create a semaphore per provider to prevent one provider from blocking another
            # Each provider gets its own semaphore with a limit of 2 concurrent tasks
            provider_semaphores = {provider: asyncio.Semaphore(2) for provider in providers_for_parallel}

            # Helper function to run a task with the appropriate semaphore
            async def run_with_semaphore(task):
                meta = test_task_map[task]
                provider = meta['provider']
                async with provider_semaphores[provider]:
                    return await task

            # Instead of grouping by test/run, run all provider tasks fully in parallel
            # This prevents blocking between different providers
            all_semaphore_tasks = []

            # Create a task entry for each provider/test/run combination
            for task in all_test_tasks:
                meta = test_task_map[task]
                test_id = meta['test_id']
                run_num = meta['run_num']
                provider = meta['provider']

                # Log the tasks being prepared
                log_benchmark(f"Preparing task for Test {test_id}, Run {run_num}, Provider {provider}")

                # Add the semaphore-wrapped task to our execution list
                all_semaphore_tasks.append(run_with_semaphore(task))

            # Execute ALL provider tasks concurrently, not grouped by test/run
            log_benchmark(f"Executing all tasks across all providers in parallel")
            all_completed_tasks = await asyncio.gather(*all_semaphore_tasks, return_exceptions=True)

            # Process results and organize them by test/run/provider
            for task, result in zip(all_test_tasks, all_completed_tasks):
                meta = test_task_map[task]
                test_id = meta['test_id']
                run_num = meta['run_num']
                provider = meta['provider']

                # Initialize results structure
                test_results = overall_results.setdefault(f"test_{test_id}", {})
                run_results = test_results.setdefault(f"run_{run_num}", {})

                # Process the result
                if isinstance(result, Exception):
                    log_provider(provider, f"Test {test_id}, Run {run_num}: Execution failed: {str(result)}")
                    run_results[provider] = {'metrics': EnhancedTimingMetrics(), 'output': None, 'error': str(result)}
                else:
                    p_name, p_results, error = result
                    run_results[p_name] = p_results
                    if error:
                        run_results[p_name]['error'] = str(error)

        # Clean up any dedicated executors
        for provider, executor in self.provider_executors.items():
            log_benchmark(f"Shutting down dedicated executor for {provider}")
            executor.shutdown()
        self.provider_executors.clear()

        log_benchmark("All tests completed")
        return overall_results


class ResultsVisualizer:
    @staticmethod
    def print_summary_info(warmup_runs: int, measurement_runs: int, tests: dict, providers: list):
        print("\n" + "=" * 80)
        print("Test Configuration Summary".center(80))
        print("=" * 80)
        print(f"Warmup Runs: {warmup_runs}")
        print(f"Measurement Runs: {measurement_runs}")
        tests_used = ', '.join(f"{tid}:{func.__name__}" for tid, func in tests.items())
        print(f"Tests Used ({len(tests)}): {tests_used}")
        print(f"Providers Used: {', '.join(providers)}")
        print("=" * 80 + "\n")

    @staticmethod
    def print_historical_comparison(
        history: BenchmarkHistory,
        tests: Dict[int, Callable],
        providers: List[str],
        limit: int = 5,
        metrics: List[str] = None
    ):
        """
        Print a historical comparison of benchmark results.

        Args:
            history: The benchmark history
            tests: Dictionary of tests to show history for
            providers: List of providers to compare
            limit: Number of recent runs to include
            metrics: Optional list of specific metrics to show (defaults to total time only)
        """
        if not metrics:
            metrics = ["total_time"]  # Default to showing only total time

        print("\n" + "=" * 80)
        print("Historical Performance Trends".center(80))
        print("=" * 80)

        for test_id in tests.keys():
            test_func = tests[test_id]
            print(f"\n{colored(f'Historical Trend for Test {test_id}: {test_func.__name__}', 'blue', attrs=['bold'])}")

            # Get provider comparison
            comparison = history.get_provider_comparison(test_id, providers, runs=limit)

            if "error" in comparison:
                print(f"  {comparison['error']}")
                continue

            # Print comparison table
            if comparison["providers"]:
                headers = ["Provider", "Avg Time (ms)", "Std Dev", "CV (%)", "Error Rate (%)", "Samples"]
                table_data = []

                for provider, stats in comparison["providers"].items():
                    row = [
                        provider.capitalize(),
                        f"{stats['avg_time']:.2f}",
                        f"{stats['stdev']:.2f}",
                        f"{stats['cv']:.2f}",
                        f"{stats['error_rate']:.1f}",
                        stats['samples']
                    ]
                    table_data.append(row)

                print(tabulate(table_data, headers=headers, tablefmt="grid"))

                # Print fastest and most consistent providers
                if comparison["fastest_provider"]:
                    print(f"\nFastest Provider: {comparison['fastest_provider'].capitalize()}")
                if comparison["most_consistent_provider"]:
                    print(f"Most Consistent Provider: {comparison['most_consistent_provider'].capitalize()}")

            # Show trend data for each provider
            print(f"\nPerformance Trends (last {limit} runs):")

            for provider in providers:
                for metric in metrics:
                    metric_name = "Total Time" if metric == "total_time" else metric
                    trend_data = history.get_trend_data(test_id, provider, metric, limit)

                    if "error" in trend_data:
                        continue  # Skip if no data for this provider and metric

                    data_points = trend_data["data_points"]
                    if not data_points or all(p["value"] is None for p in data_points):
                        continue  # Skip if no valid data points

                    print(f"\n{provider.capitalize()} - {metric_name}:")

                    # Print trend summary
                    if "change_percent" in trend_data:
                        change = trend_data["change_percent"]
                        direction = "improved" if trend_data["improved"] else "regressed"
                        color = "green" if trend_data["improved"] else "red"
                        print(colored(f"  {abs(change):.2f}% {direction} over last {len(data_points)} runs", color))

                    # Print trend values
                    values = []
                    for point in data_points:
                        if point["value"] is not None:
                            timestamp = point["timestamp"].split("T")[0]  # Just show date part
                            values.append(f"{timestamp}: {point['value']:.2f}ms")

                    if values:
                        print("  Recent values:")
                        for value in values[-limit:]:  # Show only the most recent values
                            print(f"    {value}")

        print("\n" + "=" * 80)

    @staticmethod
    def print_detailed_comparison(
            overall_results: dict,
            tests: dict,
            measurement_runs: int,
            warmup_runs: int,
            providers: list
        ):
        # Print overall configuration details.
        ResultsVisualizer.print_summary_info(warmup_runs, measurement_runs, tests, providers)

        # Iterate over each test.
        for test_id, test_code_func in tests.items():
            test_results = overall_results.get(f"test_{test_id}", {})

            # Check if test is an info test (like system_info) or a performance test
            is_info_test = hasattr(test_code_func, 'is_info_test') and test_code_func.is_info_test

            # Different header depending on test type
            if is_info_test:
                print(f"\n{colored(f'Information Report for Test {test_id}: {test_code_func.__name__}', 'blue', attrs=['bold'])}")
            else:
                print(f"\n{colored(f'Performance Comparison for Test {test_id}: {test_code_func.__name__}', 'yellow', attrs=['bold'])}")

            # Check if any of the providers succeeded in running the test
            first_run_results = test_results.get("run_1", {})
            any_output = False

            # For info tests, we want to show complete output for one provider
            if is_info_test:
                best_provider_output = None
                for provider in providers:  # Use the supplied provider list
                    if provider in first_run_results and 'output' in first_run_results[provider]:
                        output = first_run_results[provider]['output']
                        if output:
                            any_output = True
                            # Select the most detailed output (longest) as the best
                            # Handle special case for Logs objects from e2b
                            if hasattr(output, 'stdout') and isinstance(output.stdout, list):
                                output_str = '\n'.join(output.stdout)
                            else:
                                output_str = str(output)

                            if best_provider_output is None or len(output_str) > len(str(best_provider_output[1])):
                                best_provider_output = (provider, output_str)

                if best_provider_output:
                    print(f"\n{colored(f'System Information from {best_provider_output[0].capitalize()}:', 'green', attrs=['bold'])}")
                    print(f"{best_provider_output[1]}")

                    # After showing the full output, provide a comparison summary between providers
                    print(f"\n{colored('Provider Comparison Summary:', 'yellow')}")
                    summary_table = []

                    # Check if each provider succeeded and report minimal info
                    for provider in providers:
                        if provider in first_run_results:
                            if first_run_results[provider].get('error'):
                                status = "Failed"
                                details = first_run_results[provider]['error']
                            else:
                                status = "Success"
                                # Try to extract OS and Python version from output if available
                                raw_output = first_run_results[provider].get('output', '')
                                details = "Output available"

                                try:
                                    # Handle Logs objects from e2b
                                    if hasattr(raw_output, 'stdout') and isinstance(raw_output.stdout, list):
                                        output_text = '\n'.join(raw_output.stdout)
                                    else:
                                        output_text = str(raw_output)

                                    if "OS:" in output_text and "Python:" in output_text:
                                        os_line = [line for line in output_text.split('\n') if "OS:" in line]
                                        py_line = [line for line in output_text.split('\n') if "Python:" in line]
                                        if os_line and py_line:
                                            details = f"{os_line[0].strip()}, {py_line[0].strip()}"
                                except Exception:
                                    # If extraction fails, just use the default message
                                    pass
                        else:
                            status = "No data"
                            details = "Test did not run"
                        summary_table.append([provider.capitalize(), status, details])

                    # Print comparison summary table
                    print(tabulate(summary_table,
                                 headers=["Provider", "Status", "Details"],
                                 tablefmt="grid"))
            else:
                # For performance tests, show brief example output
                first_provider_output = None
                for provider in providers:
                    if provider in first_run_results and 'output' in first_run_results[provider]:
                        first_provider_output = first_run_results[provider]['output']
                        any_output = True
                        break

                # if first_provider_output:
                #     try:
                #         # Handle special case for Logs objects from e2b
                #         if hasattr(first_provider_output, 'stdout') and isinstance(first_provider_output.stdout, list):
                #             output_str = '\n'.join(first_provider_output.stdout)
                #         else:
                #             output_str = str(first_provider_output)

                #         # Show abbreviated output (first few lines)
                #         output_lines = output_str.split('\n')
                #         if len(output_lines) > 10:
                #             abbreviated_output = '\n'.join(output_lines[:10]) + "\n... (output truncated)"
                #         else:
                #             abbreviated_output = output_str
                #         print(f"\nExample Output (from first run, first available provider):\n{abbreviated_output}")
                #     except Exception as e:
                #         # If formatting fails, show raw output
                #         print(f"\nExample Output (from first run, first available provider):\n{first_provider_output}")

                # Build the main metrics table for performance tests
                headers = ["Metric"] + [p.capitalize() for p in providers]
                table_data = []

                for metric in ["Workspace Creation", "Code Execution", "Cleanup"]:
                    row = [metric]
                    for provider in providers:
                        all_runs_metrics = []
                        for run_num in range(1, measurement_runs + 1):
                            run_results = test_results.get(f"run_{run_num}", {})
                            if provider in run_results:
                                run_metric = run_results[provider]['metrics'].get_statistics().get(metric, {})
                                if run_metric:
                                    all_runs_metrics.append(run_metric['mean'])
                        if all_runs_metrics:
                            avg_metric = np.mean(all_runs_metrics)
                            std_metric = np.std(all_runs_metrics)
                            row.append(f"{avg_metric:.2f}ms (±{std_metric:.2f})")
                        else:
                            row.append("N/A")
                    table_data.append(row)

                # Compute and display the total time row.
                row = ["Total Time"]
                platform_totals = {}
                for provider in providers:
                    total_times = []
                    for run_num in range(1, measurement_runs + 1):
                        run_results = test_results.get(f"run_{run_num}", {})
                        if provider in run_results:
                            total_times.append(run_results[provider]['metrics'].get_total_time())
                    if total_times:
                        provider_total = np.mean(total_times)
                        platform_totals[provider] = provider_total
                        row.append(f"{provider_total:.2f}ms")
                    else:
                        row.append("N/A")
                table_data.append(row)

                # Compute comparisons versus first provider.
                first_provider = providers[0] if providers else "daytona"
                first_provider_total = platform_totals.get(first_provider, 0)
                percentage_comparisons = []
                for provider in providers:
                    if provider == first_provider or first_provider_total == 0:
                        percentage_comparisons.append("0%")
                    elif provider in platform_totals:
                        diff_percentage = ((platform_totals[provider] - first_provider_total) / first_provider_total * 100)
                        percentage_comparisons.append(f"{diff_percentage:+.1f}%")
                    else:
                        percentage_comparisons.append("N/A")
                table_data.append([f"vs {first_provider.capitalize()} %"] + percentage_comparisons)

                # Print out the main metrics table.
                print(tabulate(table_data, headers=headers, tablefmt="grid"))

            # Build the failure summary table (for any test type)
            fail_table = []
            fail_headers = ["Provider", "Failed Runs (out of {})".format(measurement_runs)]
            errors_found = False
            for provider in providers:
                fail_count = 0
                for run_num in range(1, measurement_runs + 1):
                    run_results = test_results.get(f"run_{run_num}", {})
                    if provider in run_results and run_results[provider].get('error'):
                        fail_count += 1
                fail_table.append([provider.capitalize(), f"{fail_count}/{measurement_runs}"])
                if fail_count > 0:
                    errors_found = True

            if errors_found:
                print("\n" + colored(f"Failure Summary for Test {test_id}: {test_code_func.__name__}", 'red', attrs=['bold']))
                print(tabulate(fail_table, headers=fail_headers, tablefmt="grid"))
            else:
                print("\nNo failures recorded for this test.")


async def main(args):
    # Set num_concurrent_providers to match the number of providers being tested
    # This ensures we efficiently use resources for parallel provider execution
    providers_to_run = args.providers.split(',') if args.providers else []
    num_concurrent = max(1, len(providers_to_run))  # Ensure at least 1 for executor

    # Validate that we have providers to run
    if not providers_to_run:
        log_benchmark("No providers specified to run tests on.")
        return

    executor_obj = SandboxExecutor(
        warmup_runs=args.warmup_runs,
        measurement_runs=args.runs,
        num_concurrent_providers=num_concurrent
    )

    log_benchmark(f"Running with {num_concurrent} provider(s) in parallel")

    tests_to_run = {}
    if args.tests == "all":
        tests_to_run = defined_tests
    elif args.tests:  # Check that tests string is not empty
        for test_id in map(int, args.tests.split(',')):
            if test_id in defined_tests:
                tests_to_run[test_id] = defined_tests[test_id]
            else:
                log_benchmark(f"Test ID {test_id} not found and will be skipped.")

    # Validate that we have tests to run
    if not tests_to_run:
        log_benchmark("No valid tests specified to run.")
        return

    try:
        # Initialize benchmark history tracker with specified history file
        history = BenchmarkHistory(args.history_file)

        # Start benchmark execution
        start_time = time.time()
        overall_results = await executor_obj.run_comparison(
            tests_to_run,
            providers_to_run,
            args.runs,
            args.target_region
        )
        total_time = time.time() - start_time

        log_benchmark(f"All benchmark tests completed in {total_time:.2f} seconds")

        # Add results to history with metadata
        run_metadata = {
            "total_duration": total_time,
            "warmup_runs": args.warmup_runs,
            "measurement_runs": args.runs,
            "target_region": args.target_region,
            "command_line_args": vars(args)
        }
        history.add_benchmark_run(
            results=overall_results,
            providers=providers_to_run,
            tests=tests_to_run,
            metadata=run_metadata
        )
        log_benchmark(f"Benchmark results saved to history file: {history.history_file}")

        # Display benchmark results
        visualizer = ResultsVisualizer()
        visualizer.print_detailed_comparison(
            overall_results,
            tests_to_run,
            args.runs,
            args.warmup_runs,
            providers_to_run
        )

        # Show historical comparison if enabled
        if args.show_history and overall_results:
            visualizer.print_historical_comparison(
                history,
                tests_to_run,
                providers_to_run,
                limit=args.history_limit
            )

    except Exception as e:
        log_benchmark(f"Error during execution: {str(e)}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run sandbox performance comparison tests.")
    parser.add_argument('--tests', '-t', type=str, default='all',
                        help='Comma-separated list of test IDs to run (or "all" for all tests). Default: all')
    parser.add_argument('-a', '--all-tests', action='store_true',
                        help='Toggle between selecting all tests and no tests')
    parser.add_argument('--providers', '-p', type=str, default='daytona,e2b,codesandbox,modal,local',
                        help='Comma-separated list of providers to test. Default: daytona,e2b,codesandbox,modal,local')
    parser.add_argument('-A', '--all-providers', action='store_true',
                        help='Toggle between selecting all providers and no providers')
    parser.add_argument('--runs', '-r', type=int, default=10,
                        help='Number of measurement runs per test/provider. Default: 10')
    parser.add_argument('--warmup-runs', '-w', type=int, default=1,
                        help='Number of warmup runs. Default: 1')
    parser.add_argument('--target-region', type=str, default='eu',
                        help='Target region (eu, us, asia). Default: eu')
    parser.add_argument('--show-history', action='store_true',
                        help='Show historical comparison after benchmark')
    parser.add_argument('--history-limit', type=int, default=5,
                        help='Number of previous runs to include in history comparison. Default: 5')
    parser.add_argument('--history-file', type=str, default='benchmark_history.json',
                        help='Path to the benchmark history file. Default: benchmark_history.json')

    args = parser.parse_args()

    # Handle all-tests toggle
    if args.all_tests:
        # Toggle between all and none
        if args.tests == "all":
            args.tests = ""
        else:
            args.tests = "all"

    # Handle all-providers toggle
    if args.all_providers:
        # Toggle between all and none
        all_providers = "daytona,e2b,codesandbox,modal,local"
        if args.providers == all_providers:
            args.providers = ""
        else:
            args.providers = all_providers

    # Validate tests
    if args.tests != "all" and args.tests:
        try:
            test_ids = list(map(int, args.tests.split(',')))
        except ValueError:
            parser.error("--tests must be 'all' or comma-separated integers.")
    elif args.tests == "":
        parser.error("No tests selected. Use --select-all-tests or specify tests with --tests.")

    # Validate providers
    if not args.providers:
        parser.error("No providers selected. Use --select-all-providers or specify providers with --providers.")

    asyncio.run(main(args))