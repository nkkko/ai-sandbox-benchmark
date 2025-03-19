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

    # Run comparator directly rather than using os.system
    print("Running benchmark. Please wait...\n")
    # Import here to avoid circular imports
    import comparator as comp
    executor = comp.SandboxExecutor(
        warmup_runs=warmup_runs,
        measurement_runs=runs,
        num_concurrent_providers=len(providers)
    )

    # Get tests to run
    tests_to_run = {test_id: comp.defined_tests[test_id] for test_id in test_ids}

    # Run the benchmark using asyncio
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    results = loop.run_until_complete(executor.run_comparison(
        tests_to_run,
        providers,
        runs,
        region
    ))

    # Visualize results
    visualizer = comp.ResultsVisualizer()
    visualizer.print_detailed_comparison(results, tests_to_run, runs, warmup_runs, providers)

    # In CLI mode, we don't need to wait for input
    if not '--cli' in sys.argv:
        print("\nBenchmark finished. Press Enter to return to main menu...")
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
        self.providers = ["daytona", "e2b", "codesandbox", "modal", "local"]
        self.selected_providers = ["daytona"]  # Select all by default
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
                # Clean up the test function name to remove any wrapper prefix
                test_name = test_func.__name__
                if "test_wrapper" in test_name:
                    # If the name contains "test_wrapper", just use the actual function name
                    test_name = test_name.split(".")[-1]
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

        # Add toggle all option
        y = 7
        status = "[A] Toggle All Providers"
        attr = curses.A_NORMAL

        if self.menu_cursor == 0:
            attr |= curses.A_BOLD
            self.stdscr.addstr(y, 5, "→ ", attr)
        else:
            self.stdscr.addstr(y, 5, "  ")

        self.stdscr.addstr(y, 7, status, attr)

        # Display separator
        self.stdscr.addstr(y + 1, 7, "─" * 30)

        # Display individual providers
        for i, provider in enumerate(self.providers):
            y = 9 + i
            status = "[✓]" if provider in self.selected_providers else "[ ]"
            attr = curses.A_NORMAL

            if i + 1 == self.menu_cursor:  # +1 because we added the toggle all option
                attr |= curses.A_BOLD
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

        # Add toggle all option
        y = 7
        status = "[A] Toggle All Tests"
        attr = curses.A_NORMAL

        if self.menu_cursor == 0 and self.scroll_offset == 0:
            attr |= curses.A_BOLD
            self.stdscr.addstr(y, 5, "→ ", attr)
        else:
            self.stdscr.addstr(y, 5, "  ")

        self.stdscr.addstr(y, 7, status, attr)

        # Display separator
        self.stdscr.addstr(y + 1, 7, "─" * 30)

        # Adjust offset and menu cursor for the toggle all option
        display_offset = self.scroll_offset
        if display_offset == 0:
            # First item in the list is "Toggle All"
            visible_items = min(self.height - 14, len(defined_tests))
            test_display_start = 9  # Start displaying tests after the toggle all option
        else:
            # "Toggle All" option is scrolled out of view
            visible_items = min(self.height - 12, len(defined_tests) - display_offset)
            test_display_start = 7

        # Show scroll indicators if needed
        if display_offset > 0:
            self.stdscr.addstr(6, self.width // 2, "↑ (more tests above)")
        if display_offset + visible_items < len(defined_tests):
            self.stdscr.addstr(test_display_start + visible_items, self.width // 2, "↓ (more tests below)")

        for i, (test_id, test_func) in enumerate(list(defined_tests.items())[display_offset:display_offset+visible_items]):
            y = test_display_start + i
            is_single_run = hasattr(test_func, 'single_run') and test_func.single_run
            single_run_info = " (single run)" if is_single_run else ""
            status = "[✓]" if test_id in self.selected_tests else "[ ]"
            attr = curses.A_NORMAL

            # Adjust menu cursor positioning for the toggle all option
            cursor_pos = i + display_offset
            if display_offset == 0:
                cursor_pos += 1  # Shift by 1 for the "Toggle All" option

            if cursor_pos == self.menu_cursor:
                attr |= curses.A_BOLD  # Only use bold for selected item
                self.stdscr.addstr(y, 5, "→ ", attr)
            else:
                self.stdscr.addstr(y, 5, "  ")

            # Use bold for selected tests instead of colors to ensure readability
            if test_id in self.selected_tests:
                attr |= curses.A_BOLD

            # Clean up the test function name to remove any wrapper prefix
            func_name = test_func.__name__
            if "test_wrapper" in func_name:
                # If the name contains "test_wrapper", just use the actual function name
                func_name = func_name.split(".")[-1]
            test_name = f"{test_id}. {status} {func_name}{single_run_info}"
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

    def handle_main_menu_input_sync(self, key):
        """Handle keyboard input on the main menu (synchronous version)."""
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
            # Note: Benchmark logic (menu_cursor == 0) is handled in run_with_curses
            if self.menu_cursor == 1:  # Configure providers
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

    async def handle_main_menu_input(self, key):
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
                    # Temporarily exit curses mode to run benchmark
                    self.stdscr.clear()
                    curses.endwin()
                    # Run benchmark in plain terminal mode
                    run_plain_benchmark(self.selected_tests, self.selected_providers, self.runs, self.warmup_runs, self.region)
                    # Reset curses and return to main menu
                    self.stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.curs_set(0)  # Hide cursor
                    self.stdscr.timeout(100)  # For handling resize events
                    self.stdscr.keypad(True)  # Enable keypad mode
                    self.update_dimensions()
                    self.set_status("Benchmark completed", "success")
                    return True
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
                # Temporarily exit curses mode to run benchmark
                self.stdscr.clear()
                curses.endwin()
                # Run benchmark in plain terminal mode
                run_plain_benchmark(self.selected_tests, self.selected_providers, self.runs, self.warmup_runs, self.region)
                # Reset curses and return to main menu
                self.stdscr = curses.initscr()
                curses.start_color()
                curses.use_default_colors()
                curses.curs_set(0)  # Hide cursor
                self.stdscr.timeout(100)  # For handling resize events
                self.stdscr.keypad(True)  # Enable keypad mode
                self.update_dimensions()
                self.set_status("Benchmark completed", "success")
                return True
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
            self.menu_cursor = min(len(self.providers), self.menu_cursor + 1)  # +1 for toggle all option
        elif key == ord(' '):  # Space to toggle
            if self.menu_cursor == 0:  # Toggle All option
                if len(self.selected_providers) == len(self.providers):
                    # All are selected, so deselect all
                    self.selected_providers = []
                    self.set_status("All providers deselected", "info")
                else:
                    # Not all are selected, so select all
                    self.selected_providers = self.providers.copy()
                    self.set_status("All providers selected", "success")
            else:
                # Regular provider toggle (adjusted index for the toggle all option)
                provider = self.providers[self.menu_cursor - 1]
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
        elif key in (ord('a'), ord('A')):  # A key as a shortcut to toggle all
            if len(self.selected_providers) == len(self.providers):
                # All are selected, so deselect all
                self.selected_providers = []
                self.set_status("All providers deselected", "info")
            else:
                # Not all are selected, so select all
                self.selected_providers = self.providers.copy()
                self.set_status("All providers selected", "success")
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
            test_count = len(defined_tests)
            # Add offset for the toggle all option when scroll_offset is 0
            max_cursor = test_count if self.scroll_offset > 0 else test_count
            if self.menu_cursor < max_cursor:
                self.menu_cursor += 1

                # If we're past the toggle all option, adjust scrolling
                if self.scroll_offset == 0 and self.menu_cursor > 1:
                    visible_height = min(self.height - 14, test_count)
                    if self.menu_cursor - 1 >= visible_height:  # -1 to adjust for toggle all
                        self.scroll_offset = self.menu_cursor - visible_height
                elif self.scroll_offset > 0:
                    visible_height = min(self.height - 12, test_count - self.scroll_offset)
                    if self.menu_cursor >= self.scroll_offset + visible_height:
                        self.scroll_offset = self.menu_cursor - visible_height + 1
        elif key == ord(' '):  # Space to toggle
            if self.menu_cursor == 0 and self.scroll_offset == 0:  # Toggle All option
                if len(self.selected_tests) == len(defined_tests):
                    # All are selected, so deselect all
                    self.selected_tests = []
                    self.set_status("All tests deselected", "info")
                else:
                    # Not all are selected, so select all
                    self.selected_tests = list(defined_tests.keys())
                    self.set_status("All tests selected", "success")
            else:
                # Regular test toggle, adjusting for toggle all option
                if self.scroll_offset == 0:
                    test_index = self.menu_cursor - 1  # Adjust for toggle all option
                else:
                    test_index = self.menu_cursor

                test_id = list(defined_tests.keys())[test_index]
                if test_id in self.selected_tests:
                    self.selected_tests.remove(test_id)
                    self.set_status(f"Test {test_id} deselected", "info")
                else:
                    self.selected_tests.append(test_id)
                    self.set_status(f"Test {test_id} selected", "success")
        elif key in (ord('a'), ord('A')):  # A key as a shortcut to toggle all
            if len(self.selected_tests) == len(defined_tests):
                # All are selected, so deselect all
                self.selected_tests = []
                self.set_status("All tests deselected", "info")
            else:
                # Not all are selected, so select all
                self.selected_tests = list(defined_tests.keys())
                self.set_status("All tests selected", "success")
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

    # The run_benchmark function is now handled directly in the synchronous run_with_curses function

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

            # # Get example output
            # first_run_results = test_results.get("run_1", {})
            # first_provider_output = None
            # for provider in self.selected_providers:
            #     if provider in first_run_results and 'output' in first_run_results[provider]:
            #         first_provider_output = first_run_results[provider]['output']
            #         break

            # if first_provider_output:
            #     self.results_content.append(("Example Output:", curses.A_BOLD))
            #     for line in first_provider_output.split('\n')[:5]:  # Show first 5 lines
            #         self.results_content.append((line, curses.A_NORMAL))
            #     if first_provider_output.count('\n') > 5:
            #         self.results_content.append(("... (output truncated)", curses.A_NORMAL))
            #     self.results_content.append(("", curses.A_NORMAL))

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

    # The main_loop is now handled in the synchronous run_with_curses function


def run_tui():
    """Simple wrapper function to run the TUI with fallback to CLI mode."""
    try:
        # Use a simple wrapper to handle curses setup/teardown
        curses.wrapper(run_with_curses)
    except KeyboardInterrupt:
        print("Benchmark interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print("\n===================================")
        print("ERROR: Could not initialize TUI interface")
        print(f"Reason: {str(e)}")
        print("===================================")
        print("Falling back to CLI mode with default settings...")
        print("To manually specify settings, use command line arguments like:")
        print("  python benchmark.py --tests 1,2 --providers daytona --runs 3")
        print("For more options, run: python benchmark.py --help")
        print("===================================\n")

        # Get default args
        args = parse_args()
        providers_list = args.providers.split(',')
        test_ids = list(defined_tests.keys()) if args.tests == "all" else [int(tid) for tid in args.tests.split(',')]

        # Confirm to the user what we're about to do
        print(f"Running with providers: {', '.join(providers_list)}")
        print(f"Tests: {len(test_ids)} tests selected")
        print(f"Runs: {args.runs} (with {args.warmup_runs} warmup runs)")
        print(f"Region: {args.target_region}\n")

        # Use the plain benchmark runner with default settings
        run_plain_benchmark(
            test_ids,
            providers_list,
            args.runs,
            args.warmup_runs,
            args.target_region
        )

def run_with_curses(stdscr):
    """Run the TUI with a curses screen."""
    # Initialize curses
    curses.curs_set(0)  # Hide cursor
    curses.use_default_colors()  # Allow default colors
    stdscr.clear()

    # Create the TUI
    tui = BenchmarkTUI(stdscr)

    # Convert the async main_loop to a synchronous version
    # since curses and asyncio don't play well together
    running = True
    while running:
        tui.render()
        try:
            # Check for timeout to allow processing
            tui.stdscr.timeout(100)
            key = tui.stdscr.getch()

            # Handle no key
            if key == -1:
                continue

            # Handle window resize event
            if key == curses.KEY_RESIZE:
                tui.update_dimensions()
                continue

            # Handle view-specific inputs synchronously
            if tui.current_view == "main":
                # For the main menu, we need to handle the special case
                # to run benchmarks synchronously
                if key in (curses.KEY_ENTER, 10, 13) and tui.menu_cursor == 0 or key in (ord('r'), ord('R')):
                    # Run benchmark logic
                    if not tui.selected_tests:
                        tui.set_status("Please select at least one test to run.", "error")
                    elif not tui.selected_providers:
                        tui.set_status("Please select at least one provider.", "error")
                    elif 'codesandbox' in tui.selected_providers and not tui.check_codesandbox_service():
                        tui.set_status("CodeSandbox service not detected. Run 'node providers/codesandbox-service.js' first!", "warn")
                        # Give user time to read the warning
                        tui.stdscr.refresh()
                        time.sleep(1.5)
                    else:
                        tui.set_status("Starting benchmark...", "info")
                        # Temporarily exit curses mode to run benchmark
                        tui.stdscr.clear()
                        curses.endwin()
                        # Run benchmark in plain terminal mode
                        run_plain_benchmark(tui.selected_tests, tui.selected_providers, tui.runs, tui.warmup_runs, tui.region)
                        # Reset curses and return to main menu
                        tui.stdscr = curses.initscr()
                        curses.start_color()
                        curses.use_default_colors()
                        curses.curs_set(0)  # Hide cursor
                        tui.stdscr.timeout(100)  # For handling resize events
                        tui.stdscr.keypad(True)  # Enable keypad mode
                        tui.update_dimensions()
                        tui.set_status("Benchmark completed", "success")
                else:
                    # Otherwise handle normal input
                    running = tui.handle_main_menu_input_sync(key)
            elif tui.current_view == "providers":
                running = tui.handle_providers_menu_input(key)
            elif tui.current_view == "tests":
                running = tui.handle_tests_menu_input(key)
            elif tui.current_view == "config":
                running = tui.handle_config_menu_input(key)
            elif tui.current_view == "results":
                running = tui.handle_results_view_input(key)

        except Exception as e:
            # Handle the exception properly
            tui.set_status(f"Error: {str(e)}", "error")
            # Add proper error logging
            import logging
            logging.error(f"Error in main_loop: {str(e)}", exc_info=True)

def parse_args():
    """Parse command line arguments for direct CLI usage."""
    parser = argparse.ArgumentParser(description="AI Sandbox Benchmark Suite")
    parser.add_argument('--cli', action='store_true',
                      help='Run in command-line mode instead of TUI')
    parser.add_argument('--tests', '-t', type=str, default='all',
                      help='Comma-separated list of test IDs to run (or "all" for all tests)')
    parser.add_argument('--providers', '-p', type=str, default='daytona,e2b,codesandbox,modal,local',
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

    if args.cli or any([
        args.tests != 'all',
        args.providers != 'daytona,e2b,codesandbox,modal,local',
        args.runs != 1,
        args.warmup_runs != 0,
        args.target_region != 'eu'
    ]):
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