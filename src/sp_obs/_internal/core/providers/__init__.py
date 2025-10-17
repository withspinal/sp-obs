from sp_obs._internal.core.providers.base import BaseProvider
from sp_obs._internal.core.providers.mistral import MistralProvider
from sp_obs._internal.core.providers.openai import OpenAIProvider
from sp_obs._internal.core.providers.anthropic import AnthropicProvider
from sp_obs._internal.core.providers.firecrawl import FirecrawlProvider
from sp_obs._internal.core.providers.scrapingbee import ScrapingBeeProvider
from sp_obs._internal.core.providers.serpapi import SerpapiProvider
from sp_obs._internal.core.providers.elevenlabs import ElevenLabsProvider
from sp_obs._internal.core.providers.deepgram import DeepgramProvider
from sp_obs._internal.core.providers.perplexity import PerplexityProvider
from sp_obs._internal.core.providers.vertexai import VertexAIProvider
from sp_obs._internal.core.providers.voyageai import VoyageAIProvider

_provider_cache = {}


def get_provider(provider_name: str) -> BaseProvider:
    if provider_name not in _provider_cache:
        if provider_name == "openai":
            _provider_cache[provider_name] = OpenAIProvider()
        elif provider_name == "anthropic":
            _provider_cache[provider_name] = AnthropicProvider()
        elif provider_name == "firecrawl":
            _provider_cache[provider_name] = FirecrawlProvider()
        elif provider_name == "scrapingbee":
            _provider_cache[provider_name] = ScrapingBeeProvider()
        elif provider_name == "serpapi":
            _provider_cache[provider_name] = SerpapiProvider()
        elif provider_name == "elevenlabs":
            _provider_cache[provider_name] = ElevenLabsProvider()
        elif provider_name == "deepgram":
            _provider_cache[provider_name] = DeepgramProvider()
        elif provider_name == "perplexity":
            _provider_cache[provider_name] = PerplexityProvider()
        elif provider_name == "mistral":
            _provider_cache[provider_name] = MistralProvider()
        elif provider_name == "vertexai":
            _provider_cache[provider_name] = VertexAIProvider()
        elif provider_name == "voyageai":
            _provider_cache[provider_name] = VoyageAIProvider()
        else:
            raise ValueError(f"Invalid provider name: {provider_name}")

    return _provider_cache[provider_name]
