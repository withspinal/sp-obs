import typing
from urllib.parse import urlparse

import httpx
import opentelemetry.instrumentation.httpx

from opentelemetry.semconv_ai import SpanAttributes as AISpanAttributes
from httpx import AsyncByteStream, SyncByteStream
from opentelemetry import context, trace
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import get_tracer
from opentelemetry.util.http import redact_url

from sp_obs._internal.core.httpx.async_stream import AsyncStreamWrapper
from sp_obs._internal.core.httpx.sync_stream import SyncStreamWrapper
from sp_obs._internal.core.recognised_integrations import supported_host
from sp_obs.utils import add_request_params_to_span


class SpinalHTTPXClientInstrumentor(opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor):
    def _instrument(self, **kwargs):
        provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, tracer_provider=provider)
        super()._instrument(**kwargs)

        original_extract_response = opentelemetry.instrumentation.httpx._extract_response

        def _wrapped_extract(
            response: httpx.Response | tuple[int, httpx.Headers, httpx.SyncByteStream, dict[str, typing.Any]],
        ):
            # The current tracing context will pick up the normal httpx span current operating. However, because
            # of the conditional check 'isinstance(response, (httpx.Response, tuple))' in the base library, we will
            # not be able to tell if an exception has been raised. So this will only trigger for successful
            # operations. We would need to use the parent span created by httpx
            current_tracing_context = context.get_current()
            result = original_extract_response(response)

            # Check to see if we have support for this type of span
            httpx_span = trace.get_current_span(current_tracing_context)
            httpx_attributes = getattr(httpx_span, "attributes", {}) if httpx_span else {}
            if httpx_attributes:
                url = httpx_attributes.get(SpanAttributes.HTTP_URL)
                redacted_url = redact_url(url)

                location = urlparse(redacted_url)
                integration_provider = supported_host(location.hostname)
                if not integration_provider:
                    return result

                # Set parent span attributes which will be loaded into children upon creation
                httpx_span.set_attribute("spinal.provider", integration_provider)
                httpx_span.set_attribute("http.host", location.hostname)
                httpx_span.set_attribute(AISpanAttributes.LLM_SYSTEM, integration_provider)
                add_request_params_to_span(httpx_span, redacted_url)

            else:
                return result

            stream = response.stream
            if isinstance(stream, AsyncByteStream):
                wrapped_stream = AsyncStreamWrapper(
                    response=response,
                    wrapped_stream=stream,
                    tracer=tracer,
                    parent_context=current_tracing_context,
                    parent_attributes=httpx_attributes,
                )
            elif isinstance(stream, SyncByteStream):
                wrapped_stream = SyncStreamWrapper(
                    response=response,
                    wrapped_stream=stream,
                    tracer=tracer,
                    parent_context=current_tracing_context,
                    parent_attributes=httpx_attributes,
                )
            else:
                wrapped_stream = stream

            response.stream = wrapped_stream
            return result

        opentelemetry.instrumentation.httpx._extract_response = _wrapped_extract
