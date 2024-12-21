# llm-karpathy-consortium

[![PyPI](https://img.shields.io/pypi/v/llm-karpathy-consortium.svg)](https://pypi.org/project/llm-karpathy-consortium/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/yourusername/llm-karpathy-consortium/blob/main/LICENSE)

LLM plugin implementing Andrej Karpathy's model consortium concept - using multiple models to collectively reason about problems.

## Inspiration

Based on Karpathy's observation:

> "I find that recently I end up using *all* of the models and all the time. One aspect is the curiosity of who gets what, but the other is that for a lot of problems they have this "NP Complete" nature to them, where coming up with a solution is significantly harder than verifying a candidate solution. So your best performance will come from just asking all the models, and then getting them to come to a consensus."

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/):

```bash
llm install llm-karpathy-consortium
```

## Usage

Basic usage:

```bash
llm consortium "What are the key considerations for AGI safety?"
```

This will:
1. Send the prompt to multiple models in parallel
2. Have each model provide a response with reasoning and confidence
3. Use an arbiter model to synthesize the responses and identify key points of agreement/disagreement
4. Present a final synthesized response along with notable dissenting views

Advanced usage with custom models:

```bash
llm consortium "Complex question about quantum computing" \
  -m claude-3-opus-20240229 \
  -m gpt-4 \
  -m mistral-large \
  --arbiter-model claude-3-opus-20240229 \
  --confidence-threshold 0.9 \
  --max-iterations 5 \
  --output results.json
```

Options:

- `-m, --models`: Models to include in consortium (can specify multiple)
- `--arbiter-model`: Model to use for synthesizing responses 
- `--confidence-threshold`: Minimum confidence threshold (0-1)
- `--max-iterations`: Maximum number of iteration rounds
- `--system`: Custom system prompt
- `--output`: Save full results to JSON file

The full JSON output includes:
- Original prompt
- Individual model responses with reasoning
- Synthesized response and analysis
- Confidence scores
- Notable dissenting views
- Metadata about models used and iteration count

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

```bash
cd llm-karpathy-consortium
python -m venv venv
source venv/bin/activate
```

Now install the dependencies and test dependencies:

```bash
pip install -e '.[test]'
```

To run the tests:

```bash
pytest
```

## Contributing

Contributions to llm-karpathy-consortium are welcome! Please refer to the GitHub repository for more information on how to contribute.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.