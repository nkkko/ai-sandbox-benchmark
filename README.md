# SDK Playground and Comparison

A comprehensive toolkit for testing and benchmarking different code execution sandboxes, including Daytona, e2b, CodeSandbox, and Modal.

## Overview

This project provides tools to:
- Generate code using LangChain and OpenAI
- Execute code in multiple sandbox environments:
  - Daytona
  - e2b
  - CodeSandbox
  - Modal
- Compare performance metrics between different sandbox environments
- Visualize execution results and timing statistics

## Requirements

- Python 3.8+
- Node.js (for CodeSandbox service)
- Required API keys:
  - OpenAI API key
  - Daytona API key and server URL
  - e2b environment setup
  - CodeSandbox API key
  - Modal setup

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nkkko/sdk-play.git
cd sdk-play
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies (for CodeSandbox service):
```bash
npm install
```

4. Create a `.env` file with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key
DAYTONA_API_KEY=your_daytona_api_key
DAYTONA_SERVER_URL=your_daytona_server_url
CSB_API_KEY=your_codesandbox_api_key
E2B_API_KEY=your_e2b_key
```

## Project Structure

- `comparison_4.py` - Latest version with Modal integration
- `comparison_3.py` - Previous version with CodeSandbox integration
- `comparison_stats.py` - Statistical analysis tools
- `comparison.py` - Basic comparison between sandboxes
- `daytona_example.py` - Standalone Daytona example
- `e2b_example.py` - Standalone e2b example
- `modaltest.py` - Modal sandbox testing
- `codesandbox-service.js` - CodeSandbox wrapper service

## Usage

### Running the CodeSandbox Service
Start the CodeSandbox wrapper service:
```bash
node codesandbox-service.js
```

### Running Comparisons
```bash
# Full comparison (all sandboxes)
python comparison_4.py

# Previous version (without Modal)
python comparison_3.py

# Basic comparison
python comparison.py
```

### Individual Sandbox Testing
```bash
python daytona_example.py
python e2b_example.py
python modaltest.py
```

## Features

- Code generation using LangChain and OpenAI
- Comprehensive sandbox execution timing metrics
- Colored console output
- Syntax highlighting for generated code
- Tabulated performance comparisons
- Statistical analysis of execution times
- Error handling and reporting
- Logging system

## Measured Metrics

For each sandbox environment, the following metrics are collected:
- Initialization time
- Workspace creation time
- Code execution time
- Cleanup time
- Total execution time
- Statistical variations (mean, standard deviation, min, max)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Apache 2.0

## Credits

- Daytona SDK
- e2b Code Interpreter
- CodeSandbox SDK
- Modal
- LangChain
- OpenAI