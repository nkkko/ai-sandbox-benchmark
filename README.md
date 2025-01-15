# SDK Playground and Comparison

A comparative analysis toolkit for testing and benchmarking different code execution sandboxes, specifically Daytona and e2b.

## Overview

This project provides tools to:
- Generate code using LangChain and OpenAI
- Execute code in both Daytona and e2b sandboxes
- Compare performance metrics between different sandbox environments
- Visualize execution results and timing statistics

## Requirements

- Python 3.8+
- OpenAI API key
- Daytona API key and server URL
- e2b environment setup

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nkkko/sdk-play.git
cd sdk-play
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key
DAYTONA_API_KEY=your_daytona_api_key
DAYTONA_SERVER_URL=your_daytona_server_url
E2B_API_KEY=your_e2b_key
```

## Project Structure

- `comparison_stats.py` - Advanced statistical comparison between sandboxes
- `comparison.py` - Basic comparison between Daytona and e2b sandboxes
- `daytona_example.py` - Standalone Daytona sandbox example
- `e2b_example.py` - Standalone e2b sandbox example
- `requirements.txt` - Project dependencies

## Usage

### Basic Comparison
```bash
python comparison.py
```

### Detailed Statistical Analysis
```bash
python comparison_stats.py
```

### Individual Sandbox Testing
```bash
python daytona_example.py
python e2b_example.py
```

## Features

- Code generation using LangChain and OpenAI
- Sandbox execution timing metrics
- Colored console output
- Syntax highlighting for generated code
- Tabulated performance comparisons
- Statistical analysis of execution times
- Error handling and reporting

## Output Metrics

The comparison tools measure:
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
- LangChain
- OpenAI
