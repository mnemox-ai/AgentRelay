"""Tests for WorkerExecutor — all subprocess calls are mocked."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentrelay.worker.executor import (
    ExecutionStatus,
    ExecutorConfig,
    WorkerExecutor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_task_spec(
    task_type: str = "coding",
    input_data: dict | None = None,
    output_schema: dict | None = None,
) -> dict:
    return {
        "task_type": task_type,
        "input_data": input_data or {"instruction": "Write a hello world function"},
        "output_schema": output_schema or {
            "type": "object",
            "required": ["code"],
            "properties": {"code": {"type": "string"}},
        },
        "validation_method": "schema",
        "difficulty": "easy",
        "token_estimate": 1000,
    }


def _mock_process(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
    """Create a mock asyncio.Process."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_includes_instruction(self):
        executor = WorkerExecutor()
        spec = _sample_task_spec(input_data={"instruction": "Do something"})
        prompt = executor._build_prompt(spec)
        assert "Do something" in prompt

    def test_includes_input_data(self):
        executor = WorkerExecutor()
        spec = _sample_task_spec(input_data={"question": "What is 2+2?"})
        prompt = executor._build_prompt(spec)
        assert "What is 2+2?" in prompt

    def test_includes_output_schema(self):
        executor = WorkerExecutor()
        schema = {"type": "object", "required": ["answer"]}
        spec = _sample_task_spec(output_schema=schema)
        prompt = executor._build_prompt(spec)
        assert '"answer"' in prompt
        assert "JSON" in prompt

    def test_no_output_schema(self):
        executor = WorkerExecutor()
        spec = {"task_type": "coding", "input_data": {"x": 1}}
        prompt = executor._build_prompt(spec)
        assert "schema" not in prompt.lower() or "JSON output" in prompt

    def test_empty_input_data(self):
        executor = WorkerExecutor()
        spec = {"task_type": "coding", "input_data": {}}
        prompt = executor._build_prompt(spec)
        assert "coding" in prompt


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------

class TestBuildCommand:
    def test_basic_command(self):
        executor = WorkerExecutor()
        cmd = executor._build_command("hello")
        assert "claude" in cmd[0].lower()
        assert "-p" in cmd
        assert "hello" in cmd
        assert "--output-format" in cmd
        assert "text" in cmd

    def test_custom_claude_path(self):
        config = ExecutorConfig(claude_path="/usr/local/bin/claude")
        executor = WorkerExecutor(config)
        cmd = executor._build_command("hello")
        assert cmd[0] == "/usr/local/bin/claude"

    def test_with_model(self):
        config = ExecutorConfig(model="claude-haiku-4-5-20251001")
        executor = WorkerExecutor(config)
        cmd = executor._build_command("hello")
        assert "--model" in cmd
        assert "claude-haiku-4-5-20251001" in cmd

    def test_with_allowed_tools(self):
        config = ExecutorConfig(allowed_tools=["Bash", "Read"])
        executor = WorkerExecutor(config)
        cmd = executor._build_command("hello")
        assert "--allowedTools" in cmd
        assert "Bash,Read" in cmd

    def test_no_model_no_tools(self):
        executor = WorkerExecutor()
        cmd = executor._build_command("hello")
        assert "--model" not in cmd
        assert "--allowedTools" not in cmd


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

class TestParseOutput:
    def test_parse_plain_json(self):
        executor = WorkerExecutor()
        data = executor._parse_output('{"code": "print(42)"}')
        assert data == {"code": "print(42)"}

    def test_parse_json_code_block(self):
        executor = WorkerExecutor()
        raw = '```json\n{"code": "print(42)"}\n```'
        data = executor._parse_output(raw)
        assert data == {"code": "print(42)"}

    def test_parse_generic_code_block(self):
        executor = WorkerExecutor()
        raw = '```\n{"answer": 4}\n```'
        data = executor._parse_output(raw)
        assert data == {"answer": 4}

    def test_parse_invalid_json(self):
        executor = WorkerExecutor()
        data = executor._parse_output("This is not JSON at all")
        assert data is None

    def test_parse_empty_string(self):
        executor = WorkerExecutor()
        data = executor._parse_output("")
        assert data is None

    def test_parse_json_with_whitespace(self):
        executor = WorkerExecutor()
        data = executor._parse_output('  \n  {"x": 1}  \n  ')
        assert data == {"x": 1}


# ---------------------------------------------------------------------------
# Execute — success
# ---------------------------------------------------------------------------

