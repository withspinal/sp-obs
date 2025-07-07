# sp-obs

Spinal Observability integration for Python applications. This library provides a custom OpenTelemetry span processor that integrates seamlessly with observability frameworks like Pydantic Logfire.

## Installation

```bash
pip install sp-obs
```

## Usage with Logfire

The recommended way to use sp-obs is by integrating it with Pydantic Logfire's `additional_span_processors`:

```python
import logfire
from sp_obs import SpinalSpanProcessor, SpinalConfig

# Configure Spinal
spinal_config = SpinalConfig(
    endpoint="https://your-spinal-endpoint.com/spans",
    api_key="your-api-key"  # or set SPINAL_API_KEY env var
)

# Initialize logfire with Spinal processor
logfire.configure(
    additional_span_processors=[SpinalSpanProcessor(spinal_config)],
    # other logfire configuration...
)
```

## Configuration

### Environment Variables

- `SPINAL_API_KEY`: Your Spinal API key
- `SPINAL_TRACING_ENDPOINT`: The Spinal tracing endpoint URL

### SpinalConfig Options

- `endpoint`: HTTP endpoint to send spans to (required)
- `api_key`: API key for authentication (required)
- `headers`: Optional custom headers for the HTTP request
- `timeout`: Request timeout in seconds (default: 30)
- `batch_size`: Batch size for span export (default: 100)

## Features

### Context Management

Add both workflow and user context to traces for comprehensive tracking:

```python
from sp_obs import spinal_add_context

# Add workflow and user context to current trace
token = spinal_add_context(workflow_id=12345, user_id="user123")
# Your traced operations here
# Optionally detach context when done
context.detach(token)
```

### User Context

Add user context to spans for better tracking:

```python
from sp_obs import add_user_context

# In your request handler
add_user_context(
    mapped_user_id="user123",
    attributes={"plan": "premium", "region": "us-west"}
)
```

### Billable Events

Mark specific operations as billable:

```python
from sp_obs import add_as_billable

# Mark an operation as billable
add_as_billable(attributes={
    "operation": "api_call",
    "credits_used": 10
})
```

## What Gets Tracked

The SpinalSpanProcessor automatically tracks:
- Spans with `gen_ai.system` attribute (AI/LLM operations)
- Billable events (marked with `spinal_add_as_billable`)
- User context spans
- Spans with workflow_id and user context from baggage

## Migration from Legacy API

If you're using the old `sp_obs.init()` approach, migrate to the new API:

```python
# Old (deprecated)
import sp_obs
sp_obs.init(endpoint="...", api_key="...")

# New (recommended)
import logfire
from sp_obs import SpinalSpanProcessor, SpinalConfig

config = SpinalConfig(endpoint="...", api_key="...")
logfire.configure(additional_span_processors=[SpinalSpanProcessor(config)])
```

## License

MIT License - see LICENSE file for details.