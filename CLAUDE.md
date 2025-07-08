# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`sp-obs` is an OpenTelemetry span interceptor that automatically attaches to existing TracerProvider instances to duplicate AI/LLM spans to custom endpoints for billing and monitoring. It works by intercepting spans from any OpenTelemetry-instrumented application and selectively forwarding AI/LLM operations, billable events, and user-contextualized spans.

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

# This creates:
# - dist/sp_obs-{version}-py3-none-any.whl
# - dist/sp_obs-{version}.tar.gz
```

## Architecture and Key Components

### Core Design Pattern
The library uses an **interceptor pattern** to attach to existing OpenTelemetry TracerProvider instances, avoiding the need for users to modify their existing observability setup.

### File Structure
- `src/sp_obs/provider.py`: All core implementation (SpinalConfig, SpinalSpanProcessor, SpinalSpanExporter)
- `src/sp_obs/__init__.py`: Public API exports and utility functions

### Key Classes

1. **SpinalConfig**: Configuration container
   - Environment variables: `SPINAL_TRACING_ENDPOINT`, `SPINAL_API_KEY`
   - Defaults: timeout=5s, batch_size=100
   - Supports custom headers for authentication

2. **SpinalSpanProcessor** (extends BatchSpanProcessor):
   - Implements `_should_process()` for selective filtering
   - Filters by: `gen_ai.system` attribute, billable events, user context
   - Overrides `on_end()` to intercept span completion
   - Automatically enriches spans with baggage context

3. **SpinalSpanExporter** (implements SpanExporter):
   - Converts OTEL spans to JSON format
   - HTTP POST with configurable timeout
   - Preserves all span attributes including baggage

### Public API Functions

- `spinal_attach()`: Auto-attaches to existing or new TracerProvider
- `spinal_add_context()`: Adds workflow_id and user_id to baggage
- `spinal_add_as_billable()`: Creates billable event spans
- `configure_for_openai_agents()`: Logfire + OpenAI helper

### Context Propagation

Uses OpenTelemetry baggage for distributed tracing:
- Baggage keys: `workflow_id`, `user`
- Automatically propagates through HTTP headers (W3C format)
- Context preserved across service boundaries

## Important Considerations

1. **No Test Suite**: Project ships without tests - verify changes manually against example integrations.

2. **Selective Processing**: Only forwards spans matching specific criteria to minimize overhead and costs.

3. **Framework Agnostic**: While optimized for Logfire, must work with vanilla OpenTelemetry.

4. **Interceptor Behavior**: Never interferes with existing span processors or exporters.

5. **Python 3.13+**: Uses modern Python features - no compatibility shims for older versions.

6. **Batch Processing**: Inherits BatchSpanProcessor behavior - spans exported in batches for efficiency.