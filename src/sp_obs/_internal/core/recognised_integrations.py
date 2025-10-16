GEN_AI_INTEGRATION = {
    "api.openai.com": "openai",
    "api.anthropic.com": "anthropic",
    "api.mistral.ai": "mistral",
    "api.voyageai.com": "voyageai",
}

TOOLS_INTEGRATION = {
    "api.elevenlabs.io": "elevenlabs",
    "serpapi.com": "serpapi",
    "api.firecrawl.dev": "firecrawl",
    "app.scrapingbee.com": "scrapingbee",
    "api.deepgram.com": "deepgram",
    "api.perplexity.ai": "perplexity",
}

INTEGRATIONS = GEN_AI_INTEGRATION | TOOLS_INTEGRATION


def supported_host(hostname: str) -> str | None:
    if standard_host := INTEGRATIONS.get(hostname):
        return standard_host

    if hostname.find("aiplatform.googleapis.com") != -1:
        return "vertexai"

    return None
