# Testing Skill — AI Bytes Pipeline

> pytest patterns for testing Python agents without hitting live APIs.

---

## Setup

```bash
pip install pytest pytest-mock pytest-cov
```

---

## Test Structure

```
tests/
├── conftest.py
├── test_script_agent.py
├── test_voice_agent.py
├── test_visual_agent.py
├── test_assembly_agent.py
├── test_publisher_agent.py
└── fixtures/
    ├── ep01_script.json     # sample script JSON
    └── ep01_voice.mp3       # short sample MP3
```

---

## conftest.py

```python
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_script() -> dict:
    import json
    return json.loads((FIXTURES / "ep01_script.json").read_text())

@pytest.fixture
def tmp_episode_dir(tmp_path):
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    return ep_dir
```

---

## Script Agent Test

```python
from unittest.mock import MagicMock, patch
from agents import script_agent

def test_run_returns_valid_json(tmp_episode_dir):
    mock_response = MagicMock()
    mock_response.content[0].text = '{"episode":"01","topic":"RAG","title":"T","hook":"H","concept":"C","slides":[],"voiceover":"V","takeaway":"T","tags":"#AI","youtube_title":"T #Shorts","youtube_description":"D","scheduled_publish":"2026-05-12T02:30:00Z"}'

    with patch("agents.script_agent.anthropic.Anthropic") as mock_client:
        mock_client.return_value.messages.create.return_value = mock_response
        result = script_agent.run(episode=1, week=1, input_data={"topic": "What is RAG?"})

    assert result["success"] is True
    assert Path(result["output_path"]).exists()

def test_run_retries_on_malformed_json(tmp_episode_dir):
    bad_response = MagicMock()
    bad_response.content[0].text = "not json"
    good_response = MagicMock()
    good_response.content[0].text = '{"episode":"01","topic":"RAG","title":"T","hook":"H","concept":"C","slides":[],"voiceover":"V","takeaway":"T","tags":"#AI","youtube_title":"T #Shorts","youtube_description":"D","scheduled_publish":"2026-05-12T02:30:00Z"}'

    with patch("agents.script_agent.anthropic.Anthropic") as mock_client:
        mock_client.return_value.messages.create.side_effect = [bad_response, good_response]
        result = script_agent.run(episode=1, week=1, input_data={"topic": "RAG"})

    assert result["success"] is True
```

---

## Voice Agent Test

```python
from unittest.mock import patch, MagicMock
from agents import voice_agent

def test_run_produces_mp3(tmp_path, sample_script):
    mock_audio = b"FAKE_MP3_BYTES"

    with patch("agents.voice_agent.ElevenLabs") as mock_el, \
         patch("agents.voice_agent.validate_mp3_duration", return_value=60.0):
        mock_el.return_value.generate.return_value = iter([mock_audio])
        result = voice_agent.run(episode=1, week=1, input_data=sample_script)

    assert result["success"] is True
```

---

## Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=agents --cov-report=term-missing

# Single agent
pytest tests/test_script_agent.py -v
```

---

## Best Practices for Agent Tests

- Always mock external API calls (Anthropic, ElevenLabs, YouTube, ffprobe)
- Use `tmp_path` fixture for output files — never write to `output/` in tests
- Test both success path AND retry/failure path for every agent
- Validate the output file exists and has the correct path format
- Keep fixtures minimal — a valid JSON dict is enough for script tests
