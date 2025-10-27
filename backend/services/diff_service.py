"""
Diff Service - Text Comparison and Diff Generation
Provides various diff formats and similarity analysis between text versions
"""

import difflib
from typing import List, Dict, Any, Tuple
from enum import Enum

from backend.utils import get_logger

logger = get_logger(__name__)


class DiffFormat(str, Enum):
    """Diff output formats"""
    UNIFIED = "unified"
    HTML = "html"
    SIDE_BY_SIDE = "side_by_side"
    LINES = "lines"
    WORDS = "words"


class DiffService:
    """
    Service for generating diffs between text versions

    Provides:
    - Line-by-line diffs
    - Word-by-word diffs
    - HTML formatted diffs
    - Side-by-side comparison
    - Similarity scoring
    - Change statistics
    """

    @staticmethod
    def generate_diff(
        text1: str,
        text2: str,
        format: DiffFormat = DiffFormat.UNIFIED,
        context_lines: int = 3
    ) -> Dict[str, Any]:
        """
        Generate diff between two texts

        Args:
            text1: Original text
            text2: Modified text
            format: Desired diff format
            context_lines: Number of context lines for unified diff

        Returns:
            Dictionary containing diff data and statistics
        """
        try:
            if format == DiffFormat.UNIFIED:
                return DiffService._generate_unified_diff(text1, text2, context_lines)
            elif format == DiffFormat.HTML:
                return DiffService._generate_html_diff(text1, text2)
            elif format == DiffFormat.SIDE_BY_SIDE:
                return DiffService._generate_side_by_side_diff(text1, text2)
            elif format == DiffFormat.LINES:
                return DiffService._generate_line_diff(text1, text2)
            elif format == DiffFormat.WORDS:
                return DiffService._generate_word_diff(text1, text2)
            else:
                raise ValueError(f"Unknown diff format: {format}")

        except Exception as e:
            logger.error(f"Failed to generate diff: {str(e)}")
            raise

    @staticmethod
    def _generate_unified_diff(
        text1: str,
        text2: str,
        context_lines: int = 3
    ) -> Dict[str, Any]:
        """Generate unified diff format (similar to git diff)"""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            lines1,
            lines2,
            fromfile="Version A",
            tofile="Version B",
            lineterm='',
            n=context_lines
        ))

        stats = DiffService._calculate_diff_stats(lines1, lines2)

        return {
            "format": "unified",
            "diff": "\n".join(diff),
            "diff_lines": diff,
            "statistics": stats
        }

    @staticmethod
    def _generate_html_diff(text1: str, text2: str) -> Dict[str, Any]:
        """Generate HTML formatted diff"""
        differ = difflib.HtmlDiff()

        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        html = differ.make_table(
            lines1,
            lines2,
            fromdesc="Version A",
            todesc="Version B",
            context=True,
            numlines=3
        )

        stats = DiffService._calculate_diff_stats(lines1, lines2)

        return {
            "format": "html",
            "html": html,
            "statistics": stats
        }

    @staticmethod
    def _generate_side_by_side_diff(text1: str, text2: str) -> Dict[str, Any]:
        """Generate side-by-side diff with line matching"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        # Use SequenceMatcher to find matching blocks
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        opcodes = matcher.get_opcodes()

        side_by_side = []

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                # Lines are the same
                for i in range(i1, i2):
                    side_by_side.append({
                        "type": "equal",
                        "left_line": i + 1,
                        "left_content": lines1[i],
                        "right_line": j1 + (i - i1) + 1,
                        "right_content": lines2[j1 + (i - i1)]
                    })
            elif tag == 'replace':
                # Lines are different
                max_len = max(i2 - i1, j2 - j1)
                for i in range(max_len):
                    left_content = lines1[i1 + i] if i1 + i < i2 else None
                    right_content = lines2[j1 + i] if j1 + i < j2 else None
                    side_by_side.append({
                        "type": "replace",
                        "left_line": (i1 + i + 1) if left_content else None,
                        "left_content": left_content,
                        "right_line": (j1 + i + 1) if right_content else None,
                        "right_content": right_content
                    })
            elif tag == 'delete':
                # Lines deleted from left
                for i in range(i1, i2):
                    side_by_side.append({
                        "type": "delete",
                        "left_line": i + 1,
                        "left_content": lines1[i],
                        "right_line": None,
                        "right_content": None
                    })
            elif tag == 'insert':
                # Lines inserted in right
                for i in range(j1, j2):
                    side_by_side.append({
                        "type": "insert",
                        "left_line": None,
                        "left_content": None,
                        "right_line": i + 1,
                        "right_content": lines2[i]
                    })

        stats = DiffService._calculate_diff_stats(lines1, lines2)

        return {
            "format": "side_by_side",
            "comparisons": side_by_side,
            "statistics": stats
        }

    @staticmethod
    def _generate_line_diff(text1: str, text2: str) -> Dict[str, Any]:
        """Generate line-by-line diff with change types"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        differ = difflib.Differ()
        diff = list(differ.compare(lines1, lines2))

        changes = []
        for line in diff:
            if line.startswith('  '):
                changes.append({"type": "equal", "content": line[2:]})
            elif line.startswith('- '):
                changes.append({"type": "delete", "content": line[2:]})
            elif line.startswith('+ '):
                changes.append({"type": "insert", "content": line[2:]})
            elif line.startswith('? '):
                # Hint line showing intra-line differences
                changes.append({"type": "hint", "content": line[2:]})

        stats = DiffService._calculate_diff_stats(lines1, lines2)

        return {
            "format": "lines",
            "changes": changes,
            "statistics": stats
        }

    @staticmethod
    def _generate_word_diff(text1: str, text2: str) -> Dict[str, Any]:
        """Generate word-by-word diff"""
        words1 = text1.split()
        words2 = text2.split()

        matcher = difflib.SequenceMatcher(None, words1, words2)
        opcodes = matcher.get_opcodes()

        changes = []

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                changes.append({
                    "type": "equal",
                    "words": words1[i1:i2]
                })
            elif tag == 'replace':
                changes.append({
                    "type": "replace",
                    "old_words": words1[i1:i2],
                    "new_words": words2[j1:j2]
                })
            elif tag == 'delete':
                changes.append({
                    "type": "delete",
                    "words": words1[i1:i2]
                })
            elif tag == 'insert':
                changes.append({
                    "type": "insert",
                    "words": words2[j1:j2]
                })

        stats = DiffService._calculate_diff_stats(words1, words2)

        return {
            "format": "words",
            "changes": changes,
            "statistics": stats
        }

    @staticmethod
    def _calculate_diff_stats(seq1: List[str], seq2: List[str]) -> Dict[str, Any]:
        """Calculate statistics about the diff"""
        matcher = difflib.SequenceMatcher(None, seq1, seq2)

        # Get operation counts
        added = 0
        deleted = 0
        changed = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                added += j2 - j1
            elif tag == 'delete':
                deleted += i2 - i1
            elif tag == 'replace':
                changed += max(i2 - i1, j2 - j1)

        # Calculate similarity ratio
        similarity = matcher.ratio()

        return {
            "added": added,
            "deleted": deleted,
            "changed": changed,
            "similarity": round(similarity, 4),
            "original_length": len(seq1),
            "new_length": len(seq2),
            "net_change": len(seq2) - len(seq1)
        }

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return round(matcher.ratio(), 4)

    @staticmethod
    def get_change_summary(text1: str, text2: str) -> Dict[str, Any]:
        """
        Get a high-level summary of changes between texts

        Args:
            text1: Original text
            text2: Modified text

        Returns:
            Dictionary with change summary
        """
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        words1 = text1.split()
        words2 = text2.split()

        chars1 = len(text1)
        chars2 = len(text2)

        # Calculate changes
        line_stats = DiffService._calculate_diff_stats(lines1, lines2)
        word_stats = DiffService._calculate_diff_stats(words1, words2)

        return {
            "lines": {
                "added": line_stats["added"],
                "deleted": line_stats["deleted"],
                "changed": line_stats["changed"],
                "total_before": line_stats["original_length"],
                "total_after": line_stats["new_length"]
            },
            "words": {
                "added": word_stats["added"],
                "deleted": word_stats["deleted"],
                "changed": word_stats["changed"],
                "total_before": word_stats["original_length"],
                "total_after": word_stats["new_length"]
            },
            "characters": {
                "before": chars1,
                "after": chars2,
                "net_change": chars2 - chars1
            },
            "similarity": {
                "line_similarity": line_stats["similarity"],
                "word_similarity": word_stats["similarity"],
                "overall_similarity": DiffService.calculate_similarity(text1, text2)
            }
        }

    @staticmethod
    def highlight_changes(text1: str, text2: str) -> Tuple[str, str]:
        """
        Return texts with inline change markers

        Args:
            text1: Original text
            text2: Modified text

        Returns:
            Tuple of (marked_text1, marked_text2) with change markers
        """
        words1 = text1.split()
        words2 = text2.split()

        matcher = difflib.SequenceMatcher(None, words1, words2)

        marked1 = []
        marked2 = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                marked1.extend(words1[i1:i2])
                marked2.extend(words2[j1:j2])
            elif tag == 'replace':
                marked1.extend([f"[-{w}-]" for w in words1[i1:i2]])
                marked2.extend([f"[+{w}+]" for w in words2[j1:j2]])
            elif tag == 'delete':
                marked1.extend([f"[-{w}-]" for w in words1[i1:i2]])
            elif tag == 'insert':
                marked2.extend([f"[+{w}+]" for w in words2[j1:j2]])

        return " ".join(marked1), " ".join(marked2)
