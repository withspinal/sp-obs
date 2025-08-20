# SP-OBS: Spinal OpenTelemetry Integration

SP-OBS is Spinal's cost tracking library built on top of OpenTelemetry. It works by automatically instrumenting HTTP libraries (httpx, requests) and attaching a processor to existing OpenTelemetry setups. This dual approach allows it to integrate seamlessly with existing observability frameworks while selectively forwarding AI/LLM operations and billing events to Spinal's platform.

## Features

- Seamlessly integrates with existing OpenTelemetry setups
- Works with Logfire, vanilla OpenTelemetry, or any OTEL-compatible framework
- Automatic instrumentation of httpx and requests libraries
- Adds user and workflow context to spans for better tracking
- Selective span processing - only sends relevant AI/billing spans
- Built-in data scrubbing for sensitive information

## Supported Providers

### Foundation Models

SP-OBS automatically captures usage and costs for all models from these providers:

#### **OpenAI** (`api.openai.com`)
- **GPT Models**: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, GPT-3.5 Turbo 16K
- **DALL-E Models**: DALL-E 2, DALL-E 3
- **Whisper Models**: Whisper-1
- **Embedding Models**: text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
- **Fine-tuned Models**: All custom fine-tuned models
- **Function Calling**: All function calling and tool use
- **Vision Models**: GPT-4 Vision, GPT-4 Turbo Vision

#### **Anthropic** (`api.anthropic.com`)
- **Claude Models**: Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku
- **Legacy Models**: Claude 2.1, Claude 2.0, Claude Instant
- **Vision Models**: Claude 3 Vision models
- **Function Calling**: All function calling and tool use
- **Streaming**: Real-time streaming responses

### AI Tools & Services

SP-OBS also tracks usage for these AI-powered tools:

#### **ElevenLabs** (`api.elevenlabs.io`)
- Text-to-Speech conversion
- Voice cloning and synthesis
- Audio generation and manipulation

#### **SerpAPI** (`serpapi.com`)
- Search engine results
- Web scraping and data extraction
- SERP (Search Engine Results Page) data

#### **ScrapingBee** (`app.scrapingbee.com`)
- Web scraping and data extraction
- JavaScript rendering and dynamic content
- Proxy rotation and geolocation

#### **Firecrawl** (`api.firecrawl.dev`)
- Web crawling and scraping
- Content extraction
- Site monitoring and data collection

## Installation

```bash
pip install sp-obs
```

## Quick Start

### Configuration

Configure SP-OBS with your endpoint and API key. Instrumentation happens automatically when you call `configure()`:

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

That's it! SP-OBS will automatically instrument httpx and requests to capture AI/LLM operations and HTTP requests.

## Using Tags for Context

Tags allow you to add business context to your traces for better cost tracking and observability. They work through OpenTelemetry's baggage system and persist across function calls.

### Tag Usage Methods

#### **1. Context Manager (Recommended)**
```python
import sp_obs

with sp_obs.tag(
    workflow_id="workflow-123",
    user_id="user-456",
    aggregation_id="session-789",  # optional, reserved keyword
    custom_field="value",          # any additional tags
    environment="production"
):
    # All spans created here will have these tags
    response = client.chat.completions.create(...)
```

#### **2. Function Call (Applies to current context)**
```python
sp_obs.tag(
    workflow_id="workflow-123", 
    user_id="user-456",
    custom_metadata="example"
)
# All subsequent spans will have these tags
```

### Tag Naming Convention

All tags are automatically prefixed with `spinal.` in the baggage:
- `workflow_id` → `spinal.workflow_id`
- `user_id` → `spinal.user_id`
- `custom_field` → `spinal.custom_field`

**Special case**: `aggregation_id` becomes `spinal_aggregation_id`

### Real-World Example

```python
# Set tags for a user session
with sp_obs.tag(
    user_id="user-123",
    workflow_id="chatbot-session",
    session_id="sess-456",
    model_preference="gpt-4",
    tenant_id="enterprise-001"
):
    # This OpenAI call will have all tags attached
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}]
    )
    
    # Resulting span attributes:
    # - spinal.user_id: "user-123"
    # - spinal.workflow_id: "chatbot-session"
    # - spinal.session_id: "sess-456"
    # - spinal.model_preference: "gpt-4"
    # - spinal.tenant_id: "enterprise-001"
```

### Tag Best Practices

1. **Use Context Managers**: Prefer context managers for automatic cleanup
2. **Be Consistent**: Use consistent tag names across your application
3. **Include Business Context**: Add tags that help with cost analysis (user_id, tenant_id, etc.)
4. **Reserve aggregation_id**: Use this for grouping related traces together

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

@app.post("/generate")
async def generate(user_id: str, workflow_id: str):
    with sp_obs.tag(user_id=user_id, workflow_id=workflow_id):
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )
        return response
```

### Multi-Provider Example

```python
import sp_obs
from openai import OpenAI
from anthropic import Anthropic
import httpx

# Configure SP-OBS
sp_obs.configure(api_key="your-spinal-api-key")

# Set up clients
openai_client = OpenAI(api_key="your-openai-key")
anthropic_client = Anthropic(api_key="your-anthropic-key")

# Use with tags for context
with sp_obs.tag(
    user_id="user-123",
    workflow_id="content-generation",
    project="marketing-campaign"
):
    # OpenAI call
    openai_response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Write a blog post"}]
    )
    
    # Anthropic call
    anthropic_response = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        messages=[{"role": "user", "content": "Review this content"}]
    )
    
    # ElevenLabs call (via httpx)
    with httpx.Client() as client:
        tts_response = client.post(
            "https://api.elevenlabs.io/v1/text-to-speech/voice_id",
            json={"text": "Hello world"}
        )
```

## License

MIT License - see LICENSE file for details.