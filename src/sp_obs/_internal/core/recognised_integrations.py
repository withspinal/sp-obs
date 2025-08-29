GEN_AI_INTEGRATION = {
    "api.openai.com": "openai",
    "api.anthropic.com": "anthropic",
}

TOOLS_INTEGRATION = {
    "api.elevenlabs.io": "elevenlabs",
    "serpapi.com": "serpapi",
    "api.firecrawl.dev": "firecrawl",
    "app.scrapingbee.com": "scrapingbee",
    "api.deepgram.com": "deepgram",
}

INTEGRATIONS = GEN_AI_INTEGRATION | TOOLS_INTEGRATION