class TestExecuteSuccess:
    @pytest.mark.asyncio
    async def test_success_with_json_output(self):
        executor = WorkerExecutor()
        spec = _sample_task_spec()
        output = json.dumps({"code": "def hello(): print('hi')"})

        proc = _mock_process(stdout=output.encode(), returncode=0)
        with patch("agentrelay.worker.executor.asyncio.create_subprocess_exec", return_value=proc):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.return_code == 0
        assert result.output_data == {"code": "def hello(): print('hi')"}
        assert result.error == ""
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_success_plain_text_output(self):
        executor = WorkerExecutor()
        spec = _sample_task_spec()

        proc = _mock_process(stdout=b"Just some text, not JSON", returncode=0)
        with patch("agentrelay.worker.executor.asyncio.create_subprocess_exec", return_value=proc):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.output_data is None
        assert "Just some text" in result.output

    @pytest.mark.asyncio
    async def test_success_with_stderr(self):
        executor = WorkerExecutor()
        spec = _sample_task_spec()
        output = json.dumps({"code": "x"})

        proc = _mock_process(stdout=output.encode(), stderr=b"warning: something", returncode=0)
        with patch("agentrelay.worker.executor.asyncio.create_subprocess_exec", return_value=proc):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.stderr == "warning: something"


# ---------------------------------------------------------------------------
# Execute — failure
# ---------------------------------------------------------------------------

class TestExecuteFailure:
    @pytest.mark.asyncio
    async def test_nonzero_exit_code(self):
        executor = WorkerExecutor()
        spec = _sample_task_spec()

        proc = _mock_process(stdout=b"", stderr=b"Error: rate limited", returncode=1)
        with patch("agentrelay.worker.executor.asyncio.create_subprocess_exec", return_value=proc):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.FAILED
        assert result.return_code == 1
        assert "rate limited" in result.stderr
        assert "code 1" in result.error

    @pytest.mark.asyncio
    async def test_claude_not_found(self):
        executor = WorkerExecutor(ExecutorConfig(claude_path="nonexistent-binary"))
        spec = _sample_task_spec()

        with patch(
            "agentrelay.worker.executor.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("No such file"),
        ):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.ERROR
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_os_error(self):
        executor = WorkerExecutor()
        spec = _sample_task_spec()

        with patch(
            "agentrelay.worker.executor.asyncio.create_subprocess_exec",
            side_effect=OSError("Permission denied"),
        ):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.ERROR
        assert "Permission denied" in result.error


# ---------------------------------------------------------------------------
# Execute — timeout
# ---------------------------------------------------------------------------

class TestExecuteTimeout:
    @pytest.mark.asyncio
    async def test_timeout(self):
        config = ExecutorConfig(timeout_seconds=1)
        executor = WorkerExecutor(config)
        spec = _sample_task_spec()

        proc = _mock_process()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch("agentrelay.worker.executor.asyncio.create_subprocess_exec", return_value=proc):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.TIMEOUT
        assert "timed out" in result.error
        proc.kill.assert_called_once()
        proc.wait.assert_called_once()


# ---------------------------------------------------------------------------
# ExecutorConfig defaults
# ---------------------------------------------------------------------------

class TestExecutorConfig:
    def test_defaults(self):
        config = ExecutorConfig()
        assert config.claude_path == "claude"
        assert config.timeout_seconds == 300
        assert config.max_output_bytes == 1_048_576
        assert config.allowed_tools == []
        assert config.model is None

    def test_custom_config(self):
        config = ExecutorConfig(
            claude_path="/opt/claude",
            timeout_seconds=60,
            max_output_bytes=512,
            allowed_tools=["Bash"],
            model="opus",
        )
        assert config.claude_path == "/opt/claude"
        assert config.timeout_seconds == 60
        assert config.model == "opus"


# ---------------------------------------------------------------------------
# Output truncation
# ---------------------------------------------------------------------------

class TestOutputTruncation:
    @pytest.mark.asyncio
    async def test_large_stdout_truncated(self):
        config = ExecutorConfig(max_output_bytes=32)
        executor = WorkerExecutor(config)
        spec = _sample_task_spec()

        large_output = b"x" * 1000
        proc = _mock_process(stdout=large_output, returncode=0)
        with patch("agentrelay.worker.executor.asyncio.create_subprocess_exec", return_value=proc):
            result = await executor.execute(spec)

        assert result.status == ExecutionStatus.SUCCESS
        assert len(result.output) == 32

    @pytest.mark.asyncio
    async def test_large_stderr_truncated(self):
        config = ExecutorConfig(max_output_bytes=16)
        executor = WorkerExecutor(config)
        spec = _sample_task_spec()

        proc = _mock_process(stdout=b"{}", stderr=b"e" * 500, returncode=0)
        with patch("agentrelay.worker.executor.asyncio.create_subprocess_exec", return_value=proc):
            result = await executor.execute(spec)

        assert len(result.stderr) == 16
