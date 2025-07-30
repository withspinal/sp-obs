"""
Unit tests for scrubbing functionality
"""

import unittest

from sp_obs import DefaultScrubber, NoOpScrubber


class TestDefaultScrubber(unittest.TestCase):
    def setUp(self):
        self.scrubber = DefaultScrubber()

    def test_scrub_basic_patterns(self):
        attributes = {
            "password": "secret123",
            "api_key": "sk-1234567890",
            "user_name": "john_doe",
            "secret_token": "abc123",
            "normal_field": "visible_data",
        }

        scrubbed = self.scrubber.scrub_attributes(attributes)

        # Check sensitive fields are scrubbed
        self.assertIn("[Scrubbed due to password]", scrubbed["password"])
        self.assertIn("[Scrubbed due to api", scrubbed["api_key"])
        self.assertIn("[Scrubbed due to secret_token]", scrubbed["secret_token"])
        self.assertIn("[Scrubbed due to user_name]", scrubbed["user_name"])

        # Check normal fields are not scrubbed
        self.assertEqual(scrubbed["normal_field"], "visible_data")

    def test_scrub_case_insensitive(self):
        attributes = {"PASSWORD": "secret", "ApiKey": "key123", "SECRET": "hidden"}

        scrubbed = self.scrubber.scrub_attributes(attributes)

        self.assertIn("[Scrubbed", scrubbed["PASSWORD"])
        self.assertIn("[Scrubbed", scrubbed["ApiKey"])
        self.assertIn("[Scrubbed", scrubbed["SECRET"])

    def test_scrub_nested_dictionaries(self):
        attributes = {
            "user": {
                "name": "John",
                "password": "secret123",
                "profile": {
                    "api_key": "hidden",
                    "email": "john@example.com",
                    "dogs_name": "billy",
                },
            }
        }

        scrubbed = self.scrubber.scrub_attributes(attributes)

        # Check nested values are scrubbed
        self.assertIn("[Scrubbed", scrubbed["user"]["password"])
        self.assertIn("[Scrubbed", scrubbed["user"]["profile"]["api_key"])
        self.assertIn("[Scrubbed", scrubbed["user"]["profile"]["email"])

        # Check normal values remain
        self.assertEqual(scrubbed["user"]["profile"]["dogs_name"], "billy")

    def test_scrub_lists(self):
        attributes = {
            "items": [{"name": "item1", "secret": "hidden1"}, {"name": "item2", "api_key": "hidden2"}, "plain_string"]
        }

        scrubbed = self.scrubber.scrub_attributes(attributes)

        # Check list items are processed
        self.assertIn("[Scrubbed", scrubbed["items"][0]["secret"])
        self.assertIn("[Scrubbed", scrubbed["items"][1]["api_key"])
        self.assertEqual(scrubbed["items"][2], "plain_string")

    def test_custom_patterns(self):
        custom_scrubber = DefaultScrubber(extra_patterns=["dogs_name", "ssn", "credit_card", "profile_information"])

        attributes = {
            "user_email": "test@example.com",
            "dogs_name": "billy",
            "ssn": "123-45-6789",
            "credit_card": "1234-5678-9012-3456",
            "normal_field": "visible",
            "profile_information": {"test1": "test1", "test2": "test2"},
        }

        scrubbed = custom_scrubber.scrub_attributes(attributes)

        # Check custom patterns are scrubbed
        self.assertIn("[Scrubbed", scrubbed["dogs_name"])
        self.assertIn("[Scrubbed", scrubbed["ssn"])
        self.assertIn("[Scrubbed", scrubbed["credit_card"])
        self.assertIn("[Scrubbed", scrubbed["profile_information"])  # replaces the whole dictionary

        # Normal field remains
        self.assertEqual(scrubbed["normal_field"], "visible")

    def test_empty_attributes(self):
        """Test scrubbing empty or None attributes"""
        self.assertEqual(self.scrubber.scrub_attributes({}), {})
        self.assertEqual(self.scrubber.scrub_attributes(None), None)

    def test_protected_patterns(self):
        """Test that protected patterns are not scrubbed"""

        with self.assertRaisesRegex(ValueError, r"Attribute name 'spinal' is protected and cannot be scrubbed"):
            _ = DefaultScrubber(extra_patterns=["credit_card", "house", "spinal"])

        with self.assertRaisesRegex(ValueError, r"Attribute name 'attributes' is protected and cannot be scrubbed"):
            _ = DefaultScrubber(extra_patterns=["credit_card", "house", "attributes"])

        _ = DefaultScrubber(extra_patterns=["credit_card", "house", "personal_attributes"])


class TestNoOpScrubber(unittest.TestCase):
    """Test NoOpScrubber class"""

    def setUp(self):
        """Create scrubber instance for tests"""
        self.scrubber = NoOpScrubber()

    def test_no_scrubbing(self):
        """Test that NoOpScrubber doesn't modify attributes"""
        attributes = {
            "password": "visible_password",
            "api_key": "visible_key",
            "secret": "visible_secret",
            "normal": "normal_value",
        }

        result = self.scrubber.scrub_attributes(attributes)

        # Everything should be unchanged
        self.assertEqual(result, attributes)
        self.assertEqual(result["password"], "visible_password")
        self.assertEqual(result["api_key"], "visible_key")

    def test_nested_no_scrubbing(self):
        """Test that nested structures remain unchanged"""
        attributes = {"nested": {"password": "still_visible", "deeper": {"secret": "also_visible"}}}

        result = self.scrubber.scrub_attributes(attributes)

        # Should be identical
        self.assertEqual(result, attributes)


if __name__ == "__main__":
    unittest.main()
