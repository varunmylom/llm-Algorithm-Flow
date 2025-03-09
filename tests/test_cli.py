import json
import os
import tempfile
import pytest
from click.testing import CliRunner
import llm
import click
from llm_consortium import register_commands

# Create a dummy CLI group for testing
@click.group()
def cli():
    pass

register_commands(cli)

def dummy_orchestrate(prompt):
    return {
        "original_prompt": prompt,
        "model_responses": [],
        "synthesis": {"synthesis": "dummy response", "confidence": 1.0, "analysis": "none"},
        "metadata": {"models_used": {"dummy": 1}, "arbiter": "dummy", "timestamp": "now", "iteration_count": 1}
    }

class DummyResponse:
    def text(self):
        return "<synthesis>dummy response</synthesis><confidence>1.0</confidence><analysis>none</analysis>"
    @property
    def response_json(self):
        return {"finish_reason": "dummy"}
    def log_to_db(self, db):
        pass

class DummyModel:
    def prompt(self, xml_prompt):
        return DummyResponse()

def dummy_get_model(model_id):
    return DummyModel()

@pytest.fixture(autouse=True)
def patch_llm(monkeypatch):
    monkeypatch.setattr(llm, "get_model", dummy_get_model)
    from llm_consortium import ConsortiumOrchestrator
    monkeypatch.setattr(ConsortiumOrchestrator, "orchestrate", lambda self, prompt: dummy_orchestrate(prompt))

def test_run_command_min_iterations():
    runner = CliRunner()
    result = runner.invoke(cli, [
        "consortium", "run", "Test prompt",
        "--min-iterations", "2",
        "--models", "dummy:1",
        "--arbiter", "dummy",
    ])
    assert result.exit_code == 0
    assert "dummy response" in result.output

def test_save_command():
    runner = CliRunner()
    result = runner.invoke(cli, [
        "consortium", "save", "test-consortium",
        "--models", "dummy:1",
        "--arbiter", "dummy",
        "--confidence-threshold", "0.9",
        "--max-iterations", "3",
        "--min-iterations", "2"
    ])
    assert result.exit_code == 0
    assert "test-consortium" in result.output.lower()
