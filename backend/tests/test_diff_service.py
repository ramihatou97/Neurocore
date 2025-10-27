"""
Tests for Diff Service
Tests text comparison and diff generation
"""

import pytest
from backend.services.diff_service import DiffService, DiffFormat


class TestDiffService:
    """Test suite for DiffService"""

    def test_calculate_similarity(self):
        """Test similarity calculation"""
        text1 = "Hello world"
        text2 = "Hello world"
        similarity = DiffService.calculate_similarity(text1, text2)
        assert similarity == 1.0

        text1 = "Hello world"
        text2 = "Goodbye world"
        similarity = DiffService.calculate_similarity(text1, text2)
        assert 0 < similarity < 1

    def test_generate_diff_unified(self):
        """Test unified diff generation"""
        text1 = "Line 1\nLine 2\nLine 3"
        text2 = "Line 1\nLine 2 modified\nLine 3"

        result = DiffService.generate_diff(text1, text2, format=DiffFormat.UNIFIED)

        assert result["format"] == "unified"
        assert "statistics" in result
        assert result["statistics"]["changed"] > 0

    def test_generate_diff_side_by_side(self):
        """Test side-by-side diff generation"""
        text1 = "Line 1\nLine 2"
        text2 = "Line 1\nLine 2 modified"

        result = DiffService.generate_diff(text1, text2, format=DiffFormat.SIDE_BY_SIDE)

        assert result["format"] == "side_by_side"
        assert "comparisons" in result
        assert len(result["comparisons"]) > 0

    def test_get_change_summary(self):
        """Test change summary generation"""
        text1 = "Hello world this is a test"
        text2 = "Hello world this is a modified test with more words"

        summary = DiffService.get_change_summary(text1, text2)

        assert "lines" in summary
        assert "words" in summary
        assert "characters" in summary
        assert "similarity" in summary

        assert summary["words"]["total_before"] == 6
        assert summary["words"]["total_after"] > 6

    def test_highlight_changes(self):
        """Test change highlighting"""
        text1 = "The quick brown fox"
        text2 = "The slow brown fox"

        marked1, marked2 = DiffService.highlight_changes(text1, text2)

        assert "[-quick-]" in marked1
        assert "[+slow+]" in marked2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
