"""
Unit tests for safe_decode function in the exporter module
"""

from sp_obs._internal.exporter import safe_decode


class TestSafeDecode:
    """Test safe_decode function"""

    def test_valid_utf8(self):
        """Test decoding valid UTF-8 text"""
        # ASCII text
        assert safe_decode(b"Hello World") == "Hello World"

        # UTF-8 with emojis
        assert safe_decode("Hello 🌍 World".encode("utf-8")) == "Hello 🌍 World"

        # UTF-8 with Chinese characters
        assert safe_decode("你好世界".encode("utf-8")) == "你好世界"

        # UTF-8 with various Unicode
        text = 'Café ñoño €100 • "quotes"'
        assert safe_decode(text.encode("utf-8")) == text

    def test_windows_1252_fallback(self):
        """Test fallback to Windows-1252 encoding"""
        # Windows smart quotes (0x93 and 0x94)
        data = b"He said \x93Hello\x94"
        result = safe_decode(data)
        # Should decode with windows-1252 to get Unicode left/right double quotes (U+201C, U+201D)
        assert result == "He said \u201cHello\u201d"  # Using Unicode escapes for clarity

        # Euro sign (0x80 in Windows-1252)
        data = b"\x80 100"
        result = safe_decode(data)
        assert result == "€ 100"

        # Em dash (0x97 in Windows-1252)
        data = b"Start\x97End"
        result = safe_decode(data)
        assert result == "Start—End"

    def test_latin1_ultimate_fallback(self):
        """Test fallback to Latin-1 for non-UTF-8, non-Windows-1252 data"""
        # Data with bytes that are invalid in Windows-1252 (0x81, 0x8D, 0x8F, 0x90, 0x9D)
        # These should fall back to Latin-1
        data = b"Test\x81\x8d\x8f\x90\x9d"
        result = safe_decode(data)
        # Latin-1 will decode these as control characters
        assert len(result) == 9  # All bytes decoded
        assert result.startswith("Test")

    def test_invalid_utf8_bytes(self):
        """Test handling of invalid UTF-8 byte sequences"""
        # Invalid UTF-8 continuation byte
        data = b"Hello\x9aWorld"
        result = safe_decode(data)
        # Should not raise, should return some decoded string
        assert "Hello" in result
        assert "World" in result

        # Invalid UTF-8 start byte
        data = b"Test\xc3\x28End"  # 0xC3 expects continuation but gets 0x28
        result = safe_decode(data)
        assert "Test" in result
        assert "End" in result

    def test_mixed_content(self):
        """Test handling of mixed valid and invalid content"""
        # Mix of valid ASCII and invalid UTF-8
        data = b"Start\xdb\x9aMiddle\xff\xfeEnd"
        result = safe_decode(data)
        # Should handle gracefully without raising
        assert "Start" in result
        assert "Middle" in result
        assert "End" in result

    def test_empty_and_edge_cases(self):
        """Test edge cases"""
        # Empty bytes
        assert safe_decode(b"") == ""

        # Single byte
        assert safe_decode(b"A") == "A"

        # Null byte
        assert safe_decode(b"\x00") == "\x00"

        # All possible single bytes (Latin-1 should handle all)
        for i in range(256):
            result = safe_decode(bytes([i]))
            assert len(result) == 1  # Should decode to exactly one character

    def test_real_world_scenarios(self):
        """Test scenarios that might occur with OpenAI/Anthropic responses"""
        # Truncated UTF-8 multibyte sequence (common in streaming)
        truncated = "Hello 世".encode("utf-8")[:-1]  # Cut off last byte of 世
        result = safe_decode(truncated)
        assert "Hello" in result

        # JSON with smart quotes from Windows
        json_like = b'{"message": \x93Hello\x94}'
        result = safe_decode(json_like)
        # Check for Windows-1252 left/right double quotes (U+201C, U+201D)
        assert "\u201cHello\u201d" in result

        # SSE stream with mixed content
        sse_data = b'data: {"text": "Test\x97Complete"}\n\n'
        result = safe_decode(sse_data)
        assert "Test—Complete" in result  # Em dash from Windows-1252
