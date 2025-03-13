# AI Sandbox Benchmark

Welcome to **AI Sandbox Benchmark** – an open-source, standardized benchmarking framework designed to evaluate and compare various code execution sandbox environments like Daytona, e2b, CodeSandbox, Modal, and others.

Whether you're a developer looking to choose the best sandbox for your projects or a contributor aiming to enhance the benchmarking suite, this project is for you!

## 🚀 Get Involved

We invite developers, testers, and enthusiasts to contribute by adding new tests or integrating additional sandbox providers. Your contributions help make AI Sandbox Benchmark a comprehensive and reliable tool for the community.

**How to Contribute:**
- **Add New Tests:** Extend the test suite with new scenarios to evaluate sandbox performance.
- **Integrate Providers:** Connect additional sandbox environments to broaden the comparison scope.
- **Improve Documentation:** Help enhance the clarity and usability of the project guides.
- **Optimize Existing Tests:** Improve performance of current tests, like the improved prime calculation test.

Check out the [Contributing Guidelines](#contributing) below to get started!

## 📁 Project Structure

```
ai-sandbox-benchmark
├── SPECIFICATION.md
├── metrics.py
├── comparator.py
├── benchmark.py     # Terminal UI for benchmarking
├── migrate_tests.py # Test migration utility
├── test_rule.py
├── requirements.txt
├── providers
│   ├── daytona.py
│   ├── codesandbox.py
│   ├── __init__.py
│   ├── e2b.py
│   ├── modal.py
│   ├── local.py     # Local execution provider
│   ├── utils.py     # Provider utilities
│   └── codesandbox-service.js
├── tests
│   ├── MIGRATION_GUIDE.md
│   ├── README.md
│   ├── __init__.py
│   ├── test_list_directory.py
│   ├── test_calculate_primes.py
│   ├── test_llm_generated_primes.py
│   ├── test_resource_intensive_calculation.py
│   ├── test_container_stability.py
│   ├── test_database_operations.py
│   ├── test_fft_multiprocessing_performance.py
│   ├── test_fft_performance.py
│   ├── test_file_io_performance.py
│   ├── test_improved_calculate_primes.py
│   ├── test_optimized_example.py
│   ├── test_package_installation.py
│   ├── test_sandbox_utils.py
│   ├── test_startup_time.py
│   ├── test_system_info.py
│   ├── test_template.py
│   └── test_utils.py
└── README.md
```

## 🛠 Installation

### Prerequisites

- **Python 3.8+**
- **Node.js** (for CodeSandbox service)
- **Git**

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/nkkko/ai-sandbox-benchmark.git
   cd ai-sandbox-benchmark
   ```

2. **Set Up a Virtual Environment (Optional but Recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node.js Dependencies (for CodeSandbox Service)**

   Navigate to the `providers` directory and install dependencies:

   ```bash
   cd providers
   npm install
   cd ..
   ```

5. **Configure Environment Variables**

   Create a `.env` file in the root directory with the necessary API keys:

   ```env
   OPENAI_API_KEY=your_openai_api_key
   DAYTONA_API_KEY=your_daytona_api_key
   DAYTONA_SERVER_URL=your_daytona_server_url
   CSB_API_KEY=your_codesandbox_api_key
   ```

6. **Configure Sandbox Settings (Optional)**

   The `config.yml` file allows you to customize various aspects of the benchmark, including which environment variables are passed to sandbox environments:

   ```yaml
   # Environment variables to pass to sandboxes
   env_vars:
     pass_to_sandbox:
       - OPENAI_API_KEY
       # Add other variables as needed

   # Test configuration
   tests:
     warmup_runs: 1
     measurement_runs: 10

   # Provider-specific settings
   providers:
     daytona:
       default_region: eu
   ```

## 🏃 Usage

### Start the CodeSandbox Service

Before running benchmarks with CodeSandbox, ensure the CodeSandbox service is active:

```bash
node providers/codesandbox-service.js
```

### Available Tests

The benchmark includes the following tests:

1. **Calculate Primes** - Calculates the first 10 prime numbers, their sum and average
2. **Improved Calculate Primes** - Optimized version of the prime calculation test
3. **Resource Intensive Calculation** - Runs CPU, memory, and disk-intensive tasks to stress test the environment
4. **Package Installation** - Measures installation and import time for simple and complex Python packages
5. **File I/O Performance** - Benchmarks file operations with different file sizes and formats
6. **Startup Time** - Measures Python interpreter and library startup times
7. **LLM Generated Primes** - Generates code using an LLM to calculate prime numbers
8. **Database Operations** - Tests SQLite database performance for various operations
9. **Container Stability** - Measures stability under combined CPU, memory, and disk load
10. **List Directory** - Basic system command execution test using ls command
11. **System Info** - Gathers detailed system information about the environment
12. **FFT Performance** - Benchmarks Fast Fourier Transform computation speed
13. **FFT Multiprocessing Performance** - Tests FFT computation with parallel processing
14. **Optimized Example** - Demonstrates optimized code execution patterns
15. **Sandbox Utils** - Tests utility functions specific to sandbox environments
16. **Template** - Template for creating new tests

### Run Benchmarks

You can run benchmarks using either the command-line interface or the interactive Terminal UI.

#### 1. Terminal User Interface (Recommended)

The benchmark TUI provides an interactive way to select tests and providers:

```bash
python benchmark.py
```

Navigate the interface with:
- Arrow keys to move
- Space to toggle selections
- Enter to confirm/run
- 'q' to exit

#### 2. Command-Line Interface

Execute the comparator script directly for command-line benchmarking:

```bash
python comparator.py
```

To use the CLI mode with the TUI script:

```bash
python benchmark.py --cli
```

#### Available Options

- `--tests` or `-t`: Comma-separated list of test IDs to run (or `"all"`).
  **Default:** `all`

- `--providers` or `-p`: Comma-separated list of providers to test.
  **Default:** `daytona,e2b,codesandbox,modal,local`

- `--runs` or `-r`: Number of measurement runs per test/provider.
  **Default:** `10`

- `--warmup-runs` or `-w`: Number of warmup runs.
  **Default:** `1`

- `--target-region`: Target region (e.g., `eu`, `us`, `asia`).
  **Default:** `eu`

- `--show-history`: Show historical performance comparison.
  **Default:** Disabled (flag to enable)

- `--history-limit`: Number of previous runs to include in history.
  **Default:** `5`

- `--history-file`: Path to the benchmark history file.
  **Default:** `benchmark_history.json`

#### Examples

- **Run All Tests on All Providers**

  ```bash
  python comparator.py
  ```

- **Run Specific Tests on Selected Providers**

  ```bash
  python comparator.py --tests 1,3 --providers daytona,codesandbox
  ```

- **Run Tests on Local Machine Only**

  ```bash
  python comparator.py --providers local
  ```

- **Increase Measurement and Warmup Runs**

  ```bash
  python comparator.py --runs 20 --warmup-runs 2
  ```

- **View Historical Performance Trends**

  ```bash
  python comparator.py --tests 1 --show-history
  ```

- **Compare Recent Performance with History**

  ```bash
  python comparator.py --tests 1,2 --providers daytona,e2b --show-history --history-limit 10
  ```

- **Use Custom History File**

  ```bash
  python comparator.py --tests 1 --history-file custom_history.json --show-history
  ```

### Parallel Provider Testing

The benchmark suite now runs tests on all selected providers in parallel, significantly reducing overall benchmark time. Each test will be executed on all providers simultaneously, rather than waiting for each provider to finish before moving to the next one.

## 🖥️ Terminal UI

The benchmark tool includes a full-featured Terminal User Interface (TUI) that makes it easy to:
- Select specific tests to run
- Choose which providers to benchmark
- Configure runs and warmup settings
- View results in formatted tables

To launch the TUI:
```bash
python benchmark.py
```

## ✨ Features

- **Parallel Provider Execution**: Tests run simultaneously across all selected providers
- **Interactive TUI**: User-friendly terminal interface for selecting tests and providers
- **WCAG-Compliant Interface**: High-contrast, accessible terminal UI
- **Automated CodeSandbox Detection**: Warns if CodeSandbox service is not running
- **Flexible Test Configuration**: Run any combination of tests and providers
- **Comprehensive Metrics**: Detailed timing for workspace creation, execution, and cleanup
- **Statistical Analysis**: Mean, standard deviation, and relative performance comparisons
- **Warmup Runs**: Configurable warmup runs to ensure stable measurements

## 📈 Metrics & Performance Tracking

AI Sandbox Benchmark collects detailed performance metrics across providers and offers robust historical tracking:

### Core Metrics

- **Workspace Creation Time**: Time taken to initialize the sandbox environment
- **Code Execution Time**: Time to execute the test code
- **Cleanup Time**: Time required to tear down resources
- **Total Time**: Overall end-to-end performance

### Historical Performance Tracking

The benchmark suite now includes performance history tracking that:

- **Stores Results**: Automatically saves benchmark results to a history file
- **Tracks Trends**: Analyzes performance changes over time
- **Detects Changes**: Identifies improvements or regressions between runs
- **Compares Providers**: Shows relative performance across providers

### Advanced Analysis

- **Statistical Metrics**: Standard deviation, coefficient of variation, min/max values
- **Provider Comparisons**: Identifies fastest and most consistent providers
- **Reliability Tracking**: Tracks error rates and failures over time
- **Performance Trends**: Visualizes performance changes with percentage improvements

### Future Enhancements

- Comprehensive network performance metrics
- Graphical visualization of performance trends
- Automated regression detection and alerting

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

1. **Fork the Repository**

   Click the "Fork" button at the top right of the repository page to create your own fork.

2. **Clone Your Fork**

   ```bash
   git clone https://github.com/yourusername/sandbox-comparator.git
   cd sandbox-comparator
   ```

3. **Create a New Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Your Changes**

   - Add new tests in the `tests/` directory.
   - Integrate new providers in the `providers/` directory.
   - Update documentation as needed.

5. **Commit Your Changes**

   ```bash
   git commit -m "Add your descriptive commit message"
   ```

6. **Push to Your Fork**

   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open a Pull Request**

   Go to the original repository and create a pull request from your forked branch.

**Please ensure your contributions adhere to the existing code style and include relevant tests where applicable.**

## 📄 License

This project is licensed under the [Apache 2.0 License](LICENSE).

## 🙏 Credits

- **Sandbox Providers:**
  - [Daytona SDK](https://daytona.io/)
  - [e2b Code Interpreter](https://e2b.io/)
  - [CodeSandbox SDK](https://codesandbox.io/)
  - [Modal](https://modal.com/)
  - Local Provider (runs tests on the local machine)

- **Libraries and Tools:**
  - [LangChain](https://langchain.com/)
  - [OpenAI](https://openai.com/)
  - [NumPy](https://numpy.org/)
  - [Tabulate](https://github.com/astanin/python-tabulate)
  - [Curses](https://docs.python.org/3/library/curses.html) (Terminal UI)
  - [Dotenv](https://github.com/theskumar/python-dotenv)
  - [Termcolor](https://pypi.org/project/termcolor/)
  - [Requests](https://requests.readthedocs.io/)

---

*Join us in building a robust benchmarking tool for sandbox environments. Your participation makes a difference!*
