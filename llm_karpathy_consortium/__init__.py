import click
import json
import llm
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import sys
import re
import os
import pathlib
import sqlite_utils

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger(__name__)

logger.debug("llm_karpathy_consortium module is being imported")

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

class DatabaseConnection:
    _instance: Optional['DatabaseConnection'] = None
    
    def __init__(self):
        self.db = sqlite_utils.Database(logs_db_path())
    
    @classmethod
    def get_connection(cls) -> sqlite_utils.Database:
        """Get singleton database connection."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance.db

def log_response(response, model):
    """Log model response to database."""
    try:
        db = DatabaseConnection.get_connection()
        response.log_to_db(db)
    except Exception as e:
        print(f"Error logging to database: {e}")

class ConsortiumOrchestrator:
    def __init__(
        self,
        models: List[str],
        system_prompt: Optional[str] = None,
        confidence_threshold: float = 0.8,
        max_iterations: int = 3,
        arbiter_model: Optional[str] = None,
    ):
        self.models = models
        self.system_prompt = system_prompt or "You are part of a model consortium working together to solve problems. Be thorough in your reasoning and explain your confidence level (0-1) in your answer."
        self.confidence_threshold = confidence_threshold
        self.max_iterations = max_iterations
        self.arbiter_model = arbiter_model or "claude-3-opus-20240229"

    async def orchestrate(self, prompt: str) -> Dict[str, Any]:
        iteration_count = 0
        final_result = None

        while iteration_count < self.max_iterations:
            iteration_count += 1
            logger.debug(f"Starting iteration {iteration_count}")

            # Get responses from all models
            model_responses = await self._get_model_responses(prompt)

            # Have arbiter synthesize and evaluate responses
            synthesis = await self._synthesize_responses(prompt, model_responses)

            if synthesis["confidence"] >= self.confidence_threshold:
                final_result = synthesis
                break

            # Prepare for next iteration if needed
            prompt = f"Previous synthesis: {synthesis['synthesis']}\n\nAreas needing refinement: {', '.join(synthesis['refinement_areas'])}\n\nPlease provide an updated response addressing these refinement areas."

        if final_result is None:
            final_result = synthesis

        return {
            "original_prompt": prompt,
            "model_responses": model_responses,
            "synthesis": final_result,
            "metadata": {
                "models_used": self.models,
                "arbiter_model": self.arbiter_model,
                "timestamp": datetime.utcnow().isoformat(),
                "iteration_count": iteration_count
            }
        }

    async def _get_model_responses(self, prompt: str) -> List[Dict[str, Any]]:
        tasks = [self._get_model_response(model, prompt) for model in self.models]
        return await asyncio.gather(*tasks)

    async def _get_model_response(self, model: str, prompt: str) -> Dict[str, Any]:
        logger.debug(f"Getting response from model: {model}")
        try:
            response = llm.get_model(model).prompt(prompt, system=self.system_prompt)
            log_response(response, model)
            return {
                "model": model,
                "response": response.text(),
                "confidence": self._extract_confidence(response.text()),
            }
        except Exception as e:
            logger.exception(f"Error getting response from {model}")
            return {"model": model, "error": str(e)}

    async def _synthesize_responses(self, prompt: str, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.debug("Synthesizing responses")
        arbiter = llm.get_model(self.arbiter_model)
        arbiter_prompt = f"""Original prompt: {prompt}

Responses from the consortium:

{self._format_responses(responses)}

Please:
1. Analyze the different responses and their reasoning
2. Identify areas of agreement and disagreement
3. Synthesize a final response that represents the best consensus
4. Highlight any important dissenting views
5. Provide recommendations for further iterations if needed

Structure your response as follows:

Synthesis:
[Your synthesized response here]

Confidence: [Your confidence in this synthesis (0-1)]

Analysis:
[Your analysis of the responses]

Dissent:
[Notable dissenting views]

Needs Iteration: [true/false]

