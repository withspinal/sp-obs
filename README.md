# sp-obs

SP-OBS is Spinal's cost tracking library built on top of OpenTelemetry. It works by automatically instrumenting HTTP libraries (httpx, requests) and 
attaching a processor to existing OpenTelemetry setups. This dual approach allows it to integrate seamlessly with existing observability frameworks while 
selectively forwarding AI/LLM operations and billing events to Spinal's platform.

## Features

- Seamlessly integrates with existing OpenTelemetry setups
- Works with Logfire, vanilla OpenTelemetry, or any OTEL-compatible framework
- Automatic instrumentation of httpx and requests libraries
- Adds user and workflow context to spans for better tracking
- Selective span processing - only sends relevant AI/billing spans
- Built-in data scrubbing for sensitive information

## Installation

```bash
pip install sp-obs
```

## Quick Start

```python
import sp_obs

# Configure with your API key
sp_obs.configure(api_key="your-api-key")

# That's it! AI calls are now tracked automatically
```

## Adding Context

Use tags to add business context to your AI operations:

```python
# Context manager (recommended)
with sp_obs.tag(user_id="user-123", workflow_id="chat-session"):
    # All AI calls here will be tagged
    response = openai_client.chat.completions.create(...)

# Or set tags globally
sp_obs.tag(user_id="user-123", workflow_id="chat-session")
```

## Supported Providers

- **OpenAI** - GPT-4, GPT-3.5, DALL-E, Whisper, Embeddings
- **Anthropic** - Claude 3 (Opus, Sonnet, Haiku), Claude 2
- **ElevenLabs** - Text-to-speech
- **Perplexity** - Online LLMs with search
- **Deepgram** - Speech-to-text
- **SerpAPI** - Search results
- **ScrapingBee** - Web scraping
- **Firecrawl** - Web crawling

## Billing Events

Track custom billing events:

```python
sp_obs.add_billing_event(
    success=True,
    user_id="user-123",
    amount=99.99,
    currency="USD"
)
```

## Environment Variables

- `SPINAL_API_KEY` - Your API key
- `SPINAL_TRACING_ENDPOINT` - Custom endpoint (default: https://cloud.withspinal.com)

## Advanced Configuration

### Batch Processing

Control how spans are batched and exported:

```python
sp_obs.configure(
    api_key="your-api-key",
    max_queue_size=2048,          # Max buffered spans before dropping
    max_export_batch_size=512,    # Spans per batch
    schedule_delay_millis=5000,   # Export interval (ms)
    export_timeout_millis=30000   # Export timeout (ms)
)
```

### Data Scrubbing

Automatically redact sensitive information from spans:

```python
from sp_obs import DefaultScrubber, NoOpScrubber

# Use default scrubber (removes tokens, keys, passwords)
sp_obs.configure(
    api_key="your-api-key",
    scrubber=DefaultScrubber()
)

# Disable scrubbing
sp_obs.configure(
    api_key="your-api-key",
    scrubber=NoOpScrubber()
)

# Custom scrubber
class CustomScrubber:
    def scrub_attributes(self, attributes: dict) -> dict:
        # Your scrubbing logic
        return attributes

sp_obs.configure(
    api_key="your-api-key",
    scrubber=CustomScrubber()
)
```

### Additional Options

```python
sp_obs.configure(
    api_key="your-api-key",
    endpoint="https://custom.endpoint.com",  # Custom endpoint
    headers={"X-Custom": "header"},          # Additional headers
    timeout=10,                              # Request timeout (seconds)
    set_global_tracer=False                  # Disable if using another tracer
)
```

## License

MIT