"""Static contract checks for the isolated Whisper service boundary."""

import ast
from pathlib import Path

WHISPER_SERVER = Path(__file__).parents[2] / "docker" / "whisper" / "server.py"


def test_grading_endpoint_has_no_model_biasing_prompt():
    tree = ast.parse(WHISPER_SERVER.read_text(encoding="utf-8"))
    prompt_names = {
        node.arg
        for node in ast.walk(tree)
        if isinstance(node, ast.arg) and node.arg == "initial_prompt"
    }
    prompt_keywords = {
        node.arg
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword) and node.arg == "initial_prompt"
    }
    assert not prompt_names and not prompt_keywords
