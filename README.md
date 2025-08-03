# SP-OBS: Spinal OpenTelemetry Integration

SP-OBS is Spinal's cost tracking library built on top of open telemetry. It works by adding isolated tracers to libraries that have not been instrumented
and attached a processor to libraries that aloready have been instrumented. 
This means we can also play nice with other observability libraries out there. 
## Features

- Seamlessly integrates with existing OpenTelemetry setups
- Works with Logfire, vanilla OpenTelemetry, or any OTEL-compatible framework
- Adds user and workflow context to spans for better tracking
- Selective span processing - only sends relevant AI/billing spans

## Installation

```bash
pip install sp-obs
```

### With AI Provider Support

```bash
# For OpenAI support
pip install sp-obs[openai]

# For Anthropic support  
pip install sp-obs[anthropic]

# For all providers
pip install sp-obs[all]
```

## Quick Start

### Configuration

First, configure SP-OBS with your endpoint and API key:

```python
import sp_obs

# Configure globally (recommended)
sp_obs.configure(
    api_key="your-api-key"
    # endpoint defaults to "https://cloud.withspinal.com" if not specified
)
```

Or use environment variables:
- `SPINAL_TRACING_ENDPOINT` (defaults to "https://cloud.withspinal.com")
- `SPINAL_API_KEY`

### Instrumenting AI Providers

```python
import sp_obs

# Configure SP-OBS
sp_obs.configure()

# Instrument providers
sp_obs.instrument_openai()
sp_obs.instrument_anthropic()
sp_obs.instrument_httpx()
sp_obs.instrument_requests()
```

### Adding Tags to Traces

Use the `tag` function to add user, workflow, and custom information to traces:

```python
import sp_obs

# As a context manager
with sp_obs.tag(
    workflow_id="workflow-123",
    user_id="user-456",
    aggregation_id="session-789",  # optional, reserved keyword
    custom_field="value",          # any additional tags
    environment="production"
):
    # All spans created here will have these tags
    response = client.chat.completions.create(...)

# As a function call (applies tags to current context)
sp_obs.tag(
    workflow_id="workflow-123", 
    user_id="user-456",
    custom_metadata="example"
)
```

**Note**: Only `aggregation_id` is a reserved keyword parameter. All other keyword arguments are added as custom tags with the `spinal.` prefix.

## Configuration Options

### Environment Variables

- `SPINAL_TRACING_ENDPOINT`: HTTP endpoint to send spans to (default: "https://cloud.withspinal.com")
- `SPINAL_API_KEY`: API key for authentication
- `SPINAL_PROCESS_MAX_QUEUE_SIZE`: Max spans in queue (default: 2048)
- `SPINAL_PROCESS_SCHEDULE_DELAY`: Export delay in ms (default: 5000)
- `SPINAL_PROCESS_MAX_EXPORT_BATCH_SIZE`: Batch size (default: 512)
- `SPINAL_PROCESS_EXPORT_TIMEOUT`: Export timeout in ms (default: 30000)

### Advanced Configuration

```python
sp_obs.configure(
    api_key="your-api-key",
    endpoint="https://cloud.withspinal.com",  # Optional - this is the default
    headers={"Custom-Header": "value"},
    timeout=5,
    max_queue_size=2048,
    max_export_batch_size=512,
    schedule_delay_millis=5000,
    export_timeout_millis=30000,
    scrubber=my_custom_scrubber  # Optional
)
```

## Data Scrubbing

SP-OBS includes automatic scrubbing of sensitive data:

```python
from sp_obs import DefaultScrubber, NoOpScrubber

# Use default scrubber (redacts tokens, keys, passwords)
sp_obs.configure(scrubber=DefaultScrubber())

# Or disable scrubbing
sp_obs.configure(scrubber=NoOpScrubber())

# Or implement custom scrubbing
class MyCustomScrubber:
    def scrub_attributes(self, attributes: dict) -> dict:
        # Your scrubbing logic
        return attributes

sp_obs.configure(scrubber=MyCustomScrubber())
```

## Performance Considerations

SP-OBS uses a BatchSpanProcessor to minimize performance impact:

- Spans are batched and sent asynchronously in a background thread
- Default batch size: 512 spans
- Default flush interval: 5 seconds
- Spans are dropped if queue exceeds max size (default: 2048)

To tune for high-volume applications:

```python
sp_obs.configure(
    max_queue_size=5000,          # Increase queue size
    max_export_batch_size=1000,   # Larger batches
    schedule_delay_millis=2000    # More frequent exports
)
```

## What Spans Are Captured?

SP-OBS automatically captures:
- AI/LLM spans (identified by `gen_ai.system` attribute)
- HTTPX and request spans
- Explicitly created billing event spans
- Spans with attached user/workflow context

All other spans are ignored to minimize overhead and data transfer.

## Integration Examples

### FastAPI Application

```python
from fastapi import FastAPI
import sp_obs
from openai import AsyncOpenAI

app = FastAPI()
client = AsyncOpenAI()

# Configure on startup
@app.on_event("startup")
async def startup():
    sp_obs.configure()
    sp_obs.instrument_openai()

@app.post("/generate")
async def generate(user_id: str, workflow_id: str):
    with sp_obs.tag(user_id=user_id, workflow_id=workflow_id):
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )
        return response
```

## License

MIT License - see LICENSE file for details.