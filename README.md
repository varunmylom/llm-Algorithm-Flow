# LLM Consortium Plugin

A plugin for the `llm` package that enables managing a consortium of language models with arbitration capabilities. This plugin allows you to:

- Send prompts to multiple language models simultaneously
- Collect and evaluate responses based on confidence levels
- Use an arbiter model to select or synthesize the best response
- Track interaction history and model performance

## Installation

```bash
pip install llm-consortium
```

## Usage

```bash
llm -m consortium "Your prompt" --model gpt-4 --model claude-3 --arbiter-model claude-3-sonnet-20240307
```

Or programmatically:

```python
import llm
from llm.plugins.consortium import ConsortiumPlugin

consortium = ConsortiumPlugin()
result = await consortium.run_consortium(
    prompt="Your prompt",
    models=["gpt-4", "claude-3"],
    arbiter_model="claude-3-sonnet-20240307",
    confidence_threshold=0.9,
    max_iterations=2
)
print(result.response)
```

## Features

- Asynchronous model execution
- Confidence-based response selection
- Automatic arbitration for low-confidence responses
- CSV-based interaction logging
- Configurable confidence thresholds and iteration limits

## License

MIT License
