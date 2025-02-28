#!/usr/bin/env python3
"""
AI Sandbox Benchmark - Terminal User Interface

A curses-based TUI for the AI Sandbox Benchmark suite. This interface provides a
user-friendly way to select and run benchmarks across different sandbox providers.
"""
import os
import sys
import argparse
import asyncio
import curses
import textwrap
import time
from typing import List, Dict, Any, Optional, Tuple

import comparator
from comparator import SandboxExecutor, ResultsVisualizer, defined_tests
import numpy as np

def run_plain_benchmark(test_ids, providers, runs, warmup_runs, region):
    """Run benchmark in plain terminal mode (without curses)."""
    print("\n=== Running AI Sandbox Benchmark ===\n")
    print(f"Tests: {test_ids}")
    print(f"Providers: {providers}")
    print(f"Runs: {runs} (with {warmup_runs} warmup runs)")
    print(f"Region: {region}\n")
    
    # Check if CodeSandbox service is running if it's selected
    if 'codesandbox' in providers and not check_codesandbox_service(show_message=False):
        print("\nWARNING: CodeSandbox service is not running!")
        print("If you want to test with CodeSandbox, please run:")
        print("    node providers/codesandbox-service.js")
        print("\nAvailable options:")
        print("1. Continue without CodeSandbox (tests will fail)")
        print("2. Continue with all other providers (remove CodeSandbox)")
        print("3. Abort benchmark")
        
        while True:
            choice = input("\nEnter your choice (1-3): ").strip()
            if choice == '1':
                print("Continuing with all providers, CodeSandbox tests will fail...")
                break
            elif choice == '2':
                providers.remove('codesandbox')
                print(f"Continuing with providers: {', '.join(providers)}")
                break
            elif choice == '3':
                print("Benchmark aborted.")
                return
            else:
                print("Invalid choice, please enter 1, 2, or 3.")
    
    # Completely exit and restart Python process with the benchmark command
    os.system(f"python comparator.py --tests {','.join(map(str, test_ids))} --providers {','.join(providers)} --runs {runs} --warmup-runs {warmup_runs} --target-region {region}")
    
    # Wait for user acknowledgment before exiting
    print("\nBenchmark finished. Press Enter to exit...")
    input()


