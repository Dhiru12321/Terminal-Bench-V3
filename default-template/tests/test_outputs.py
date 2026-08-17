from pathlib import Path


def test_output_exists():
    """The agent must write hello to the output file."""
    assert Path("/app/output.txt").read_text().strip() == "hello"
