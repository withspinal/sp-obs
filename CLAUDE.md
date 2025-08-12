# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`sp-obs` is Spinal's cost tracking library built on top of OpenTelemetry. It works by adding isolated tracers to libraries that haven't been instrumented and attaching a processor to libraries that already have instrumentation. This dual approach allows it to integrate seamlessly with existing observability setups while selectively forwarding AI/LLM operations and billing events to Spinal's platform.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install in editable mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Code Quality
```bash
# Run linter (configured in ruff.toml)
ruff check src/

# Auto-fix linting issues
ruff check --fix src/

# Format code
ruff format src/

# Install pre-commit hooks (runs automatically on commit)
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files
```

### Building and Distribution
```bash
# Build the package (uses hatchling)
python -m build

# Upload to TestPyPI for testing
python -m twine upload --repository testpypi dist/*

# Upload to PyPI for release
python -m twine upload dist/*
```

## Architecture and Key Components

### Core Design Pattern
The library uses an **interceptor pattern** to attach to existing OpenTelemetry TracerProvider instances, avoiding the need for users to modify their existing observability setup.

### File Structure
- `src/sp_obs/provider.py`: Context management functions (`tag`, `add_context` - deprecated)
- `src/sp_obs/__init__.py`: Public API exports
- `src/sp_obs/_internal/processor.py`: SpinalSpanProcessor implementation
- `src/sp_obs/_internal/exporter.py`: SpinalSpanExporter (singleton with httpx session) and safe_decode utility
- `src/sp_obs/_internal/config.py`: Configuration management
- `src/sp_obs/_internal/providers/`: Provider-specific instrumentations (OpenAI, Anthropic, etc.)
- `tests/test_exporter/test_safe_decode.py`: Tests for encoding/decoding handling

### Key Classes

1. **SpinalConfig** (`_internal/config.py`): Configuration container
   - Environment variables: `SPINAL_TRACING_ENDPOINT`, `SPINAL_API_KEY`
   - Batch processing vars: `SPINAL_PROCESS_MAX_QUEUE_SIZE`, `SPINAL_PROCESS_SCHEDULE_DELAY`, etc.
   - Defaults: timeout=5s, max_queue_size=2048, batch_size=512
   - Includes scrubber support for sensitive data redaction

2. **SpinalSpanProcessor** (`_internal/processor.py`, extends BatchSpanProcessor):
   - Implements `_should_process()` with SpanType enum-based filtering
   - Filters: AI providers (OpenAI, Anthropic), HTTPX requests (excluding AI endpoints)
   - Captures baggage in `on_start()` to preserve context across thread boundaries
   - Uses `_batch_processor.emit()` to bypass sampling

3. **SpinalSpanExporter** (`_internal/exporter.py`, implements SpanExporter):
   - Singleton pattern with thread-safe initialization
   - Reuses httpx.Client session for efficiency
   - Converts spans to JSON with full attribute preservation
   - Applies configured scrubber before export
   - Includes `safe_decode()` utility for robust encoding handling (UTF-8 → Windows-1252 → Latin-1 fallback)

### Public API Functions

- `configure()`: Set up global configuration
- `tag()`: Context manager for adding workflow_id/user_id to baggage (replaces deprecated `add_context()`)
- `instrument_openai()`, `instrument_anthropic()`, etc.: Provider instrumentations
- `shutdown()`, `force_flush()`: Cleanup utilities
- Scrubber classes: `DefaultScrubber`, `NoOpScrubber`, `SpinalScrubber`

### Context Propagation

Uses OpenTelemetry baggage for distributed tracing:
- Baggage keys: `spinal.workflow_id`, `spinal.user_context.id`, `spinal.aggregation_id`
- Baggage captured in `on_start()` due to thread boundary between app and export threads
- Automatically propagates through HTTP headers (W3C format)
- Context manager pattern ensures proper attach/detach

## Important Considerations

1. **Thread Safety**: Baggage doesn't cross thread boundaries - captured in `on_start()` while context is available.

2. **Selective Processing**: Only forwards AI/LLM spans and HTTPX requests (excluding AI provider endpoints).

3. **Singleton Exporter**: SpinalSpanExporter uses singleton pattern to reuse HTTP connections.

4. **No Sampling**: Processor bypasses OTEL sampling by using `_batch_processor.emit()` directly.

5. **Python 3.11+**: Requires Python 3.11 or higher (per pyproject.toml).

6. **Batch Processing**: Default 5-second flush interval or 512-span batch size, whichever comes first.

7. **Encoding Handling**: The exporter includes robust encoding support via `safe_decode()`:
   - Primary: UTF-8 decoding (standard for modern APIs)
   - Fallback 1: Windows-1252 (handles Windows smart quotes, euro signs, etc.)
   - Fallback 2: Latin-1 with replacement characters (prevents crashes on any byte sequence)
   - This prevents UnicodeDecodeError exceptions when processing response data from various sources