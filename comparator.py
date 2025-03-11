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
    if filename.endswith('.py') and not filename.startswith('__'):
        module_name = filename[:-3]
        module = importlib.import_module(f'{TESTS_DIR}.{module_name}')
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith('test_'):
                defined_tests[test_id] = func
                test_id += 1

# Import providers from separate modules
from providers import daytona, e2b, codesandbox, modal

# Map provider names to their corresponding execute() implementations.
# Note: the daytona.execute() requires (code, executor, target_region).
provider_executors = {
    'daytona': daytona.execute,
    'e2b': e2b.execute,
    'codesandbox': codesandbox.execute,
    'modal': modal.execute
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedTimingMetrics:
    def __init__(self):
        self.metrics = {
            "Workspace Creation": [],
            "Code Execution": [],
            "Cleanup": []
        }
        self.errors = []

    def add_metric(self, name: str, time_value: float):
        if name in self.metrics:
            # Convert to milliseconds
            self.metrics[name].append(time_value * 1000)

    def add_error(self, error: str):
        self.errors.append(error)

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        stats_dict = {}
        for name, measurements in self.metrics.items():
            if measurements:
                stats_dict[name] = {
                    'mean': np.mean(measurements),
                    'std': np.std(measurements),
                    'min': np.min(measurements),
                    'max': np.max(measurements)
                }
        return stats_dict

    def get_total_time(self) -> float:
        return sum(np.mean(times) for times in self.metrics.values() if times)


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
        load_dotenv()
        self.config = self._load_config()
        self._validate_environment()
        
        logger.info(f"Initialized SandboxExecutor with {num_concurrent_providers} concurrent providers, "
                   f"{warmup_runs} warmup runs, and {measurement_runs} measurement runs")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yml file."""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info("Loaded configuration from config.yml")
                return config
            else:
                logger.warning("config.yml not found, using default configuration")
                return {}
        except Exception as e:
            logger.error(f"Error loading config.yml: {e}")
            return {}
    
    def get_sandbox_env_vars(self) -> Dict[str, str]:
        """Get environment variables that should be passed to sandboxes."""
        env_vars = {}
        try:
            if self.config and 'env_vars' in self.config and 'pass_to_sandbox' in self.config['env_vars']:
                for var_name in self.config['env_vars']['pass_to_sandbox']:
                    if var_name in os.environ:
                        env_vars[var_name] = os.environ[var_name]
                        logger.info(f"Will pass {var_name} to sandboxes")
        except Exception as e:
            logger.error(f"Error getting sandbox env vars: {e}")
        return env_vars

    def _validate_environment(self):
        required_vars = {
            "DAYTONA_API_KEY": "Daytona API key",
            "DAYTONA_SERVER_URL": "Daytona server URL",
            "CSB_API_KEY": "CodeSandbox API key"
        }
        # Optional but useful API keys
        optional_vars = {
            "OPENAI_API_KEY": "OpenAI API key",
            "ANTHROPIC_API_KEY": "Anthropic API key"
        }
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                raise ValueError(f"Missing {description} in environment variables: {var}")
            logger.info(f"Found {description}")
            
        # Check for optional API keys
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                logger.info(f"Found {description}")
            else:
                logger.info(f"Did not find {description}")

    async def run_test_on_provider(self, test_code_func: Callable, provider: str, executor: ThreadPoolExecutor, target_region: str) -> Tuple[str, Dict[str, Any], Any]:
        results = {'metrics': EnhancedTimingMetrics(), 'output': None}
        try:
            code = test_code_func()
            env_vars = self.get_sandbox_env_vars()
            logger.info(f"Executing test on {provider}...")
            
            if provider == "daytona":
                # Daytona requires additional parameters: executor and target_region.
                output, metrics = await provider_executors[provider](code, executor, target_region, env_vars)
            else:
                output, metrics = await provider_executors[provider](code, env_vars)
                
            # Merge metrics from executed provider into our results
            for metric_name, metric_values in metrics.metrics.items():
                if metric_values:
                    results['metrics'].metrics[metric_name].extend(metric_values)
            results['output'] = output
            logger.info(f"Completed {provider} execution")
            return provider, results, None
        except Exception as e:
            logger.error(f"Failed to execute {provider}: {str(e)}")
            results['metrics'].add_error(str(e))
            return provider, results, e

    async def run_comparison(self, tests: Dict[int, Callable], providers: List[str], measurement_runs: int, target_region: str) -> Dict[str, Any]:
        overall_results = {}
        logger.info("Starting comparison run...")

        # Handle tests that should only run once
        single_run_tests = {test_id: func for test_id, func in tests.items() 
                           if hasattr(func, 'single_run') and func.single_run}
        
        multi_run_tests = {test_id: func for test_id, func in tests.items()
                          if test_id not in single_run_tests}
        
        if single_run_tests:
            test_names = ", ".join([f"{test_id}:{func.__name__}" for test_id, func in single_run_tests.items()])
            logger.info(f"The following tests will only run once (ignoring measurement_runs): {test_names}")

        # Run warmups fully in parallel across both providers and tests
        if self.warmup_runs > 0:
            logger.info(f"Performing {self.warmup_runs} warmup runs in parallel...")
            
            # Create a shared thread pool executor for all warmup runs
            with ThreadPoolExecutor(max_workers=self.num_concurrent_providers * len(providers)) as executor:
                warmup_tasks = []
                
                for i in range(self.warmup_runs):
                    # Only do warmup runs for multi-run tests
                    for test_id, test_code_func in multi_run_tests.items():
                        for provider in providers:
                            warmup_task = asyncio.create_task(
                                self.run_test_on_provider(test_code_func, provider, executor, target_region)
                            )
                            warmup_tasks.append(warmup_task)
                
                # Run all warmup tasks concurrently and ignore results
                await asyncio.gather(*warmup_tasks, return_exceptions=True)
                logger.info("Warmup runs completed")

        # Global thread pool executor for all test runs
        with ThreadPoolExecutor(max_workers=self.num_concurrent_providers * len(providers)) as executor:
            all_test_tasks = []
            test_task_map = {}  # Maps tasks to metadata (test_id, provider, run_num)
            
            # Schedule all single-run tests - PROVIDER PARALLEL
            if single_run_tests:
                logger.info("Scheduling single-run tests...")
                for test_id, test_code_func in single_run_tests.items():
                    logger.info(f"Scheduling test {test_id}: {test_code_func.__name__} (single run)")
                    
                    # Create tasks for all providers in parallel for this test
                    provider_tasks = []
                    for provider in providers:
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
                logger.info(f"Scheduling {measurement_runs} measurement runs for standard tests...")
                for run in range(measurement_runs):
                    run_num = run + 1
                    for test_id, test_code_func in multi_run_tests.items():
                        # Create tasks for all providers in parallel for this test and run
                        provider_tasks = []
                        for provider in providers:
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
            
            # Use a semaphore to limit concurrency based on the number of providers
            # This ensures we don't exceed resource limits while still getting maximum parallelism
            sem = asyncio.Semaphore(len(providers) * 2)  # Allow 2 tests per provider
            
            # Helper function to run a task with the semaphore
            async def run_with_semaphore(task):
                async with sem:
                    return await task
            
            # Group tasks by test and run for parallel execution
            tasks_by_test_run = {}
            for task in all_test_tasks:
                meta = test_task_map[task]
                test_id = meta['test_id']
                run_num = meta['run_num']
                key = (test_id, run_num)
                if key not in tasks_by_test_run:
                    tasks_by_test_run[key] = []
                tasks_by_test_run[key].append(task)
            
            # Process all tests and runs
            all_completed_tasks = []
            for (test_id, run_num), tasks in tasks_by_test_run.items():
                # For each test and run, execute all provider tasks in parallel
                logger.info(f"Executing Test {test_id}, Run {run_num} across all providers in parallel")
                
                # Wrap tasks with semaphore
                semaphore_tasks = [run_with_semaphore(task) for task in tasks]
                
                # Execute all provider tasks for this test and run concurrently
                provider_results = await asyncio.gather(*semaphore_tasks, return_exceptions=True)
                
                # Process results for this batch
                for task, result in zip(tasks, provider_results):
                    meta = test_task_map[task]
                    provider = meta['provider']
                    
                    # Initialize results structure
                    test_results = overall_results.setdefault(f"test_{test_id}", {})
                    run_results = test_results.setdefault(f"run_{run_num}", {})
                    
                    # Process the result
                    if isinstance(result, Exception):
                        logger.error(f"Test {test_id}, Run {run_num}: Failed to execute {provider}: {str(result)}")
                        run_results[provider] = {'metrics': EnhancedTimingMetrics(), 'output': None, 'error': str(result)}
                    else:
                        p_name, p_results, error = result
                        run_results[p_name] = p_results
                        if error:
                            run_results[p_name]['error'] = str(error)
                    
                # Store completed tasks for return
                all_completed_tasks.extend(provider_results)
        
        logger.info("All tests completed")
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
                        
                if first_provider_output:
                    try:
                        # Handle special case for Logs objects from e2b
                        if hasattr(first_provider_output, 'stdout') and isinstance(first_provider_output.stdout, list):
                            output_str = '\n'.join(first_provider_output.stdout)
                        else:
                            output_str = str(first_provider_output)
                        
                        # Show abbreviated output (first few lines)
                        output_lines = output_str.split('\n')
                        if len(output_lines) > 10:
                            abbreviated_output = '\n'.join(output_lines[:10]) + "\n... (output truncated)"
                        else:
                            abbreviated_output = output_str
                        print(f"\nExample Output (from first run, first available provider):\n{abbreviated_output}")
                    except Exception as e:
                        # If formatting fails, show raw output
                        print(f"\nExample Output (from first run, first available provider):\n{first_provider_output}")

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
        logger.error("No providers specified to run tests on.")
        return
    
    executor_obj = SandboxExecutor(
        warmup_runs=args.warmup_runs, 
        measurement_runs=args.runs, 
        num_concurrent_providers=num_concurrent
    )
    
    logger.info(f"Running with {num_concurrent} provider(s) in parallel")

    tests_to_run = {}
    if args.tests == "all":
        tests_to_run = defined_tests
    elif args.tests:  # Check that tests string is not empty
        for test_id in map(int, args.tests.split(',')):
            if test_id in defined_tests:
                tests_to_run[test_id] = defined_tests[test_id]
            else:
                logger.warning(f"Test ID {test_id} not found and will be skipped.")
                
    # Validate that we have tests to run
    if not tests_to_run:
        logger.error("No valid tests specified to run.")
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
        
        logger.info(f"All benchmark tests completed in {total_time:.2f} seconds")
        
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
        logger.info(f"Benchmark results saved to history file: {history.history_file}")
        
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
        logger.error(f"Error during execution: {str(e)}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run sandbox performance comparison tests.")
    parser.add_argument('--tests', '-t', type=str, default='all',
                        help='Comma-separated list of test IDs to run (or "all" for all tests). Default: all')
    parser.add_argument('-a', '--all-tests', action='store_true',
                        help='Toggle between selecting all tests and no tests')
    parser.add_argument('--providers', '-p', type=str, default='daytona,e2b,codesandbox,modal',
                        help='Comma-separated list of providers to test. Default: daytona,e2b,codesandbox,modal')
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
        all_providers = "daytona,e2b,codesandbox,modal"
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
