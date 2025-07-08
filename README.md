# SP-OBS: Spinal OpenTelemetry Integration

SP-OBS is an OpenTelemetry span interceptor that automatically attaches to existing TracerProvider instances to duplicate AI/LLM spans to custom endpoints for billing and monitoring.

## Features

- Automatically intercepts AI/LLM spans (e.g., from OpenAI, Anthropic)
- Seamlessly integrates with existing OpenTelemetry setups
- Works with Logfire, vanilla OpenTelemetry, or any OTEL-compatible framework
- Adds user and workflow context to spans for better tracking
- Selective span processing - only sends relevant AI/billing spans

## Installation

```bash
pip install sp-obs
```

## Quick Start

### With Existing OpenTelemetry Setup

If you already have OpenTelemetry configured (e.g., via Logfire, manual setup, or auto-instrumentation):

```python
from sp_obs import spinal_attach

# Simply attach to the existing TracerProvider
spinal_attach()
```

### With Logfire

```python
import logfire
from sp_obs import spinal_attach

# Configure logfire without sending to their backend
logfire.configure(send_to_logfire=False)

# Attach Spinal processor
spinal_attach()

# Use logfire instrumentation as normal
logfire.instrument_openai()
```

### Without Any OpenTelemetry Setup

```python
from sp_obs import spinal_attach

# Initialize OpenTelemetry and attach Spinal
spinal_attach(init_otel_if_needed=True, service_name="my-service")
```

### Manual Configuration

For more control, you can manually create and add the processor:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from sp_obs import SpinalConfig, SpinalSpanProcessor

# Set up OpenTelemetry
provider = TracerProvider()
trace.set_tracer_provider(provider)

# Configure and add Spinal processor
config = SpinalConfig(
    endpoint="https://your-endpoint.com/spans",
    api_key="your-api-key"
)
processor = SpinalSpanProcessor(config)
provider.add_span_processor(processor)
```

## Configuration

### Environment Variables

- `SPINAL_TRACING_ENDPOINT`: HTTP endpoint to send spans to
- `SPINAL_API_KEY`: API key for authentication

### SpinalConfig Options

```python
config = SpinalConfig(
    endpoint="https://your-endpoint.com/spans",  # Required
    api_key="your-api-key",                      # Required
    headers={"Custom-Header": "value"},          # Optional custom headers
    timeout=5,                                   # Request timeout in seconds
    batch_size=100                               # Batch size for span export
)
```

## Adding Context to Traces

Add user and workflow context that will be attached to all relevant spans:

```python
from sp_obs import spinal_add_context, spinal_add_as_billable

# Add context for tracking
context_token = spinal_add_context(
    workflow_id="workflow-123",
    user_id="user-456"
)

# Your AI/LLM operations here...

# Mark specific operations as billable
spinal_add_as_billable({
    "operation": "text_generation",
    "model": "gpt-4",
    "tokens": 1500
})
```

## Checking TracerProvider Status

```python
from sp_obs import is_tracer_provider_configured

if is_tracer_provider_configured():
    print("OpenTelemetry is already configured")
else:
    print("No TracerProvider configured")
```

## What Spans Are Captured?

SP-OBS automatically captures:
- AI/LLM spans (identified by `gen_ai.system` attribute)
- Explicitly created billing event spans
- Spans with attached user/workflow context

All other spans are ignored to minimize overhead and data transfer.

## Integration Examples

### FastAPI with Logfire

```python
from fastapi import FastAPI
import logfire
from sp_obs import spinal_attach, spinal_add_context

app = FastAPI()

# Configure observability
logfire.configure(send_to_logfire=False)
spinal_attach()
logfire.instrument_openai()

@app.post("/generate")
async def generate(user_id: str, workflow_id: str):
    # Add context for this request
    token = spinal_add_context(
        user_id=user_id,
        workflow_id=workflow_id
    )
    
    # Your OpenAI call here - automatically tracked
    response = await openai_client.chat.completions.create(...)
    return response
```

### Standalone Script

```python
from openai import OpenAI
from sp_obs import spinal_attach, spinal_add_context

# Initialize with automatic OTEL setup
spinal_attach(init_otel_if_needed=True)

# Add context
spinal_add_context(user_id="test-user", workflow_id="batch-job-1")

# Use OpenAI - spans automatically captured
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## License

[Your License Here]