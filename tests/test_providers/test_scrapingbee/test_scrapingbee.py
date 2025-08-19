from typing import Any, Dict
import pytest

from sp_obs._internal.core.providers import get_provider


class TestScrapingBeeProvider:
    """Test ScrapingBee provider functionality"""

    @pytest.fixture
    def sample_response_attributes(self) -> Dict[str, Any]:
        """Provide sample ScrapingBee response attributes from actual span"""
        return {
            "spinal.provider": "scrapingbee",
            "content-type": "application/json",
            "content-encoding": "",
            "http.status_code": 500,
            "http.url": "https://app.scrapingbee.com/api/v1/?api_key=REDACTED&url=https%3A%2F%2Fapp.scrapingbee.com%2Fapi%2Fv1%2F%3Fapi_key%3DBAD_KEY%26url%3Dhttps%3A%2F%2Fexample.com&render_js=false",
            "http.host": "app.scrapingbee.com",
            "spinal.http.request.query.url": "https://app.scrapingbee.com/api/v1/?api_key=BAD_KEY&url=https://example.com",
            "spinal.http.request.query.render_js": "false",
            "spinal.response.size": 647,
            "spinal.response.streaming": False,
        }

    @pytest.fixture
    def sample_response_headers(self) -> Dict[str, Any]:
        """Provide sample ScrapingBee response headers from actual production response"""
        return {
            "Date": "Tue, 19 Aug 2025 18:01:21 GMT",
            "Content-Type": "text/html; charset=UTF-8",
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
            "Spb-access-control-allow-credentials": "true",
            "Spb-cache-control": "max-age=3, must-revalidate",
            "Spb-content-encoding": "gzip",
            "Spb-content-type": "text/html; charset=UTF-8",
            "Spb-date": "Tue, 19 Aug 2025 18:01:18 GMT",
            "Spb-server": "Apache",
            "Spb-strict-transport-security": "max-age=31536000; includeSubDomains",
            "Spb-vary": "Accept-Encoding,Cookie",
            "Spb-via": "1.1 ac3e1d7135d19671e1860c67a45b3f70.cloudfront.net (CloudFront)",
            "Spb-x-amz-cf-id": "UeJgb2_m9c4kI3ucKsCDb_XLgTZDENxTIrgEuue4c_NXtNVm_LMCpg==",
            "Spb-x-amz-cf-pop": "OSL50-P2",
            "Spb-x-cache": "Miss from cloudfront",
            "Spb-x-content-type-options": "nosniff",
            "Spb-x-frame-options": "DENY",
            "Spb-cost": "5",
            "Spb-initial-status-code": "200",
            "Spb-resolved-url": "https://www.geeksforgeeks.org/python/self-in-python-class/",
            "Set-Cookie": "http_referrer=https://www.geeksforgeeks.org/python/self-in-python-class/; Domain=geeksforgeeks.org; Expires=Wed, 31 Dec 1969 23:59:59 GMT; Path=/, _lr_retry_request=true; Domain=www.geeksforgeeks.org; Expires=Tue, 19 Aug 2025 19:01:21 GMT; Path=/, _pubcid=b8e54c51-4909-46d2-bfb2-d8e4076547eb; Domain=geeksforgeeks.org; Expires=Thu, 18 Sep 2025 18:01:21 GMT; Path=/, gfg_ads_exp=NO-RUNNING-EXPERIMENTS; Domain=geeksforgeeks.org; Expires=Wed, 31 Dec 1969 23:59:59 GMT; Path=/, _gd_visitor=491848ec-4b96-490e-8c9e-7ab61f8f8954; Domain=www.geeksforgeeks.org; Expires=Wed, 23 Sep 2026 18:01:21 GMT; Path=/, _gd_session=c3c2585d-6011-4186-8191-cfa71d583b85; Domain=www.geeksforgeeks.org; Expires=Tue, 19 Aug 2025 22:01:21 GMT; Path=/, _pubcid_cst=zix7LPQsHA%3D%3D; Domain=geeksforgeeks.org; Expires=Thu, 18 Sep 2025 18:01:21 GMT; Path=/, _gcl_au=1.1.138642603.1755626480; Domain=geeksforgeeks.org; Expires=Mon, 17 Nov 2025 18:01:20 GMT; Path=/, _lr_env_src_ats=false; Domain=www.geeksforgeeks.org; Expires=Thu, 18 Sep 2025 18:01:21 GMT; Path=/, gfg_id5_ipv4=157.90.64.97; Domain=geeksforgeeks.org; Expires=Wed, 31 Dec 1969 23:59:59 GMT; Path=/, _ga=GA1.1.1230185266.1755626480; Domain=geeksforgeeks.org; Expires=Wed, 23 Sep 2026 18:01:20 GMT; Path=/, gfg_ads_country=DE; Domain=geeksforgeeks.org; Expires=Wed, 31 Dec 1969 23:59:59 GMT; Path=/, _ga_DWCCJLKX3X=GS2.1.s1755626480$o1$g0$t1755626480$j60$l0$h0; Domain=geeksforgeeks.org; Expires=Wed, 23 Sep 2026 18:01:20 GMT; Path=/, gfg_id5_user_agent=Mozilla/5.0%20%28X11%3B%20Linux%20x86_64%29%20AppleWebKit/537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome/131.0.0.0%20Safari/537.36; Domain=geeksforgeeks.org; Expires=Wed, 31 Dec 1969 23:59:59 GMT; Path=/",
            "Access-Control-Allow-Origin": "*",
            "Permissions-Policy": "browsing-topics=()",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "Strict-Transport-Security": "max-age=31556926; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Vary": "Cookie",
            "Content-Encoding": "gzip",
            "Sozu-Id": "01K31QW6GX08VPGAE0XQ4EDTWT",
        }

    def test_provider_identification(self, sample_response_attributes):
        """Test that the correct provider is identified"""
        provider = get_provider(sample_response_attributes["spinal.provider"])

        # Verify it's the ScrapingBeeProvider provider
        from sp_obs._internal.core.providers.scrapingbee import ScrapingBeeProvider

        assert isinstance(provider, ScrapingBeeProvider), f"Expected ScrapingBeeProvider instance, got {type(provider)}"

    def test_provider_parse_header_attributes(self, sample_response_headers):
        """Test that the provider parses the header attributes correctly"""
        provider = get_provider("scrapingbee")

        headers = {"cost": "5"}

        parsed = provider.parse_response_headers(sample_response_headers)
        # Verify it's returning the expected output
        assert parsed == headers

    def test_provider_parse_response_attributes(self, sample_response_attributes):
        """Test that the provider parses the response attributes correctly"""
        provider = get_provider("scrapingbee")
        # test that the provider returns an empty dict
        parsed = provider.parse_response_attributes(sample_response_attributes)
        assert parsed == {}
