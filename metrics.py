#!/usr/bin/env python3
import numpy as np

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

    def get_statistics(self) -> dict:
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