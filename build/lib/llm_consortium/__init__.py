import click
import json
import llm
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import sys
import re
import os
import pathlib
import sqlite_utils
from pydantic import BaseModel
import time  # added import for time
import concurrent.futures  # Add concurrent.futures for parallel processing
import threading  # Add threading for thread-local storage

# Todo:
# "finish_reason": "length"
# "finish_reason": "max_tokens"
# "stop_reason": "max_tokens",
# "finishReason": "MAX_TOKENS"
# "finishReason": "length"
# response.response_json
# Todo: setup continuation models: claude, deepseek etc.

# Read system prompt from file
def _read_system_prompt() -> str:
    try:
        file_path = pathlib.Path(__file__).parent / "system_prompt.txt"
        with open(file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading system prompt file: {e}")
        return ""

def _read_arbiter_prompt() -> str:
    try:
        file_path = pathlib.Path(__file__).parent / "arbiter_prompt.xml"
        with open(file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading arbiter prompt file: {e}")
        return ""

def _read_iteration_prompt() -> str:
    try:
        file_path = pathlib.Path(__file__).parent / "iteration_prompt.txt"
        with open(file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading iteration prompt file: {e}")
        return ""

DEFAULT_SYSTEM_PROMPT = _read_system_prompt()

def user_dir() -> pathlib.Path:
    """Get or create user directory for storing application data."""
    llm_user_path = os.environ.get("LLM_USER_PATH")
    if llm_user_path:
        path = pathlib.Path(llm_user_path)
    else:
        path = pathlib.Path(click.get_app_dir("io.datasette.llm"))
    path.mkdir(exist_ok=True, parents=True)
    return path

def logs_db_path() -> pathlib.Path:
    """Get path to logs database."""
    return user_dir() / "logs.db"

def setup_logging() -> None:
    """Configure logging to write to both file and console."""
    log_path = user_dir() / "consortium.log"

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler with ERROR level
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(str(log_path))
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.ERROR)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

# Replace existing logging setup with new setup
setup_logging()
logger = logging.getLogger(__name__)
logger.debug("llm_karpathy_consortium module is being imported")

class DatabaseConnection:
    _thread_local = threading.local()

    @classmethod
    def get_connection(cls) -> sqlite_utils.Database:
        """Get thread-local database connection to ensure thread safety."""
        if not hasattr(cls._thread_local, 'db'):
            cls._thread_local.db = sqlite_utils.Database(logs_db_path())
        return cls._thread_local.db

def _get_finish_reason(response_json: Dict[str, Any]) -> Optional[str]:
    """Helper function to extract finish reason from various API response formats."""
    if not isinstance(response_json, dict):
        return None
    # List of possible keys for finish reason (case-insensitive)
    reason_keys = ['finish_reason', 'finishReason', 'stop_reason']

    # Convert response to lowercase for case-insensitive matching
    lower_response = {k.lower(): v for k, v in response_json.items()}

    # Check each possible key
    for key in reason_keys:
        value = lower_response.get(key.lower())
        if value:
            return str(value).lower()

    return None

def log_response(response, model):
    """Log model response to database and log file."""
    try:
        db = DatabaseConnection.get_connection()
        response.log_to_db(db)
        logger.debug(f"Response from {model} logged to database")

        # Check for truncation in various formats
        if response.response_json:
            finish_reason = _get_finish_reason(response.response_json)
            truncation_indicators = ['length', 'max_tokens', 'max_token']

            if finish_reason and any(indicator in finish_reason for indicator in truncation_indicators):
                logger.warning(f"Response from {model} truncated. Reason: {finish_reason}")

    except Exception as e:
        logger.error(f"Error logging to database: {e}")

class IterationContext:
    def __init__(self, synthesis: Dict[str, Any], model_responses: List[Dict[str, Any]]):
        self.synthesis = synthesis
        self.model_responses = model_responses

class ConsortiumConfig(BaseModel):
    models: Dict[str, int]  # Maps model names to instance counts
    system_prompt: Optional[str] = None
    confidence_threshold: float = 0.8
    max_iterations: int = 3
    minimum_iterations: int = 1
    arbiter: Optional[str] = None

    def to_dict(self):
        return self.model_dump()

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class ConsortiumOrchestrator:
    def __init__(self, config: ConsortiumConfig):
        self.models = config.models
        # Retain system_prompt from config for backwards compatibility, but do not pass it separately.
        self.system_prompt = config.system_prompt  
        self.confidence_threshold = config.confidence_threshold
        self.max_iterations = config.max_iterations
        self.minimum_iterations = config.minimum_iterations
        self.arbiter = config.arbiter or "claude-3-opus-20240229"
        self.iteration_history: List[IterationContext] = []
        # New: Dictionary to track conversation IDs for each model instance
        self.conversation_ids: Dict[str, str] = {}

    def orchestrate(self, prompt: str) -> Dict[str, Any]:
        iteration_count = 0
        final_result = None
        original_prompt = prompt
        # Incorporate system instructions into the user prompt if available.
        if self.system_prompt:
            combined_prompt = f"[SYSTEM INSTRUCTIONS]\n{self.system_prompt}\n[/SYSTEM INSTRUCTIONS]\n\n{original_prompt}"
        else:
            combined_prompt = original_prompt

        current_prompt = f"""<prompt>
    <instruction>{combined_prompt}</instruction>
</prompt>"""

        while iteration_count < self.max_iterations or iteration_count < self.minimum_iterations:
            iteration_count += 1
            logger.debug(f"Starting iteration {iteration_count}")

            # Get responses from all models using the current prompt
            model_responses = self._get_model_responses(current_prompt)

            # Have arbiter synthesize and evaluate responses
            synthesis = self._synthesize_responses(original_prompt, model_responses)

            # Store iteration context
            self.iteration_history.append(IterationContext(synthesis, model_responses))

            if synthesis["confidence"] >= self.confidence_threshold and iteration_count >= self.minimum_iterations:
                final_result = synthesis
                break

            # Prepare for next iteration if needed
            current_prompt = self._construct_iteration_prompt(original_prompt, synthesis)

        if final_result is None:
            final_result = synthesis

        return {
            "original_prompt": original_prompt,
            "model_responses": model_responses,
            "synthesis": final_result,
            "metadata": {
                "models_used": self.models,
                "arbiter": self.arbiter,
                "timestamp": datetime.utcnow().isoformat(),
                "iteration_count": iteration_count
            }
        }

    def _get_model_responses(self, prompt: str) -> List[Dict[str, Any]]:
        responses = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for model, count in self.models.items():
                for instance in range(count):
                    futures.append(
                        executor.submit(self._get_model_response, model, prompt, instance)
                    )
            
            # Gather all results as they complete
            for future in concurrent.futures.as_completed(futures):
                responses.append(future.result())
                
        return responses

    def _get_model_response(self, model: str, prompt: str, instance: int) -> Dict[str, Any]:
        logger.debug(f"Getting response from model: {model} instance {instance + 1}")
        attempts = 0
        max_retries = 3
        
        # Generate a unique key for this model instance
        instance_key = f"{model}-{instance}"
        
        while attempts < max_retries:
            try:
                xml_prompt = f"""<prompt>
    <instruction>{prompt}</instruction>
</prompt>"""
                
                # Check if we have an existing conversation for this model instance
                conversation_id = self.conversation_ids.get(instance_key)
                
                # If we have a conversation_id, continue that conversation
                if conversation_id:
                    response = llm.get_model(model).prompt(
                        xml_prompt,
                        conversation_id=conversation_id
                    )
                else:
                    # Start a new conversation
                    response = llm.get_model(model).prompt(xml_prompt)
                    # Store the conversation_id for future iterations
                    if hasattr(response, 'conversation_id') and response.conversation_id:
                        self.conversation_ids[instance_key] = response.conversation_id
                
                text = response.text()
                log_response(response, f"{model}-{instance + 1}")
                return {
                    "model": model,
                    "instance": instance + 1,
                    "response": text,
                    "confidence": self._extract_confidence(text),
                    "conversation_id": getattr(response, 'conversation_id', None)
                }
            except Exception as e:
                # Check if the error is a rate-limit error
                if "RateLimitError" in str(e):
                    attempts += 1
                    wait_time = 2 ** attempts  # exponential backoff
                    logger.warning(f"Rate limit encountered for {model}, retrying in {wait_time} seconds... (attempt {attempts})")
                    time.sleep(wait_time)
                else:
                    logger.exception(f"Error getting response from {model} instance {instance + 1}")
                    return {"model": model, "instance": instance + 1, "error": str(e)}
        return {"model": model, "instance": instance + 1, "error": "Rate limit exceeded after retries."}

    def _parse_confidence_value(self, text: str, default: float = 0.5) -> float:
        """Helper method to parse confidence values consistently."""
        # Try to find XML confidence tag, now handling multi-line and whitespace better
        xml_match = re.search(r"<confidence>\s*(0?\.\d+|1\.0|\d+)\s*</confidence>", text, re.IGNORECASE | re.DOTALL)
        if xml_match:
            try:
                value = float(xml_match.group(1).strip())
                return value / 100 if value > 1 else value
            except ValueError:
                pass

        # Fallback to plain text parsing
        for line in text.lower().split("\n"):
            if "confidence:" in line or "confidence level:" in line:
                try:
                    nums = re.findall(r"(\d*\.?\d+)%?", line)
                    if nums:
                        num = float(nums[0])
                        return num / 100 if num > 1 else num
                except (IndexError, ValueError):
                    pass

        return default

    def _extract_confidence(self, text: str) -> float:
        return self._parse_confidence_value(text)

    def _construct_iteration_prompt(self, original_prompt: str, last_synthesis: Dict[str, Any]) -> str:
        """Construct the prompt for the next iteration."""
        # Simplified prompt that doesn't need to include the full history
        # since the conversation context is maintained by the provider
        return f"""Refining response for original prompt:
{original_prompt}

Arbiter feedback from previous attempt:
{json.dumps(last_synthesis, indent=2)}

Please improve your response based on this feedback."""

    def _format_iteration_history(self) -> str:
        history = []
        for i, iteration in enumerate(self.iteration_history, start=1):
            model_responses = "\n".join(
                f"<model_response>{r['model']}: {r.get('response', 'Error')}</model_response>"
                for r in iteration.model_responses
            )

            history.append(f"""<iteration>
            <iteration_number>{i}</iteration_number>
            <model_responses>
                {model_responses}
            </model_responses>
            <synthesis>{iteration.synthesis['synthesis']}</synthesis>
            <confidence>{iteration.synthesis['confidence']}</confidence>
            <refinement_areas>
                {self._format_refinement_areas(iteration.synthesis['refinement_areas'])}
            </refinement_areas>
        </iteration>""")
        return "\n".join(history) if history else "<no_previous_iterations>No previous iterations available.</no_previous_iterations>"

    def _format_refinement_areas(self, areas: List[str]) -> str:
        return "\n                ".join(f"<area>{area}</area>" for area in areas)

    def _format_responses(self, responses: List[Dict[str, Any]]) -> str:
        formatted = []
        for r in responses:
            formatted.append(f"""<model_response>
            <model>{r['model']}</model>
            <instance>{r.get('instance', 1)}</instance>
            <confidence>{r.get('confidence', 'N/A')}</confidence>
            <response>{r.get('response', 'Error: ' + r.get('error', 'Unknown error'))}</response>
        </model_response>""")
        return "\n".join(formatted)

    def _synthesize_responses(self, original_prompt: str, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.debug("Synthesizing responses")
        arbiter = llm.get_model(self.arbiter)

        formatted_history = self._format_iteration_history()
        formatted_responses = self._format_responses(responses)

        # Load and format the arbiter prompt template
        arbiter_prompt_template = _read_arbiter_prompt()
        arbiter_prompt = arbiter_prompt_template.format(
            original_prompt=original_prompt,
            formatted_responses=formatted_responses,
            formatted_history=formatted_history
        )

        arbiter_response = arbiter.prompt(arbiter_prompt)
        log_response(arbiter_response, arbiter)

        # Print raw arbiter response
        # click.echo(arbiter_response.text())

        try:
            return self._parse_arbiter_response(arbiter_response.text())
        except Exception as e:
            logger.error(f"Error parsing arbiter response: {e}")
            return {
                "synthesis": arbiter_response.text(),
                "confidence": 0.5,
                "analysis": "Parsing failed - see raw response",
                "dissent": "",
                "needs_iteration": False,
                "refinement_areas": []
            }

    def _parse_arbiter_response(self, text: str, is_final_iteration: bool = False) -> Dict[str, Any]:
        """Parse arbiter response with special handling for final iteration."""
        sections = {
            "synthesis": r"<synthesis>([\s\S]*?)</synthesis>",
            "confidence": r"<confidence>\s*([\d.]+)\s*</confidence>",
            "analysis": r"<analysis>([\s\S]*?)</analysis>",
            "dissent": r"<dissent>([\s\S]*?)</dissent>",
            "needs_iteration": r"<needs_iteration>(true|false)</needs_iteration>",
            "refinement_areas": r"<refinement_areas>([\s\S]*?)</refinement_areas>"
        }

        result = {}
        for key, pattern in sections.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if key == "confidence":
                    try:
                        value = float(match.group(1).strip())
                        result[key] = value / 100 if value > 1 else value
                    except (ValueError, TypeError):
                        result[key] = 0.5
                elif key == "needs_iteration":
                    result[key] = match.group(1).lower() == "true"
                elif key == "refinement_areas":
                    result[key] = [area.strip() for area in match.group(1).split("\n") if area.strip()]
                else:
                    result[key] = match.group(1).strip()

        # For final iteration, extract clean text response
        if is_final_iteration:
            clean_text = result.get("synthesis", "")
            # Remove any remaining XML tags
            clean_text = re.sub(r"<[^>]+>", "", clean_text).strip()
            result["clean_text"] = clean_text

        return result

def parse_models(models: List[str], count: int) -> Dict[str, int]:
    """Parse models and counts from CLI arguments into a dictionary."""
    model_dict = {}
    
    for item in models:
        model_dict[item] = count
    
    return model_dict

def read_stdin_if_not_tty() -> Optional[str]:
    """Read from stdin if it's not a terminal."""
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return None

class ConsortiumModel(llm.Model):
    can_stream = False

    class Options(llm.Options):
        confidence_threshold: Optional[float] = None
        max_iterations: Optional[int] = None

    def __init__(self, model_id: str, config: ConsortiumConfig):
        self.model_id = model_id
        self.config = config
        self._orchestrator = None  # Lazy initialization

    def __str__(self):
        return f"Consortium Model: {self.model_id}"

    def get_orchestrator(self):
        if self._orchestrator is None:
            try:
                self._orchestrator = ConsortiumOrchestrator(self.config)
            except Exception as e:
                raise llm.ModelError(f"Failed to initialize consortium: {e}")
        return self._orchestrator

    def execute(self, prompt, stream, response, conversation):
        """Execute the consortium synchronously"""
        try:
            result = self.get_orchestrator().orchestrate(prompt.prompt)
            response.response_json = result
            return result["synthesis"]["synthesis"]

        except Exception as e:
            raise llm.ModelError(f"Consortium execution failed: {e}")

def _get_consortium_configs() -> Dict[str, ConsortiumConfig]:
    """Fetch saved consortium configurations from the database."""
    db = DatabaseConnection.get_connection()

    db.execute("""
        CREATE TABLE IF NOT EXISTS consortium_configs (
            name TEXT PRIMARY KEY,
            config TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    configs = {}
    for row in db["consortium_configs"].rows:
        config_name = row["name"]
        config_data = json.loads(row["config"])
        configs[config_name] = ConsortiumConfig.from_dict(config_data)
    return configs

def _save_consortium_config(name: str, config: ConsortiumConfig) -> None:
    """Save a consortium configuration to the database."""
    db = DatabaseConnection.get_connection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS consortium_configs (
            name TEXT PRIMARY KEY,
            config TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db["consortium_configs"].insert(
        {"name": name, "config": json.dumps(config.to_dict())}, replace=True
    )

from click_default_group import DefaultGroup

class DefaultToRunGroup(DefaultGroup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set 'run' as the default command
        self.default_cmd_name = 'run'
        self.ignore_unknown_options = True

    def get_command(self, ctx, cmd_name):
        # Try to get the command normally
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv
        # If command not found, check if it's an option for the default command
        if cmd_name.startswith('-'):
            return super().get_command(ctx, self.default_cmd_name)
        return None

    def resolve_command(self, ctx, args):
        # Handle the case where no command is provided
        if not args:
            args = [self.default_cmd_name]
        return super().resolve_command(ctx, args)

def create_consortium(
    models: list[str],
    confidence_threshold: float = 0.8,
    max_iterations: int = 3,
    min_iterations: int = 1,
    arbiter: Optional[str] = None,
    system_prompt: Optional[str] = None,
    default_count: int = 1,
    raw: bool = False,
) -> ConsortiumOrchestrator:
    """
    Create and return a ConsortiumOrchestrator with a simplified API.
    - models: list of model names. To specify instance counts, use the format "model:count".
    - system_prompt: if not provided, DEFAULT_SYSTEM_PROMPT is used.
    """
    model_dict = {}
    for m in models:
        model_dict[m] = default_count
    config = ConsortiumConfig(
        models=model_dict,
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        confidence_threshold=confidence_threshold,
        max_iterations=max_iterations,
        minimum_iterations=min_iterations,
        arbiter=arbiter,
        raw=raw,
    )
    return ConsortiumOrchestrator(config=config)

@llm.hookimpl
def register_commands(cli):
    @cli.group(cls=DefaultToRunGroup)
    @click.pass_context
    def consortium(ctx):
        """Commands for managing and running model consortiums"""
        pass

    @consortium.command(name="run")
    @click.argument("prompt", required=False)
    @click.option(
        "-m",
        "--model", "models",  # store values in 'models'
        multiple=True,
        help="Model to include in consortium (use format 'model -n count'; can specify multiple)",
        default=["claude-3-opus-20240229", "claude-3-sonnet-20240229", "gpt-4", "gemini-pro"],
    )
    @click.option(
        "-n",
        "--count",
        type=int,
        default=1,
        help="Number of instances (if count not specified per model)",
    )
    @click.option(
        "--arbiter",
        help="Model to use as arbiter",
        default="claude-3-opus-20240229"
    )
    @click.option(
        "--confidence-threshold",
        type=float,
        help="Minimum confidence threshold",
        default=0.8
    )
    @click.option(
        "--max-iterations",
        type=int,
        help="Maximum number of iteration rounds",
        default=3
    )
    @click.option(
        "--min-iterations",
        type=int,
        help="Minimum number of iterations to perform",
        default=1
    )
    @click.option(
        "--system",
        help="System prompt to use",
    )
    @click.option(
        "--output",
        type=click.Path(dir_okay=False, writable=True),
        help="Save full results to this JSON file",
    )
    @click.option(
        "--stdin/--no-stdin",
        default=True,
        help="Read additional input from stdin and append to prompt",
    )
    @click.option(
        "--raw",
        is_flag=True,
        default=False,
        help="Output raw response from arbiter model",
    )
    def run_command(prompt, models, count, arbiter, confidence_threshold, max_iterations,
                   min_iterations, system, output, stdin, raw):
        """Run prompt through a consortium of models and synthesize results."""
        # Parse models and counts
        try:
            model_dict = parse_models(models, count)
        except ValueError as e:
            raise click.ClickException(str(e))

        # If no prompt is provided, read from stdin
        if not prompt and stdin:
            prompt = read_stdin_if_not_tty()
            if not prompt:
                raise click.UsageError("No prompt provided and no input from stdin")

        # Convert percentage to decimal if needed
        if confidence_threshold > 1.0:
            confidence_threshold /= 100.0

        if stdin:
            stdin_content = read_stdin_if_not_tty()
            if stdin_content:
                prompt = f"{prompt}\n\n{stdin_content}"

        logger.info(f"Starting consortium with {len(model_dict)} models")
        logger.debug(f"Models: {', '.join(f'{k}:{v}' for k, v in model_dict.items())}")
        logger.debug(f"Arbiter model: {arbiter}")

        orchestrator = ConsortiumOrchestrator(
            config=ConsortiumConfig(
               models=model_dict,
               system_prompt=system,
               confidence_threshold=confidence_threshold,
               max_iterations=max_iterations,
               minimum_iterations=min_iterations,
               arbiter=arbiter,
            )
        )

        try:
            result = orchestrator.orchestrate(prompt)

            if output:
                with open(output, 'w') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Results saved to {output}")

            click.echo(result["synthesis"]["analysis"])
            click.echo(result["synthesis"]["dissent"])
            click.echo(result["synthesis"]["synthesis"])

            if raw:
                click.echo("\nIndividual model responses:")
                for response in result["model_responses"]:
                    click.echo(f"\nModel: {response['model']} (Instance {response.get('instance', 1)})")
                    click.echo(f"Confidence: {response.get('confidence', 'N/A')}")
                    click.echo(f"Response: {response.get('response', 'Error: ' + response.get('error', 'Unknown error'))}")

        except Exception as e:
            logger.exception("Error in consortium command")
            raise click.ClickException(str(e))

    # Register consortium management commands group
    @consortium.command(name="save")
    @click.argument("name")
    @click.option(
        "-m",
        "--model", "models",  # changed option name, storing in 'models'
        multiple=True,
        help="Model to include in consortium (use format 'model -n count')",
        required=True,
    )
    @click.option(
        "-n",
        "--count",
        type=int,
        default=1,
        help="Default number of instances (if count not specified per model)",
    )
    @click.option(
        "--arbiter",
        help="Model to use as arbiter",
        required=True
    )
    @click.option(
        "--confidence-threshold",
        type=float,
        help="Minimum confidence threshold",
        default=0.8
    )
    @click.option(
        "--max-iterations",
        type=int,
        help="Maximum number of iteration rounds",
        default=3
    )
    @click.option(
        "--min-iterations",
        type=int,
        help="Minimum number of iterations to perform",
        default=1
    )
    @click.option(
        "--system",
        help="System prompt to use",
    )
    def save_command(name, models, count, arbiter, confidence_threshold, max_iterations,
                     min_iterations, system):
        """Save a consortium configuration."""
        try:
            model_dict = parse_models(models, count)
        except ValueError as e:
            raise click.ClickException(str(e))

        config = ConsortiumConfig(
            models=model_dict,
            arbiter=arbiter,
            confidence_threshold=confidence_threshold,
            max_iterations=max_iterations,
            minimum_iterations=min_iterations,
            system_prompt=system,
        )
        _save_consortium_config(name, config)
        click.echo(f"Consortium configuration '{name}' saved.")

    @consortium.command(name="list")
    def list_command():
        """List all saved consortiums with their details."""
        db = DatabaseConnection.get_connection()

        db.execute("""
        CREATE TABLE IF NOT EXISTS consortium_configs (
            name TEXT PRIMARY KEY,
            config TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        consortiums = list(db["consortium_configs"].rows)
        if not consortiums:
            click.echo("No consortiums found.")
            return

        click.echo("Available consortiums:\n")
        for row in consortiums:
            try:
                config_data = json.loads(row['config'])
                config = ConsortiumConfig.from_dict(config_data)

                click.echo(f"Consortium: {row['name']}")
                click.echo(f"  Models: {', '.join(f'{k}:{v}' for k, v in config.models.items())}")
                click.echo(f"  Arbiter: {config.arbiter}")
                click.echo(f"  Confidence Threshold: {config.confidence_threshold}")
                click.echo(f"  Max Iterations: {config.max_iterations}")
                if config.system_prompt:
                    click.echo(f"  System Prompt: {config.system_prompt}")
                click.echo("")  # Empty line between consortiums
            except Exception as e:
                click.echo(f"Error loading consortium '{row['name']}']: {e}")

    @consortium.command(name="remove")
    @click.argument("name")
    def remove_command(name):
        """Remove a saved consortium."""
        db = DatabaseConnection.get_connection()
        db.execute("""
        CREATE TABLE IF NOT EXISTS consortium_configs (
            name TEXT PRIMARY KEY,
            config TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        try:
            db["consortium_configs"].delete(name)
            click.echo(f"Consortium '{name}' removed.")
        except sqlite_utils.db.NotFoundError:
            raise click.ClickException(f"Consortium with name '{name}' not found.")

@llm.hookimpl
def register_models(register):
    logger.debug("KarpathyConsortiumPlugin.register_commands called")
    try:
        for name, config in _get_consortium_configs().items():
            try:
                model = ConsortiumModel(name, config)
                register(model, aliases=(name,))
            except Exception as e:
                logger.error(f"Failed to register consortium '{name}': {e}")
    except Exception as e:
        logger.error(f"Failed to load consortium configurations: {e}")

class KarpathyConsortiumPlugin:
    @staticmethod
    @llm.hookimpl
    def register_commands(cli):
        logger.debug("KarpathyConsortiumPlugin.register_commands called")

logger.debug("llm_karpathy_consortium module finished loading")

__all__ = ['KarpathyConsortiumPlugin', 'log_response', 'DatabaseConnection', 'logs_db_path', 'user_dir', 'ConsortiumModel']

__version__ = "0.3.1"