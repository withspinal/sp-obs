"""Tests for integration domain mapping and URL filtering."""

import pytest
from urllib.parse import urlparse

from opentelemetry.util.http import redact_url

from sp_obs._internal.core.recognised_integrations import GEN_AI_INTEGRATION, TOOLS_INTEGRATION, INTEGRATIONS


class TestIntegrationMappings:
    """Test integration domain mappings and recognition."""

    def test_gen_ai_integration_mapping(self):
        """Test GEN_AI_INTEGRATION contains expected AI providers."""
        expected_providers = {"api.openai.com": "openai", "api.anthropic.com": "anthropic"}

        for domain, expected_system in expected_providers.items():
            assert domain in GEN_AI_INTEGRATION
            assert GEN_AI_INTEGRATION[domain] == expected_system

    def test_tools_integration_mapping(self):
        """Test TOOLS_INTEGRATION contains expected tool providers."""
        expected_tools = {
            "api.elevenlabs.io": "elevenlabs",
            "serpapi.com": "serpapi",
            "api.firecrawl.dev": "firecrawl",
            "app.scrapingbee.com": "scrapingbee",
        }

        for domain, expected_system in expected_tools.items():
            assert domain in TOOLS_INTEGRATION
            assert TOOLS_INTEGRATION[domain] == expected_system

    def test_integrations_combines_all_mappings(self):
        """Test INTEGRATIONS contains all providers from both mappings."""
        # Should contain all GEN_AI providers
        for domain in GEN_AI_INTEGRATION:
            assert domain in INTEGRATIONS
            assert INTEGRATIONS[domain] == GEN_AI_INTEGRATION[domain]

        # Should contain all TOOLS providers
        for domain in TOOLS_INTEGRATION:
            assert domain in INTEGRATIONS
            assert INTEGRATIONS[domain] == TOOLS_INTEGRATION[domain]

        # Should be the union of both
        expected_count = len(GEN_AI_INTEGRATION) + len(TOOLS_INTEGRATION)
        assert len(INTEGRATIONS) == expected_count

    def test_no_domain_overlap_between_categories(self):
        """Test that GEN_AI and TOOLS don't have overlapping domains."""
        gen_ai_domains = set(GEN_AI_INTEGRATION.keys())
        tools_domains = set(TOOLS_INTEGRATION.keys())

        # No overlap should exist
        overlap = gen_ai_domains & tools_domains
        assert len(overlap) == 0, f"Overlapping domains found: {overlap}"

    @pytest.mark.parametrize(
        "url,expected_domain,expected_system",
        [
            # OpenAI variations
            ("https://api.openai.com/v1/chat/completions", "api.openai.com", "openai"),
            ("https://api.openai.com/v1/models", "api.openai.com", "openai"),
            ("https://api.openai.com/", "api.openai.com", "openai"),
            # Anthropic variations
            ("https://api.anthropic.com/v1/messages", "api.anthropic.com", "anthropic"),
            ("https://api.anthropic.com/v1/complete", "api.anthropic.com", "anthropic"),
            # ElevenLabs variations
            ("https://api.elevenlabs.io/v1/text-to-speech/voice123", "api.elevenlabs.io", "elevenlabs"),
            ("https://api.elevenlabs.io/v1/voices", "api.elevenlabs.io", "elevenlabs"),
            # SerpAPI variations
            ("https://serpapi.com/search.json?q=test", "serpapi.com", "serpapi"),
            ("https://serpapi.com/account", "serpapi.com", "serpapi"),
            # Firecrawl variations
            ("https://api.firecrawl.dev/v0/crawl", "api.firecrawl.dev", "firecrawl"),
            ("https://api.firecrawl.dev/v0/scrape", "api.firecrawl.dev", "firecrawl"),
            # ScrapingBee variations
            ("https://app.scrapingbee.com/api/v1/", "app.scrapingbee.com", "scrapingbee"),
        ],
    )
    def test_integration_domain_extraction(self, url, expected_domain, expected_system):
        """Test domain extraction and system mapping for various URLs."""
        parsed = urlparse(url)
        actual_domain = parsed.netloc

        # Verify domain matches expected
        assert actual_domain == expected_domain

        # Verify domain is in integrations
        assert actual_domain in INTEGRATIONS

        # Verify correct system mapping
        assert INTEGRATIONS[actual_domain] == expected_system

    @pytest.mark.parametrize(
        "non_integration_url",
        [
            "https://httpbin.org/get",
            "https://jsonplaceholder.typicode.com/posts/1",
            "https://api.github.com/repos/owner/repo",
            "https://www.google.com/search?q=test",
            "https://example.com/api/v1/data",
            "https://api.stripe.com/v1/charges",
            "https://graph.microsoft.com/v1.0/me",
            "https://api.twilio.com/2010-04-01/Accounts",
        ],
    )
    def test_non_integration_domains_not_recognized(self, non_integration_url):
        """Test that non-integration domains are not in INTEGRATIONS."""
        parsed = urlparse(non_integration_url)
        domain = parsed.netloc

        # Should not be in integrations
        assert domain not in INTEGRATIONS

    def test_integration_filtering_logic(self):
        """Test the filtering logic used by instrumentations."""

        # Simulate the filtering logic from the instrumentations
        def should_process_url(url: str) -> bool:
            """Simulate the URL filtering logic from instrumentations."""
            location = urlparse(url)
            return location.netloc in INTEGRATIONS

        # Integration URLs should be processed
        integration_urls = [
            "https://api.openai.com/v1/test",
            "https://api.anthropic.com/v1/test",
            "https://api.elevenlabs.io/v1/test",
            "https://serpapi.com/test",
            "https://api.firecrawl.dev/v0/test",
        ]

        for url in integration_urls:
            assert should_process_url(url), f"Should process integration URL: {url}"

        # Non-integration URLs should be skipped
        non_integration_urls = [
            "https://httpbin.org/get",
            "https://api.github.com/repos/test",
            "https://example.com/api",
        ]

        for url in non_integration_urls:
            assert not should_process_url(url), f"Should skip non-integration URL: {url}"

    def test_case_sensitivity(self):
        """Test domain matching is case-sensitive (as expected for domains)."""
        # Domain names should be lowercase in the mappings
        for domain in INTEGRATIONS.keys():
            assert domain == domain.lower(), f"Domain should be lowercase: {domain}"

        # Test that uppercase versions don't match
        test_cases = [
            ("API.OPENAI.COM", False),
            ("api.openai.com", True),
            ("Api.OpenAI.Com", False),
            ("API.ANTHROPIC.COM", False),
            ("api.anthropic.com", True),
        ]

        for test_domain, should_match in test_cases:
            is_in_integrations = test_domain in INTEGRATIONS
            assert is_in_integrations == should_match, f"Domain {test_domain} matching should be {should_match}"

    def test_subdomain_specificity(self):
        """Test that integration matching is specific to exact subdomains."""
        # Test that subdomains of integration domains don't match
        non_matching_subdomains = [
            "subdomain.api.openai.com",
            "test.api.anthropic.com",
            "v2.api.elevenlabs.io",
            "beta.serpapi.com",
            "staging.api.firecrawl.dev",
        ]

        for subdomain in non_matching_subdomains:
            assert subdomain not in INTEGRATIONS, f"Subdomain should not match: {subdomain}"

        # Test that parent domains don't match
        parent_domains = [
            "openai.com",
            "anthropic.com",
            "elevenlabs.io",
            "firecrawl.dev",
        ]

        for parent in parent_domains:
            assert parent not in INTEGRATIONS, f"Parent domain should not match: {parent}"

    def test_integration_system_names_are_valid(self):
        """Test that all system names in integrations are valid identifiers."""
        for domain, system_name in INTEGRATIONS.items():
            # Should be non-empty string
            assert isinstance(system_name, str)
            assert len(system_name) > 0

            # Should be lowercase
            assert system_name == system_name.lower()

            # Should be valid identifier (no spaces, special chars)
            assert system_name.replace("_", "").replace("-", "").isalnum(), (
                f"System name should be alphanumeric (with _ or -): {system_name}"
            )

    def test_mapping_consistency(self):
        """Test consistency between different integration categories."""
        # All mappings should be consistent (same domain -> same system)
        all_mappings = {**GEN_AI_INTEGRATION, **TOOLS_INTEGRATION}

        for domain, system in all_mappings.items():
            assert INTEGRATIONS[domain] == system, (
                f"Inconsistent mapping for {domain}: expected {system}, got {INTEGRATIONS[domain]}"
            )

    @pytest.mark.parametrize(
        "category,mapping",
        [
            ("gen_ai", GEN_AI_INTEGRATION),
            ("tools", TOOLS_INTEGRATION),
        ],
    )
    def test_category_completeness(self, category, mapping):
        """Test that each category has reasonable completeness."""
        # Each category should have at least one provider
        assert len(mapping) > 0, f"{category} category should have at least one provider"

        # Each provider should have a valid mapping
        for domain, system in mapping.items():
            assert isinstance(domain, str)
            assert isinstance(system, str)
            assert len(domain) > 0
            assert len(system) > 0

    def test_integration_url_edge_cases(self):
        """Test edge cases in URL parsing and domain extraction."""
        edge_cases = [
            # URLs with ports (should still match)
            ("https://api.openai.com:443/v1/test", "api.openai.com", True),
            ("https://api.openai.com:8080/v1/test", "api.openai.com", True),
            # URLs with query parameters
            ("https://api.openai.com/v1/test?param=value", "api.openai.com", True),
            # URLs with fragments
            ("https://api.openai.com/v1/test#section", "api.openai.com", True),
            # URLs with userinfo (unusual but valid)
            ("https://user:pass@api.openai.com/v1/test", "api.openai.com", True),
            # IP addresses (should not match)
            ("https://192.168.1.1/api/v1/test", "192.168.1.1", False),
            ("https://127.0.0.1:8000/test", "127.0.0.1", False),
        ]

        for url, expected_netloc, should_be_integration in edge_cases:
            parsed = urlparse(redact_url(url))
            actual_netloc = parsed.hostname

            # Verify netloc extraction
            assert actual_netloc == expected_netloc

            # Verify integration status
            is_integration = actual_netloc in INTEGRATIONS
            assert is_integration == should_be_integration, (
                f"URL {url} integration status should be {should_be_integration}"
            )