class BenchmarkTUI:
    """Terminal User Interface for AI Sandbox Benchmark."""
    
    def __init__(self, stdscr):
        """Initialize the TUI with curses screen and default configuration."""
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Configure colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # Selected items
        curses.init_pair(2, curses.COLOR_YELLOW, -1)  # Headers
        curses.init_pair(3, curses.COLOR_RED, -1)    # Errors
        curses.init_pair(4, curses.COLOR_CYAN, -1)   # Highlighted options
        # Use dark text on light background for better contrast (WCAG compliant)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Status bar - high contrast
        
        # Default configuration
        self.runs = 1
        self.warmup_runs = 0
        self.region = "eu"
        
        # Available providers and tests
        self.providers = ["daytona", "e2b", "codesandbox", "modal"]
        self.selected_providers = self.providers.copy()  # Select all by default
        self.selected_tests = [1]  # Start with just the first test selected
        
        # UI state
        self.status_message = ""
        self.status_type = "info"  # "info", "error", "success"
        self.current_view = "main"  # "main", "providers", "tests", "config", "results"
        self.scroll_offset = 0
        self.menu_cursor = 0
        self.results_content = []
        
        # Initialize curses settings
        curses.curs_set(0)  # Hide cursor
        self.stdscr.timeout(100)  # For handling resize events
        self.stdscr.keypad(True)  # Enable keypad mode
    
    def update_dimensions(self):
        """Update screen dimensions when terminal is resized."""
        self.height, self.width = self.stdscr.getmaxyx()
    
    def display_header(self):
        """Display application header."""
        title = "AI Sandbox Benchmark"
        # Use bold instead of color for better accessibility
        self.stdscr.addstr(1, (self.width - len(title)) // 2, title, curses.A_BOLD)
        self.stdscr.addstr(2, (self.width - len("=" * 40)) // 2, "=" * 40)
    
    def display_footer(self):
        """Display status bar and help text at the bottom of the screen."""
        help_text = "↑/↓:Navigate | Space:Toggle | Enter:Select/Run | q:Back/Quit"
        
        # Draw status bar
        status_attr = curses.color_pair(5)
        self.stdscr.addstr(self.height - 2, 0, " " * self.width, status_attr)
        
        # Set status message style - high contrast and WCAG compliant
        if self.status_type == "error":
            msg_attr = curses.A_BOLD | curses.A_UNDERLINE  # Bold + underline for error messages
        elif self.status_type == "warn":
            msg_attr = curses.A_BOLD  # Bold for warning messages
        elif self.status_type == "success":
            msg_attr = curses.A_BOLD  # Bold for success messages
        else:
            msg_attr = curses.A_NORMAL  # Normal for info messages
        
        # Display status message (truncate if too long)
        max_msg_len = self.width - 2
        status_msg = self.status_message[:max_msg_len] if len(self.status_message) > max_msg_len else self.status_message
        self.stdscr.addstr(self.height - 2, 2, status_msg, status_attr | msg_attr)
        
        # Display help text
        footer_y = self.height - 1
        self.stdscr.addstr(footer_y, (self.width - len(help_text)) // 2, help_text)
    
    def display_main_menu(self):
        """Display the main menu screen."""
        # Display configuration summary
        config_y = 4
        self.stdscr.addstr(config_y, 3, "Current Configuration:", curses.A_BOLD)
        self.stdscr.addstr(config_y + 1, 5, f"Runs: {self.runs}")
        self.stdscr.addstr(config_y + 2, 5, f"Warmup runs: {self.warmup_runs}")
        self.stdscr.addstr(config_y + 3, 5, f"Region: {self.region}")
        
        # Display provider summary
        providers_y = config_y + 5
        self.stdscr.addstr(providers_y, 3, "Providers:", curses.A_BOLD)
        provider_text = ", ".join([p if p in self.selected_providers else f"({p})" for p in self.providers])
        self.stdscr.addstr(providers_y + 1, 5, provider_text)
        
        # Display test summary
        tests_y = providers_y + 3
        self.stdscr.addstr(tests_y, 3, "Tests:", curses.A_BOLD)
        selected_test_names = []
        for test_id in self.selected_tests:
            test_func = defined_tests.get(test_id)
            if test_func:
                is_single_run = hasattr(test_func, 'single_run') and test_func.single_run
                test_name = test_func.__name__
                if is_single_run:
                    test_name += " (single)"
                selected_test_names.append(f"{test_id}:{test_name}")
        
        # Wrap and display test names
        if selected_test_names:
            test_text = ", ".join(selected_test_names)
            wrapped_lines = textwrap.wrap(test_text, self.width - 10)
            for i, line in enumerate(wrapped_lines[:3]):  # Show max 3 lines
                self.stdscr.addstr(tests_y + 1 + i, 5, line)
            if len(wrapped_lines) > 3:
                self.stdscr.addstr(tests_y + 4, 5, "... and more")
        else:
            self.stdscr.addstr(tests_y + 1, 5, "No tests selected", curses.color_pair(3))
        
        # Display menu options
        menu_options = [
            ("R", "Run benchmark"),
            ("P", "Configure providers"),
            ("T", "Configure tests"),
            ("C", "Configure runs"),
            ("A", "Select all tests"),
            ("N", "Deselect all tests"),
            ("Q", "Quit")
        ]
        
        menu_y = tests_y + 6
        self.stdscr.addstr(menu_y, 3, "Menu:", curses.A_BOLD)
        
        for i, (key, description) in enumerate(menu_options):
            y = menu_y + i + 1
            attr = curses.A_NORMAL
            
            if i == self.menu_cursor:
                attr |= curses.A_BOLD  # Only use bold for selected menu item, not colors
                self.stdscr.addstr(y, 5, "→ ", attr)
            else:
                self.stdscr.addstr(y, 5, "  ")
                
            self.stdscr.addstr(y, 7, f"{key}: {description}", attr)
    
    def display_providers_menu(self):
        """Display the providers configuration screen."""
        self.stdscr.addstr(4, 3, "Select Providers:", curses.A_BOLD)
        self.stdscr.addstr(5, 3, "Use ↑/↓ to navigate, Space to toggle, Enter to confirm, q to return")
        
        for i, provider in enumerate(self.providers):
            y = 7 + i
            status = "[✓]" if provider in self.selected_providers else "[ ]"
            attr = curses.A_NORMAL
            
            if i == self.menu_cursor:
                attr |= curses.A_BOLD  # Only use bold for selected menu item
                self.stdscr.addstr(y, 5, "→ ", attr)
            else:
                self.stdscr.addstr(y, 5, "  ")
            
            # Use bold for selected providers instead of colors to ensure readability
            if provider in self.selected_providers:
                attr |= curses.A_BOLD
                
            self.stdscr.addstr(y, 7, f"{status} {provider}", attr)
    
    def display_tests_menu(self):
        """Display the tests configuration screen."""
        self.stdscr.addstr(4, 3, "Select Tests:", curses.A_BOLD)
        self.stdscr.addstr(5, 3, "Use ↑/↓ to navigate, Space to toggle, Enter to confirm, q to return")
        
        offset = self.scroll_offset
        visible_items = min(self.height - 12, len(defined_tests))
        
        # Show scroll indicators if needed
        if offset > 0:
            self.stdscr.addstr(6, self.width // 2, "↑ (more tests above)")
        if offset + visible_items < len(defined_tests):
            self.stdscr.addstr(7 + visible_items, self.width // 2, "↓ (more tests below)")
        
        for i, (test_id, test_func) in enumerate(list(defined_tests.items())[offset:offset+visible_items]):
            y = 7 + i
            is_single_run = hasattr(test_func, 'single_run') and test_func.single_run
            single_run_info = " (single run)" if is_single_run else ""
            status = "[✓]" if test_id in self.selected_tests else "[ ]"
            attr = curses.A_NORMAL
            
            if i + offset == self.menu_cursor:
                attr |= curses.A_BOLD  # Only use bold for selected item
                self.stdscr.addstr(y, 5, "→ ", attr)
            else:
                self.stdscr.addstr(y, 5, "  ")
            
            # Use bold for selected tests instead of colors to ensure readability
            if test_id in self.selected_tests:
                attr |= curses.A_BOLD
                
            test_name = f"{test_id}. {status} {test_func.__name__}{single_run_info}"
            max_width = self.width - 10
            if len(test_name) > max_width:
                test_name = test_name[:max_width-3] + "..."
                
            self.stdscr.addstr(y, 7, test_name, attr)
    
    def display_config_menu(self):
        """Display the runs configuration screen."""
        self.stdscr.addstr(4, 3, "Configure Run Parameters:", curses.A_BOLD)
        
        menu_options = [
            ("Measurement runs", f"{self.runs} (1-20)"),
            ("Warmup runs", f"{self.warmup_runs} (0-5)"),
            ("Region", f"{self.region} (eu, us, asia)"),
            ("Save and return", "")
        ]
        
        for i, (option, value) in enumerate(menu_options):
            y = 6 + i * 2
            attr = curses.A_NORMAL
            
            if i == self.menu_cursor:
                attr |= curses.A_BOLD  # Only use bold for selected item
                self.stdscr.addstr(y, 5, "→ ", attr)
            else:
                self.stdscr.addstr(y, 5, "  ")
                
            self.stdscr.addstr(y, 7, option, attr)
            if value:
                self.stdscr.addstr(y, 7 + len(option) + 2, value)
    
    def display_results_view(self):
        """Display benchmark results screen."""
        self.stdscr.addstr(4, 3, "Benchmark Results:", curses.A_BOLD)
        self.stdscr.addstr(5, 3, "Press q to return to main menu")
        
        if not self.results_content:
            self.stdscr.addstr(7, 5, "No results to display", curses.color_pair(3))
            return
        
        visible_height = self.height - 8
        max_lines = min(len(self.results_content), visible_height)
        
        for i in range(max_lines):
            line_idx = i + self.scroll_offset
            if line_idx < len(self.results_content):
                line = self.results_content[line_idx]
                # Truncate if line is too long
                max_width = self.width - 6
                if len(line[0]) > max_width:
                    display_line = line[0][:max_width-3] + "..."
                else:
                    display_line = line[0]
                    
                self.stdscr.addstr(7 + i, 5, display_line, line[1])
                
        # Show scroll indicators if needed
        if self.scroll_offset > 0:
            self.stdscr.addstr(6, self.width // 2, "↑ (scroll up for more)")
        if self.scroll_offset + visible_height < len(self.results_content):
            self.stdscr.addstr(self.height - 2, self.width // 2, "↓ (scroll down for more)")
    
    def render(self):
        """Render the current view."""
        self.stdscr.clear()
        self.update_dimensions()
        self.display_header()
        
        if self.current_view == "main":
            self.display_main_menu()
        elif self.current_view == "providers":
            self.display_providers_menu()
        elif self.current_view == "tests":
            self.display_tests_menu()
        elif self.current_view == "config":
            self.display_config_menu()
        elif self.current_view == "results":
            self.display_results_view()
        # Note: benchmark_running view is handled separately in run_benchmark()
        
        self.display_footer()
        self.stdscr.refresh()
    
    def handle_main_menu_input(self, key):
        """Handle keyboard input on the main menu."""
        if key == curses.KEY_UP:
            self.menu_cursor = max(0, self.menu_cursor - 1)
        elif key == curses.KEY_DOWN:
            self.menu_cursor = min(6, self.menu_cursor + 1)
        elif key == ord(' '):  # Space to toggle options
            if self.menu_cursor == 4:  # Select all tests
                self.selected_tests = list(defined_tests.keys())
                self.set_status("All tests selected", "success")
            elif self.menu_cursor == 5:  # Deselect all tests
                self.selected_tests = []
                self.set_status("All tests deselected", "info")
        elif key in (curses.KEY_ENTER, 10, 13):  # Enter to select/execute
            if self.menu_cursor == 0:  # Run benchmark
                if not self.selected_tests:
                    self.set_status("Please select at least one test to run.", "error")
                elif not self.selected_providers:
                    self.set_status("Please select at least one provider.", "error")
                elif 'codesandbox' in self.selected_providers and not self.check_codesandbox_service():
                    self.set_status("CodeSandbox service not detected. Run 'node providers/codesandbox-service.js' first!", "error")
                    # Give user time to read the warning
                    self.stdscr.refresh()
                    time.sleep(1.5)
                else:
                    self.set_status("Starting benchmark...", "info")
                    # Direct execution to avoid asyncio nesting problems
                    self.stdscr.clear()
                    curses.endwin()
                    # Run benchmark in plain terminal mode
                    run_plain_benchmark(self.selected_tests, self.selected_providers, self.runs, self.warmup_runs, self.region)
                    # Exit after benchmark completes
                    return False
            elif self.menu_cursor == 1:  # Configure providers
                self.switch_to_providers()
            elif self.menu_cursor == 2:  # Configure tests
                self.switch_to_tests()
            elif self.menu_cursor == 3:  # Configure runs
                self.switch_to_config()
            elif self.menu_cursor == 4:  # Select all tests
                self.selected_tests = list(defined_tests.keys())
                self.set_status("All tests selected", "success")
            elif self.menu_cursor == 5:  # Deselect all tests
                self.selected_tests = []
                self.set_status("All tests deselected", "info")
            elif self.menu_cursor == 6:  # Quit
                return False
        elif key in (ord('r'), ord('R')):
            if not self.selected_tests:
                self.set_status("Please select at least one test to run.", "error")
            elif not self.selected_providers:
                self.set_status("Please select at least one provider.", "error")
            elif 'codesandbox' in self.selected_providers and not self.check_codesandbox_service():
                self.set_status("CodeSandbox service not detected. Run 'node providers/codesandbox-service.js' first!", "warn")
                # Give user time to read the warning
                self.stdscr.refresh()
                time.sleep(1.5)
            else:
                self.set_status("Starting benchmark...", "info")
                # Direct execution to avoid asyncio nesting problems
                self.stdscr.clear()
                curses.endwin()
                # Run benchmark in plain terminal mode
                run_plain_benchmark(self.selected_tests, self.selected_providers, self.runs, self.warmup_runs, self.region)
                # Exit after benchmark completes
                return False
        elif key in (ord('p'), ord('P')):
            self.switch_to_providers()
        elif key in (ord('t'), ord('T')):
            self.switch_to_tests()
        elif key in (ord('c'), ord('C')):
            self.switch_to_config()
        elif key in (ord('a'), ord('A')):
            self.selected_tests = list(defined_tests.keys())
            self.set_status("All tests selected", "success")
        elif key in (ord('n'), ord('N')):
            self.selected_tests = []
            self.set_status("All tests deselected", "info")
        elif key in (ord('q'), ord('Q')):
            return False
        return True
    
    def handle_providers_menu_input(self, key):
        """Handle keyboard input on the providers menu."""
        if key == curses.KEY_UP:
            self.menu_cursor = max(0, self.menu_cursor - 1)
        elif key == curses.KEY_DOWN:
            self.menu_cursor = min(len(self.providers) - 1, self.menu_cursor + 1)
        elif key == ord(' '):  # Space to toggle
            provider = self.providers[self.menu_cursor]
            if provider in self.selected_providers:
                self.selected_providers.remove(provider)
                self.set_status(f"Provider '{provider}' deselected", "info")
            else:
                # Special handling for CodeSandbox
                if provider == 'codesandbox' and not self.check_codesandbox_service():
                    self.selected_providers.append(provider)
                    self.set_status(f"Provider '{provider}' selected, but service not detected. Run 'node providers/codesandbox-service.js' first!", "warn")
                else:
                    self.selected_providers.append(provider)
                    self.set_status(f"Provider '{provider}' selected", "success")
        elif key in (curses.KEY_ENTER, 10, 13):  # Enter to confirm and return
            # Check for CodeSandbox service if it's selected
            if 'codesandbox' in self.selected_providers and not self.check_codesandbox_service():
                self.set_status("WARNING: CodeSandbox service not detected. Run 'node providers/codesandbox-service.js' first!", "warn")
                # Brief pause to show the warning
                self.stdscr.refresh()
                time.sleep(1)
            
            self.switch_to_main()
            self.set_status("Provider selection saved", "success")
        elif key in (ord('q'), ord('Q')):
            self.switch_to_main()
        return True
    
    def handle_tests_menu_input(self, key):
        """Handle keyboard input on the tests menu."""
        if key == curses.KEY_UP:
            if self.menu_cursor > 0:
                self.menu_cursor -= 1
                if self.menu_cursor < self.scroll_offset:
                    self.scroll_offset = self.menu_cursor
        elif key == curses.KEY_DOWN:
            if self.menu_cursor < len(defined_tests) - 1:
                self.menu_cursor += 1
                visible_height = min(self.height - 12, len(defined_tests))
                if self.menu_cursor >= self.scroll_offset + visible_height:
                    self.scroll_offset = self.menu_cursor - visible_height + 1
        elif key == ord(' '):  # Space to toggle
            test_id = list(defined_tests.keys())[self.menu_cursor]
            if test_id in self.selected_tests:
                self.selected_tests.remove(test_id)
                self.set_status(f"Test {test_id} deselected", "info")
            else:
                self.selected_tests.append(test_id)
                self.set_status(f"Test {test_id} selected", "success")
        elif key in (curses.KEY_ENTER, 10, 13):  # Enter to confirm and return
            self.switch_to_main()
            self.set_status("Test selection saved", "success")
        elif key in (ord('q'), ord('Q')):
            self.switch_to_main()
        return True
    
    def handle_config_menu_input(self, key):
        """Handle keyboard input on the configuration menu."""
        if key == curses.KEY_UP:
            self.menu_cursor = max(0, self.menu_cursor - 1)
        elif key == curses.KEY_DOWN:
            self.menu_cursor = min(3, self.menu_cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if self.menu_cursor == 0:  # Runs
                self.edit_config_value("runs")
            elif self.menu_cursor == 1:  # Warmup runs
                self.edit_config_value("warmup_runs")
            elif self.menu_cursor == 2:  # Region
                self.edit_config_value("region")
            elif self.menu_cursor == 3:  # Save and return
                self.switch_to_main()
        elif key in (ord('q'), ord('Q')):
            self.switch_to_main()
        return True
    
    def handle_results_view_input(self, key):
        """Handle keyboard input on the results view."""
        if key == curses.KEY_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            max_scroll = max(0, len(self.results_content) - (self.height - 8))
            self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            self.scroll_offset = max(0, self.scroll_offset - (self.height - 8))
        elif key == curses.KEY_NPAGE:  # Page Down
            max_scroll = max(0, len(self.results_content) - (self.height - 8))
            self.scroll_offset = min(max_scroll, self.scroll_offset + (self.height - 8))
        elif key in (ord('q'), ord('Q')):
            self.switch_to_main()
        return True
    
    def edit_config_value(self, config_type):
        """Edit a configuration value."""
        curses.curs_set(1)  # Show cursor
        
        y, prompt, current, validator = 0, "", "", lambda x: True
        if config_type == "runs":
            y = 6
            prompt = "Enter measurement runs (1-20): "
            current = str(self.runs)
            validator = lambda x: x.isdigit() and 1 <= int(x) <= 20
        elif config_type == "warmup_runs":
            y = 8
            prompt = "Enter warmup runs (0-5): "
            current = str(self.warmup_runs)
            validator = lambda x: x.isdigit() and 0 <= int(x) <= 5
        elif config_type == "region":
            y = 10
            prompt = "Enter region (eu, us, asia): "
            current = self.region
            validator = lambda x: x.lower() in ["eu", "us", "asia"]
        
        # Display prompt and input field
        self.stdscr.addstr(y, 30, " " * 20)  # Clear previous value
        self.stdscr.addstr(y, 30, prompt)
        input_y, input_x = y, 30 + len(prompt)
        
        # Edit loop
        user_input = current
        while True:
            self.stdscr.addstr(input_y, input_x, user_input + " " * 10)  # Clear trailing chars
            self.stdscr.move(input_y, input_x + len(user_input))
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            if key in (curses.KEY_ENTER, 10, 13):  # Enter
                if validator(user_input):
                    if config_type == "runs":
                        self.runs = int(user_input)
                        self.set_status(f"Measurement runs set to {self.runs}", "success")
                    elif config_type == "warmup_runs":
                        self.warmup_runs = int(user_input)
                        self.set_status(f"Warmup runs set to {self.warmup_runs}", "success")
                    elif config_type == "region":
                        self.region = user_input.lower()
                        self.set_status(f"Region set to {self.region}", "success")
                    break
                else:
                    # Display validation error
                    self.set_status(f"Invalid input for {config_type}", "error")
            elif key in (27, ord('q'), ord('Q')):  # Escape or q
                break
            elif key in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
                user_input = user_input[:-1]
            elif 32 <= key <= 126:  # Printable characters
                if len(user_input) < 10:  # Limit input length
                    user_input += chr(key)
        
        curses.curs_set(0)  # Hide cursor
        self.render()  # Refresh screen
    
    def set_status(self, message, message_type="info"):
        """Set the status message and type."""
        self.status_message = message
        self.status_type = message_type
    
    def switch_to_main(self):
        """Switch to main menu view."""
        self.current_view = "main"
        self.menu_cursor = 0
        self.scroll_offset = 0
    
    def switch_to_providers(self):
        """Switch to providers configuration view."""
        self.current_view = "providers"
        self.menu_cursor = 0
    
    def switch_to_tests(self):
        """Switch to tests configuration view."""
        self.current_view = "tests"
        self.menu_cursor = 0
        self.scroll_offset = 0
    
    def switch_to_config(self):
        """Switch to run configuration view."""
        self.current_view = "config"
        self.menu_cursor = 0
    
    def switch_to_results(self):
        """Switch to results view."""
        self.current_view = "results"
        self.scroll_offset = 0
    
    async def run_benchmark(self):
        """Run benchmark with selected configuration."""
        # Set screen to benchmark view first
        self.current_view = "benchmark_running"

        # Save the current screen state
        current_screen = self.stdscr
        
        # Force a full refresh
        current_screen.clear()
        self.display_header()
        
        # Show running benchmark screen
        current_screen.addstr(4, 3, "Running Benchmark...", curses.A_BOLD)
        
        # Create a progress indicator
        progress_y = 6
        progress_x = 5
        progress_width = self.width - 10
        
        current_screen.addstr(progress_y, progress_x, "┌" + "─" * progress_width + "┐")
        current_screen.addstr(progress_y + 1, progress_x, "│" + " " * progress_width + "│")
        current_screen.addstr(progress_y + 2, progress_x, "└" + "─" * progress_width + "┘")
        
        status_y = progress_y + 4
        current_screen.addstr(status_y, 5, "Executing tests...")
        current_screen.refresh()
        
        # Record which providers are being tested
        provider_status = {}
        for provider in self.selected_providers:
            provider_status[provider] = "Preparing..."
            
        # Update UI with provider status - improved for parallel execution
        def update_provider_status():
            for i, (provider, status) in enumerate(provider_status.items()):
                if i + status_y + 1 < self.height - 3:  # Avoid writing beyond screen bounds
                    current_screen.addstr(status_y + i + 1, 7, " " * (self.width - 14))  # Clear line
                    
                    # Add indicators based on status, but keep text visible
                    status_attr = curses.A_NORMAL
                    if "Running" in status:
                        status_attr = curses.A_BOLD  # Bold for running
                    elif "Completed" in status:
                        status_attr = curses.A_BOLD  # Bold for completed
                    elif "Failed" in status:
                        status_attr = curses.A_BOLD  # Bold for failed
                    
                    current_screen.addstr(status_y + i + 1, 7, f"{provider}: ", curses.A_BOLD)
                    current_screen.addstr(status_y + i + 1, 9 + len(provider), status, status_attr)
            current_screen.refresh()
        
        update_provider_status()
        
        # Animation for progress bar
        animation_chars = ["▒", "░", "▓", "█"]
        animation_idx = 0
        progress_position = 0
        
        # Create a task for UI updates
        def update_progress():
            nonlocal animation_idx, progress_position
            animation_idx = (animation_idx + 1) % len(animation_chars)
            progress_position = (progress_position + 1) % progress_width
            
            # Draw progress animation
            progress_bar = " " * progress_width
            for i in range(min(progress_width, 10)):  # Show 10 animation chars
                pos = (progress_position + i) % progress_width
                progress_bar = progress_bar[:pos] + animation_chars[animation_idx] + progress_bar[pos+1:]
            
            current_screen.addstr(progress_y + 1, progress_x + 1, progress_bar)
            update_time = time.strftime("%H:%M:%S", time.localtime())
            current_screen.addstr(status_y, 5, f"Executing tests... Please wait [{update_time}]")
            update_provider_status()
            current_screen.refresh()
        
        # Track test state
        current_test_id = None
        current_provider = None
        
        # Redefine provider execution with progress updates
        original_run_test = SandboxExecutor.run_test_on_provider
        
        async def run_test_with_updates(self_executor, test_code_func, provider, executor, target_region):
            nonlocal current_test_id, current_provider
            # Update status before running
            test_name = test_code_func.__name__ if hasattr(test_code_func, "__name__") else "unknown"
            provider_status[provider] = f"Running {test_name}..."
            current_provider = provider
            update_provider_status()
            update_progress()
            
            # Run the original function
            result = await original_run_test(self_executor, test_code_func, provider, executor, target_region)
            
            # Update status after completion
            provider_name, results_dict, error = result
            if error:
                provider_status[provider] = f"Failed: {str(error)[:30]}..."
            else:
                provider_status[provider] = f"Completed {test_name}"
            update_provider_status()
            
            return result
        
        # Monkey patch temporarily
        SandboxExecutor.run_test_on_provider = run_test_with_updates
        
        # Convert selected tests to the format expected by SandboxExecutor
        tests_to_run = {test_id: defined_tests[test_id] for test_id in self.selected_tests}
        
        try:
            # Create executor with parallel provider execution
            executor = SandboxExecutor(
                warmup_runs=self.warmup_runs,
                measurement_runs=self.runs,
                num_concurrent_providers=len(self.selected_providers)  # Each provider can run in parallel
            )
            
            # Update UI to show parallel execution
            current_screen.addstr(status_y - 2, 5, f"Running {len(self.selected_providers)} providers in parallel")
            
            # Set up periodic progress updates
            loop = asyncio.get_event_loop()
            update_task = None
            
            def progress_callback():
                nonlocal update_task
                update_progress()
                update_task = loop.call_later(0.2, progress_callback)
            
            update_task = loop.call_later(0.2, progress_callback)
            
            # Start the benchmark
            results = await executor.run_comparison(
                tests_to_run,
                self.selected_providers,
                self.runs,
                self.region
            )
            
            # Cancel progress animation
            if update_task:
                update_task.cancel()
            
            # Restore original method
            SandboxExecutor.run_test_on_provider = original_run_test
            
            # Show completion message
            current_screen.addstr(progress_y + 1, progress_x + 1, " " * progress_width)
            current_screen.addstr(progress_y + 1, progress_x + 1, "✓ Benchmark completed successfully!", curses.color_pair(1) | curses.A_BOLD)
            current_screen.refresh()
            
            # Process results
            self.process_results(results, tests_to_run)
            
            # Show results
            time.sleep(1)  # Brief pause to show completion message
            self.switch_to_results()
            self.set_status("Benchmark completed successfully", "success")
            
        except Exception as e:
            # Restore original method
            SandboxExecutor.run_test_on_provider = original_run_test
            
            # Show error
            current_screen.addstr(progress_y + 1, progress_x + 1, " " * progress_width)
            current_screen.addstr(progress_y + 1, progress_x + 1, f"✗ Error: {str(e)[:progress_width-10]}", curses.color_pair(3) | curses.A_BOLD)
            current_screen.refresh()
            
            self.set_status(f"Error during benchmark: {str(e)}", "error")
            self.results_content = [
                (f"Error during benchmark: {str(e)}", curses.color_pair(3) | curses.A_BOLD),
                ("", curses.A_NORMAL),
                ("Press q to return to the main menu", curses.A_NORMAL)
            ]
            
            # Brief pause to show error message
            time.sleep(2)
            self.switch_to_results()
        
        return True
    
    def process_results(self, results, tests_to_run):
        """Process and format the benchmark results."""
        visualizer = ResultsVisualizer()
        
        # Create format handler to capture and process tabulate output
        self.results_content = []
        
        # Add header - high contrast for WCAG compliance
        self.results_content.append(("Benchmark Results", curses.A_BOLD))
        self.results_content.append(("", curses.A_NORMAL))
        
        # Add summary info - high contrast for WCAG compliance
        self.results_content.append(("Test Configuration Summary", curses.A_BOLD))
        self.results_content.append(("=" * 40, curses.A_NORMAL))
        self.results_content.append((f"Warmup Runs: {self.warmup_runs}", curses.A_NORMAL))
        self.results_content.append((f"Measurement Runs: {self.runs}", curses.A_NORMAL))
        
        tests_used = ', '.join(f"{tid}:{func.__name__}" for tid, func in tests_to_run.items())
        self.results_content.append((f"Tests Used ({len(tests_to_run)}): {tests_used}", curses.A_NORMAL))
        self.results_content.append((f"Providers Used: {', '.join(self.selected_providers)}", curses.A_NORMAL))
        self.results_content.append(("=" * 40, curses.A_NORMAL))
        self.results_content.append(("", curses.A_NORMAL))
        
        # Process individual test results
        for test_id, test_code_func in tests_to_run.items():
            # Use bold only for better accessibility
            self.results_content.append((f"Performance for Test {test_id}: {test_code_func.__name__}", 
                                      curses.A_BOLD))
            self.results_content.append(("", curses.A_NORMAL))
            
            test_results = results.get(f"test_{test_id}", {})
            
            # Get example output
            first_run_results = test_results.get("run_1", {})
            first_provider_output = None
            for provider in self.selected_providers:
                if provider in first_run_results and 'output' in first_run_results[provider]:
                    first_provider_output = first_run_results[provider]['output']
                    break
            
            if first_provider_output:
                self.results_content.append(("Example Output:", curses.A_BOLD))
                for line in first_provider_output.split('\n')[:5]:  # Show first 5 lines
                    self.results_content.append((line, curses.A_NORMAL))
                if first_provider_output.count('\n') > 5:
                    self.results_content.append(("... (output truncated)", curses.A_NORMAL))
                self.results_content.append(("", curses.A_NORMAL))
            
            # Process performance data
            metrics = ["Workspace Creation", "Code Execution", "Cleanup", "Total Time"]
            self.results_content.append(("Performance Metrics (ms):", curses.A_BOLD))
            
            # Headers
            header_line = f"{'Metric':<20}"
            for provider in self.selected_providers:
                header_line += f"{provider:<15}"
            self.results_content.append((header_line, curses.A_BOLD))
            self.results_content.append(("-" * len(header_line), curses.A_NORMAL))
            
            # Process each metric
            for metric in metrics:
                metric_line = f"{metric:<20}"
                for provider in self.selected_providers:
                    value = "N/A"
                    if metric == "Total Time":
                        # Calculate total time across all runs
                        total_times = []
                        for run_num in range(1, self.runs + 1):
                            run_results = test_results.get(f"run_{run_num}", {})
                            if provider in run_results:
                                total_times.append(run_results[provider]['metrics'].get_total_time())
                        if total_times:
                            value = f"{np.mean(total_times):.2f}"
                    else:
                        # Calculate metrics for standard metrics
                        all_runs_metrics = []
                        for run_num in range(1, self.runs + 1):
                            run_results = test_results.get(f"run_{run_num}", {})
                            if provider in run_results:
                                run_metric = run_results[provider]['metrics'].get_statistics().get(metric, {})
                                if run_metric:
                                    all_runs_metrics.append(run_metric['mean'])
                        if all_runs_metrics:
                            avg_metric = np.mean(all_runs_metrics)
                            std_metric = np.std(all_runs_metrics)
                            value = f"{avg_metric:.2f}±{std_metric:.2f}"
                    
                    metric_line += f"{value:<15}"
                
                # Color the metric line based on the metric type
                attr = curses.A_NORMAL
                if metric == "Total Time":
                    attr = curses.A_BOLD
                self.results_content.append((metric_line, attr))
            
            # Check for errors
            errors_found = False
            for provider in self.selected_providers:
                fail_count = 0
                for run_num in range(1, self.runs + 1):
                    run_results = test_results.get(f"run_{run_num}", {})
                    if provider in run_results and run_results[provider].get('error'):
                        fail_count += 1
                if fail_count > 0:
                    errors_found = True
                    error_msg = f"{provider} failed {fail_count}/{self.runs} runs"
                    # Use underline and bold instead of color for better accessibility
                    self.results_content.append((error_msg, curses.A_BOLD | curses.A_UNDERLINE))
            
            if not errors_found:
                self.results_content.append(("No failures recorded for this test.", curses.A_NORMAL))
            
            self.results_content.append(("", curses.A_NORMAL))
            self.results_content.append(("=" * 40, curses.A_NORMAL))
            self.results_content.append(("", curses.A_NORMAL))
    
    def check_codesandbox_service(self):
        """Check if the CodeSandbox service is running."""
        return check_codesandbox_service(show_message=False)
    
    async def main_loop(self):
        """Main application loop."""
        running = True
        # Store any pending task
        self.pending_benchmark = None
        
        # Check for CodeSandbox service if it's selected
        if 'codesandbox' in self.selected_providers and not self.check_codesandbox_service():
            # Use "warn" instead of "error" for better visibility with our WCAG-compliant colors
            self.set_status("WARNING: CodeSandbox service not detected. Run 'node providers/codesandbox-service.js' first!", "warn")
        
        while running:
            self.render()
            
            try:
                # Check for timeout to allow async tasks to run
                self.stdscr.timeout(100)
                key = self.stdscr.getch()
                
                # Handle no key (for async processing)
                if key == -1:
                    continue
                
                # Handle window resize event
                if key == curses.KEY_RESIZE:
                    self.update_dimensions()
                    continue
                
                # Handle view-specific inputs
                if self.current_view == "main":
                    running = self.handle_main_menu_input(key)
                elif self.current_view == "providers":
                    running = self.handle_providers_menu_input(key)
                elif self.current_view == "tests":
                    running = self.handle_tests_menu_input(key)
                elif self.current_view == "config":
                    running = self.handle_config_menu_input(key)
                elif self.current_view == "results":
                    running = self.handle_results_view_input(key)
                
            except Exception as e:
                self.set_status(f"Error: {str(e)}", "error")


def run_tui():
    """Simple wrapper function to run the TUI."""
    try:
        # Use a simple wrapper to handle curses setup/teardown
        curses.wrapper(run_with_curses)
    except KeyboardInterrupt:
        print("Benchmark interrupted by user.")
        sys.exit(0)

def run_with_curses(stdscr):
    """Run the TUI with a curses screen."""
    # Create an event loop for asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Initialize curses
    curses.curs_set(0)  # Hide cursor
    curses.use_default_colors()  # Allow default colors
    stdscr.clear()
    
    # Create and run the TUI
    tui = BenchmarkTUI(stdscr)
    try:
        loop.run_until_complete(tui.main_loop())
    finally:
        loop.close()

def parse_args():
    """Parse command line arguments for direct CLI usage."""
    parser = argparse.ArgumentParser(description="AI Sandbox Benchmark Suite")
    parser.add_argument('--cli', action='store_true', 
                      help='Run in command-line mode instead of TUI')
    parser.add_argument('--tests', '-t', type=str, default='all',
                      help='Comma-separated list of test IDs to run (or "all" for all tests)')
    parser.add_argument('--providers', '-p', type=str, default='daytona,e2b,codesandbox,modal',
                      help='Comma-separated list of providers to test')
    parser.add_argument('--runs', '-r', type=int, default=1,
                      help='Number of measurement runs per test/provider')
    parser.add_argument('--warmup-runs', '-w', type=int, default=0,
                      help='Number of warmup runs')
    parser.add_argument('--target-region', type=str, default='eu',
                      help='Target region (eu, us, asia)')
    
    return parser.parse_args()

def check_codesandbox_service(show_message=True):
    """Check if the CodeSandbox service is running."""
    try:
        import requests
        response = requests.get("http://localhost:3000/status", timeout=0.5)
        return response.status_code == 200
    except:
        if show_message:
            print("\nNOTE: CodeSandbox service is not running.")
            print("If you want to run tests with CodeSandbox, start the service with:")
            print("    node providers/codesandbox-service.js")
            print("Otherwise, you can ignore this message.\n")
        return False

if __name__ == "__main__":
    args = parse_args()
    
    # Check CodeSandbox service at startup
    providers_list = args.providers.split(',')
    if 'codesandbox' in providers_list:
        check_codesandbox_service()
    
    if args.cli:
        # Run in CLI mode with the provided arguments
        test_ids = []
        if args.tests == "all":
            test_ids = list(defined_tests.keys())
        else:
            test_ids = [int(tid) for tid in args.tests.split(',')]
        
        # Use the plain benchmark runner
        run_plain_benchmark(
            test_ids, 
            providers_list,
            args.runs, 
            args.warmup_runs, 
            args.target_region
        )
    else:
        # Run the TUI
        run_tui()