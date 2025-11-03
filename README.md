# sp-obs

SP-OBS is Spinal's cost tracking library built on top of OpenTelemetry. It works by automatically instrumenting HTTP libraries (httpx, requests, aiohttp) and gRPC calls, while attaching a processor to existing OpenTelemetry setups. This dual approach allows it to integrate seamlessly with existing observability frameworks while selectively forwarding AI/LLM operations and billing events to Spinal's platform.

## Features

- Seamlessly integrates with existing OpenTelemetry setups
- Works with Logfire, vanilla OpenTelemetry, or any OTEL-compatible framework
- Automatic instrumentation of httpx, requests, aiohttp libraries and gRPC calls
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

## Integration with Other Observability Tools

**IMPORTANT**: When using sp-obs alongside other OpenTelemetry providers (Logfire, Langwatch, Langsmith, Langfuse, etc.), you **MUST** set `set_global_tracer=False` to prevent tracer conflicts.

By default, sp-obs sets itself as the global tracer provider. When another OTEL library is already managing tracing, both libraries attempting to set the global tracer will cause conflicts.

### Using with Langwatch/Langsmith/Langfuse

```python
import langwatch

# Set up your primary observability tool first
langwatch.setup(api_key="your-langwatch-key")

# Configure sp-obs with set_global_tracer=False
sp_obs.configure(
    api_key="your-spinal-key",
    set_global_tracer=False
)
```

### Using with Logfire

```python
import logfire
import sp_obs

# Set up Logfire first
logfire.configure()

# Configure sp-obs with set_global_tracer=False
sp_obs.configure(
    api_key="your-spinal-key",
    set_global_tracer=False
)
```

**Note**: sp-obs will still capture and forward AI/LLM spans to Spinal even with `set_global_tracer=False`. It works by attaching its processor to the existing tracer provider.

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

**LLMs**: OpenAI, Anthropic, Perplexity
**Text-to-Speech**: ElevenLabs
**Speech-to-Text**: Deepgram
**APIs & Tools**: SerpAPI, ScrapingBee, Firecrawl

## Billing Events

Track custom billing events within a tagged context:

```python
with sp_obs.tag(user_id="user-123", workflow_id="checkout"):
    sp_obs.add_billing_event(
        success=True,
        amount=99.99,
        currency="USD"
    )
```

## Environment Variables

- `SPINAL_API_KEY` - Your API key
- `SPINAL_TRACING_ENDPOINT` - Custom endpoint (default: https://cloud.withspinal.com)

## Advanced Configuration

### Batch Processing

Control how spans are batched and exported to optimize for your application's needs:

```python
sp_obs.configure(
    api_key="your-api-key",
    max_queue_size=2048,          # Max buffered spans before dropping
    max_export_batch_size=512,    # Spans per batch
    schedule_delay_millis=5000,   # Export interval (ms)
    export_timeout_millis=30000   # Export timeout (ms)
)
```

**Parameter Guide:**

- **`max_queue_size`** (default: 2048)
  - Controls memory usage
  - **Increase** for high-volume applications (10k+ spans/min) to prevent drops during traffic spikes
  - **Decrease** for resource-constrained environments to limit memory footprint
  - **Performance impact**: Higher values = more memory but fewer outgoing network calls

- **`max_export_batch_size`** (default: 512)
  - Balances network efficiency vs. latency
  - **Increase** (up to 2048) for high-throughput applications to reduce network overhead
  - **Decrease** (to 128-256) for low-latency requirements to export spans more frequently
  - **Performance impact**: Larger batches = better network efficiency but slightly higher latency

- **`schedule_delay_millis`** (default: 5000ms)
  - How often to export spans, regardless of batch size
  - **Decrease** (to 1000-2000ms) when you need near real-time visibility
  - **Increase** (to 10000-30000ms) to reduce API calls and network overhead
  - **Performance impact**: Lower values = fresher data but more API calls and network usage

- **`export_timeout_millis`** (default: 30000ms)
  - Maximum time to wait for export to complete before failing
  - **Increase** for unreliable networks or when exporting large batches
  - **Decrease** if you prefer to drop spans rather than block on slow exports
  - **Performance impact**: Only matters when network is slow; higher values prevent timeouts

**Recommended Configurations:**

```python
# High-volume production (10k+ spans/min)
sp_obs.configure(max_queue_size=4096, max_export_batch_size=1024, schedule_delay_millis=3000)

# Low-latency requirements (real-time dashboards)
sp_obs.configure(max_queue_size=1024, max_export_batch_size=128, schedule_delay_millis=1000)

# Resource-constrained (serverless, edge)
sp_obs.configure(max_queue_size=512, max_export_batch_size=256, schedule_delay_millis=10000)
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
    set_global_tracer=False                  # See "Integration with Other Observability Tools"
)
```

## License

MIT