Refinement Areas:
[List of areas that need further refinement, if any]"""

        arbiter_response = arbiter.prompt(arbiter_prompt)
        log_response(arbiter_response, arbiter)

        try:
            return self._parse_arbiter_response(arbiter_response.text())
        except Exception as e:
            logger.exception("Error parsing arbiter response")
            return {
                "synthesis": arbiter_response.text(),
                "confidence": 0.5,
                "analysis": "Parsing failed - see raw response",
                "dissent": "",
                "needs_iteration": False,
                "refinement_areas": []
            }

    def _parse_arbiter_response(self, text: str) -> Dict[str, Any]:
        sections = {
            "synthesis": r"Synthesis:\n([\s\S]*?)(?:\n\n|$)",
            "confidence": r"Confidence:\s*(0?\.\d+|1\.0)",
            "analysis": r"Analysis:\n([\s\S]*?)(?:\n\n|$)",
            "dissent": r"Dissent:\n([\s\S]*?)(?:\n\n|$)",
            "needs_iteration": r"Needs Iteration:\s*(true|false)",
            "refinement_areas": r"Refinement Areas:\n([\s\S]*?)(?:\n\n|$)"
        }

        result = {}
        for key, pattern in sections.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if key == "confidence":
                    result[key] = float(match.group(1))
                elif key == "needs_iteration":
                    result[key] = match.group(1).lower() == "true"
                elif key == "refinement_areas":
                    result[key] = [area.strip() for area in match.group(1).split("\n") if area.strip()]
                else:
                    result[key] = match.group(1).strip()
            else:
                result[key] = "" if key != "confidence" else 0.5

        return result

    def _format_responses(self, responses: List[Dict[str, Any]]) -> str:
        formatted = []
        for r in responses:
            formatted.append(f"""Model: {r['model']}
Confidence: {r.get('confidence', 'N/A')}
Response: {r.get('response', 'Error: ' + r.get('error', 'Unknown error'))}
---""")
        return "\n\n".join(formatted)

    def _extract_confidence(self, text: str) -> float:
        # Simple heuristic to extract confidence from response
        for line in text.lower().split("\n"):
            if "confidence:" in line or "confidence level:" in line:
                try:
                    return float([x for x in line.split() if x.replace(".", "").isdigit()][0])
                except (IndexError, ValueError):
                    pass
        return 0.5  # Default confidence if not found

@llm.hookimpl
def register_commands(cli):
    @cli.command()
    @click.argument("prompt")
    @click.option(
        "-m",
        "--models",
        multiple=True,
        help="Models to include in consortium (can specify multiple)",
        default=[
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "gpt-4",
            "gemini-pro"
        ],
    )
    @click.option(
        "--arbiter-model",
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
        "--system",
        help="System prompt to use",
    )
    @click.option(
        "--output",
        type=click.Path(dir_okay=False, writable=True),
        help="Save full results to this JSON file",
    )
    def consortium(
        prompt: str,
        models: List[str],
        arbiter_model: str,
        confidence_threshold: float,
        max_iterations: int,
        system: Optional[str],
        output: Optional[str],
    ):
        """Run prompt through a consortium of models and synthesize results."""
        logger.debug("Consortium command called")
        orchestrator = ConsortiumOrchestrator(
            models=list(models),
            system_prompt=system,
            confidence_threshold=confidence_threshold,
            max_iterations=max_iterations,
            arbiter_model=arbiter_model,
        )
        
        try:
            result = asyncio.run(orchestrator.orchestrate(prompt))
            
            if output:
                with open(output, 'w') as f:
                    json.dump(result, f, indent=2)
            
            click.echo("\nSynthesized response:\n")
            click.echo(result["synthesis"]["synthesis"])
            
            click.echo(f"\nConfidence: {result['synthesis']['confidence']}")
            
            click.echo("\nAnalysis:")
            click.echo(result["synthesis"]["analysis"])
            
            if result["synthesis"]["dissent"]:
                click.echo("\nNotable dissenting views:")
                click.echo(result["synthesis"]["dissent"])
            
            click.echo(f"\nNumber of iterations: {result['metadata']['iteration_count']}")
            
            click.echo("\nIndividual model responses:")
            for response in result["model_responses"]:
                click.echo(f"\nModel: {response['model']}")
                click.echo(f"Confidence: {response.get('confidence', 'N/A')}")
                click.echo(f"Response: {response.get('response', 'Error: ' + response.get('error', 'Unknown error'))}")
                
        except Exception as e:
            logger.exception("Error in consortium command")
            raise click.ClickException(str(e))

class KarpathyConsortiumPlugin:
    @staticmethod
    @llm.hookimpl
    def register_commands(cli):
        logger.debug("KarpathyConsortiumPlugin.register_commands called")

logger.debug("llm_karpathy_consortium module finished loading")

# Ensure the KarpathyConsortiumPlugin is exported
__all__ = ['KarpathyConsortiumPlugin', 'log_response', 'DatabaseConnection', 'logs_db_path', 'user_dir']

__version__ = "0.1.0"
