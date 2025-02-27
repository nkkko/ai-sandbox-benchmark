# AI Sandbox Benchmark

Welcome to **Sandbox Comparator** – an open-source, standardized benchmarking framework designed to evaluate and compare various code execution sandbox environments like Daytona, e2b, CodeSandbox, Modal, and others.

Whether you're a developer looking to choose the best sandbox for your projects or a contributor aiming to enhance the benchmarking suite, this project is for you!

## 🚀 Get Involved

We invite developers, testers, and enthusiasts to contribute by adding new tests or integrating additional sandbox providers. Your contributions help make Sandbox Comparator a comprehensive and reliable tool for the community.

**How to Contribute:**
- **Add New Tests:** Extend the test suite with new scenarios to evaluate sandbox performance.
- **Integrate Providers:** Connect additional sandbox environments to broaden the comparison scope.
- **Improve Documentation:** Help enhance the clarity and usability of the project guides.

Check out the [Contributing Guidelines](#contributing) below to get started!

## 📁 Project Structure

```
sandbox-comparator
├── SPECIFICATION.md
├── metrics.py
├── comparator.py
├── requirements.txt
├── providers
│   ├── daytona.py
│   ├── codesandbox.py
│   ├── __init__.py
│   ├── e2b.py
│   ├── modal.py
│   └── codesandbox-service.js
├── tests
│   ├── test_list_directory.py
│   ├── test_calculate_primes.py
│   ├── __init__.py
│   ├── test_llm_generated_primes.py
│   └── test_resource_intensive_calculation.py
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
   git clone https://github.com/nkkko/sandbox-comparator.git
   cd sandbox-comparator
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

## 🏃 Usage

### Start the CodeSandbox Service

Before running benchmarks, ensure the CodeSandbox service is active (currently no Python SDK):

```bash
cd providers
node codesandbox-service.js
```

### Run Benchmarks

Execute the comparator script to start benchmarking:

```bash
python comparator.py
```

#### Available Options

- `--tests` or `-t`: Comma-separated list of test IDs to run (or `"all"`).
  **Default:** `all`

- `--providers` or `-p`: Comma-separated list of providers to test.
  **Default:** `daytona,e2b,codesandbox,modal`

- `--runs` or `-r`: Number of measurement runs per test/provider.
  **Default:** `10`

- `--warmup-runs` or `-w`: Number of warmup runs.
  **Default:** `1`

- `--target-region`: Target region (e.g., `eu`, `us`, `asia`).
  **Default:** `eu`

#### Examples

- **Run All Tests on All Providers**

  ```bash
  python comparator.py
  ```

- **Run Specific Tests on Selected Providers**

  ```bash
  python comparator.py --tests 1,3 --providers daytona,codesandbox
  ```

- **Increase Measurement and Warmup Runs**

  ```bash
  python comparator.py --runs 20 --warmup-runs 2
  ```

## 📈 Metrics

Currently, Sandbox Comparator focuses on executing standardized tests across different sandbox providers and collecting basic performance metrics such as workspace creation time, code execution time, and cleanup time.

**Planned Enhancements:**
- Comprehensive network performance metrics
- Enhanced reliability tracking
- Advanced statistical analysis

Stay tuned for updates as we continue to expand the benchmarking capabilities!

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

- **Libraries and Tools:**
  - [LangChain](https://langchain.com/)
  - [OpenAI](https://openai.com/)
  - [NumPy](https://numpy.org/)
  - [Tabulate](https://github.com/astanin/python-tabulate)
  - [Dotenv](https://github.com/theskumar/python-dotenv)
  - [Termcolor](https://pypi.org/project/termcolor/)

---

*Join us in building a robust benchmarking tool for sandbox environments. Your participation makes a difference!*
