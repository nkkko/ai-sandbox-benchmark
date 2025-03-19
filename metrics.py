#!/usr/bin/env python3
import numpy as np
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

class EnhancedTimingMetrics:
    def __init__(self):
        # Initialize with common metrics but allow dynamic addition
        self.metrics = {
            "Workspace Creation": [],
            "Code Execution": [],
            "Internal Execution": [],
            "Cleanup": []
        }
        # List of metrics that are already in milliseconds and don't need conversion
        self.ms_metrics = {"Internal Execution"}
        self.errors = []

    def add_metric(self, name: str, time_value: float):
        # Dynamically add the metric if it doesn't exist
        if name not in self.metrics:
            self.metrics[name] = []

        # Convert to milliseconds if not already in ms
        if name not in self.ms_metrics:
            time_value = time_value * 1000

        self.metrics[name].append(time_value)

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
        # Standard metrics that should be included in total time
        standard_keys = [
            "Workspace Creation",
            "Dependency Installation",
            "Environment Setup",
            "Code Execution",
            "Cleanup"
        ]

        # Skip Internal Execution and other metrics when calculating total time
        # Sum only the standard metrics that exist
        return sum(np.mean(self.metrics[key]) for key in standard_keys
                  if key in self.metrics and self.metrics[key])


class BenchmarkTimingMetrics(EnhancedTimingMetrics):
    """Extended metrics class with support for extracting internal timing data from test output."""

    def extract_internal_timing(self, output):
        """Extract timing data from standardized output format."""
        try:
            # Convert logs objects from E2B to string
            if hasattr(output, 'stdout') and isinstance(output.stdout, list):
                output_str = '\n'.join(output.stdout)
            else:
                output_str = str(output)

            # Look for the benchmark timing data markers
            start_marker = "--- BENCHMARK TIMING DATA ---"
            end_marker = "--- END BENCHMARK TIMING DATA ---"

            if start_marker in output_str and end_marker in output_str:
                # Extract the JSON part between the markers
                start_idx = output_str.find(start_marker) + len(start_marker)
                end_idx = output_str.find(end_marker)
                json_data = output_str[start_idx:end_idx].strip()

                # Parse the JSON data
                import json
                timing_data = json.loads(json_data)

                # Add the internal execution time metric
                if "internal_execution_time_ms" in timing_data:
                    self.add_metric("Internal Execution", timing_data["internal_execution_time_ms"])
                    return True

            return False
        except Exception as e:
            print(f"Error extracting internal timing: {e}")
            return False

    def to_dict(self) -> Dict:
        """Convert metrics to a serializable dictionary for storage"""
        return {
            "metrics": self.metrics,
            "errors": self.errors,
            "statistics": self.get_statistics(),
            "total_time": self.get_total_time()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'EnhancedTimingMetrics':
        """Recreate metrics object from a dictionary"""
        metrics = cls()
        metrics.metrics = data.get("metrics", {})
        metrics.errors = data.get("errors", [])
        return metrics


class BenchmarkHistory:
    """Manages historical benchmark results and provides trend analysis"""

    def __init__(self, history_file: str = "benchmark_history.json"):
        """Initialize with path to history file"""
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load history from file or create empty history"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading history file: {e}")
                return {"runs": [], "test_results": {}}
        return {"runs": [], "test_results": {}}

    def save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving history file: {e}")

    def add_benchmark_run(self, results: Dict, providers: List[str], tests: Dict,
                          timestamp: Optional[str] = None,
                          metadata: Optional[Dict] = None) -> str:
        """
        Add a new benchmark run to history

        Args:
            results: The benchmark results
            providers: List of providers used
            tests: Dictionary of tests executed
            timestamp: Optional timestamp (defaults to current time)
            metadata: Optional additional information about this run

        Returns:
            run_id: Unique identifier for this run
        """
        if not timestamp:
            timestamp = datetime.now().isoformat()

        run_id = str(uuid.uuid4())

        # Create run metadata
        run_info = {
            "id": run_id,
            "timestamp": timestamp,
            "providers": providers,
            "tests": [{"id": tid, "name": func.__name__} for tid, func in tests.items()],
            "metadata": metadata or {}
        }

        # Add run to history
        self.history["runs"].append(run_info)

        # Process and store results
        for test_key, test_data in results.items():
            if test_key not in self.history["test_results"]:
                self.history["test_results"][test_key] = {}

            # Store run results for this test
            self.history["test_results"][test_key][run_id] = {
                "timestamp": timestamp,
                "results": self._process_test_results(test_data, providers)
            }

        # Save updated history
        self.save_history()
        return run_id

    def _process_test_results(self, test_data: Dict, providers: List[str]) -> Dict:
        """Process raw test results into a format suitable for storage"""
        processed = {}

        for run_key, run_data in test_data.items():
            processed[run_key] = {}

            for provider in providers:
                if provider in run_data:
                    # Extract key metrics
                    if 'metrics' in run_data[provider]:
                        processed[run_key][provider] = {
                            "total_time": run_data[provider]['metrics'].get_total_time(),
                            "stats": run_data[provider]['metrics'].get_statistics(),
                            "error": run_data[provider].get('error', None)
                        }

        return processed

    def get_trend_data(self, test_id: int, provider: str, metric: str = "total_time",
                      limit: int = 10) -> Dict:
        """
        Get trend data for a specific test, provider and metric

        Args:
            test_id: ID of the test to analyze
            provider: Name of the provider
            metric: Metric to track (total_time, or a specific phase like Workspace Creation)
            limit: Max number of most recent runs to include

        Returns:
            Dictionary with trend data
        """
        test_key = f"test_{test_id}"
        if test_key not in self.history["test_results"]:
            return {"error": f"No history for test {test_id}"}

        # Collect data points in chronological order
        data_points = []
        provider_not_found = True

        # Sort runs by timestamp
        sorted_runs = sorted(
            [(run_id, self.history["test_results"][test_key][run_id]["timestamp"])
             for run_id in self.history["test_results"][test_key]],
            key=lambda x: x[1]
        )

        # Get the most recent runs within the limit
        recent_runs = sorted_runs[-limit:] if limit > 0 else sorted_runs

        for run_id, timestamp in recent_runs:
            run_data = self.history["test_results"][test_key][run_id]
            run_results = run_data["results"]

            # Look for data in the first run (usually run_1)
            for run_key in run_results:
                if provider in run_results[run_key]:
                    provider_not_found = False
                    provider_data = run_results[run_key][provider]

                    # Check for error
                    if provider_data.get("error"):
                        value = None
                    else:
                        # Get appropriate metric
                        if metric == "total_time":
                            value = provider_data.get("total_time")
                        else:
                            # Extract specific phase metric
                            stats = provider_data.get("stats", {})
                            value = stats.get(metric, {}).get("mean") if metric in stats else None

                    # Add data point
                    data_points.append({
                        "run_id": run_id,
                        "timestamp": timestamp,
                        "value": value
                    })
                    break

        if provider_not_found:
            return {"error": f"No data for provider {provider} in test {test_id}"}

        # Calculate trend information
        trend_info = {
            "data_points": data_points,
            "test_id": test_id,
            "provider": provider,
            "metric": metric
        }

        # Calculate basic trend statistics if we have at least 2 data points
        valid_points = [p["value"] for p in data_points if p["value"] is not None]
        if len(valid_points) >= 2:
            trend_info["min"] = min(valid_points)
            trend_info["max"] = max(valid_points)
            trend_info["avg"] = sum(valid_points) / len(valid_points)

            # Calculate improvement/regression from first to last
            first = valid_points[0]
            last = valid_points[-1]
            change = ((last - first) / first) * 100 if first != 0 else 0
            trend_info["change_percent"] = change
            trend_info["improved"] = change < 0  # Lower is better for time metrics

        return trend_info

    def get_provider_comparison(self, test_id: int,
                              providers: Optional[List[str]] = None,
                              runs: int = 5) -> Dict:
        """
        Compare providers' performance on a specific test

        Args:
            test_id: ID of the test to analyze
            providers: List of providers to compare (optional)
            runs: Number of most recent runs to include in analysis

        Returns:
            Comparison data
        """
        test_key = f"test_{test_id}"
        if test_key not in self.history["test_results"]:
            return {"error": f"No history for test {test_id}"}

        # If no providers specified, use all available
        if not providers:
            providers = set()
            for run_id in self.history["test_results"][test_key]:
                run_data = self.history["test_results"][test_key][run_id]["results"]
                for run_key in run_data:
                    providers.update(run_data[run_key].keys())
            providers = list(providers)

        # Get the most recent runs
        sorted_runs = sorted(
            [(run_id, self.history["test_results"][test_key][run_id]["timestamp"])
             for run_id in self.history["test_results"][test_key]],
            key=lambda x: x[1]
        )
        recent_runs = sorted_runs[-runs:] if runs > 0 else sorted_runs

        # Collect comparison data
        comparison = {
            "test_id": test_id,
            "runs_analyzed": len(recent_runs),
            "providers": {},
            "fastest_provider": None,
            "most_consistent_provider": None
        }

        # Analyze each provider
        for provider in providers:
            provider_times = []
            error_count = 0

            for run_id, _ in recent_runs:
                run_data = self.history["test_results"][test_key][run_id]["results"]
                found = False

                for run_key in run_data:
                    if provider in run_data[run_key]:
                        found = True
                        provider_data = run_data[run_key][provider]

                        if provider_data.get("error"):
                            error_count += 1
                        else:
                            provider_times.append(provider_data.get("total_time", 0))
                        break

                if not found:
                    # Provider not present in this run
                    pass

            # Calculate statistics if we have data
            if provider_times:
                avg = np.mean(provider_times)
                stdev = np.std(provider_times)

                comparison["providers"][provider] = {
                    "avg_time": avg,
                    "stdev": stdev,
                    "cv": (stdev / avg) * 100 if avg > 0 else 0,  # coefficient of variation
                    "error_rate": (error_count / len(recent_runs)) * 100 if recent_runs else 0,
                    "samples": len(provider_times)
                }

        # Determine fastest and most consistent provider
        if comparison["providers"]:
            comparison["fastest_provider"] = min(
                comparison["providers"].items(),
                key=lambda x: x[1]["avg_time"]
            )[0]

            comparison["most_consistent_provider"] = min(
                [item for item in comparison["providers"].items() if item[1]["samples"] > 0],
                key=lambda x: x[1]["cv"] if x[1]["avg_time"] > 0 else float('inf')
            )[0] if any(p["samples"] > 0 for p in comparison["providers"].values()) else None

        return comparison