"""
BibTeX Export Service
Converts chapter citations to BibTeX format for reference managers
"""

import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

from backend.database.models.chapter import Chapter

logger = logging.getLogger(__name__)


class BibTeXExporter:
    """
    Export chapter citations to BibTeX format
    """

    def __init__(self):
        self.citation_styles = {
            "apa": self._format_apa,
            "vancouver": self._format_vancouver,
            "chicago": self._format_chicago
        }

    def export_chapter_citations(
        self,
        chapter: Chapter,
        style: str = "apa"
    ) -> str:
        """
        Export chapter citations as BibTeX

        Args:
            chapter: Chapter object
            style: Citation style (apa, vancouver, chicago) - currently affects formatting

        Returns:
            BibTeX formatted string
        """
        logger.info(f"Exporting citations for chapter {chapter.id} to BibTeX (style={style})")

        if not chapter.citations:
            logger.warning(f"Chapter {chapter.id} has no citations")
            return f"% No citations found for chapter: {chapter.title}\n"

        citations = chapter.citations if isinstance(chapter.citations, list) else []

        bibtex_entries = []

        # Add header comment
        bibtex_entries.append(f"% BibTeX entries for: {chapter.title}")
        bibtex_entries.append(f"% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        bibtex_entries.append(f"% Total citations: {len(citations)}")
        bibtex_entries.append("")

        for i, citation in enumerate(citations, 1):
            if isinstance(citation, dict):
                bibtex_entry = self._create_bibtex_entry(citation, i, chapter.id)
                if bibtex_entry:
                    bibtex_entries.append(bibtex_entry)
                    bibtex_entries.append("")  # Blank line between entries

        return "\n".join(bibtex_entries)

    def _create_bibtex_entry(
        self,
        citation: Dict,
        index: int,
        chapter_id: str
    ) -> Optional[str]:
        """
        Create a single BibTeX entry from citation data

        Args:
            citation: Citation dictionary
            index: Citation number
            chapter_id: Chapter ID for generating unique keys

        Returns:
            BibTeX formatted entry string
        """
        # Extract citation fields
        authors = citation.get('authors', 'Unknown')
        title = citation.get('title', 'Untitled')
        year = citation.get('year', 'n.d.')
        journal = citation.get('journal', '')
        volume = citation.get('volume', '')
        pages = citation.get('pages', '')
        doi = citation.get('doi', '')
        pmid = citation.get('pmid', '')
        url = citation.get('url', '')
        publisher = citation.get('publisher', '')
        book_title = citation.get('book_title', '')
        editors = citation.get('editors', '')
        edition = citation.get('edition', '')

        # Determine entry type
        entry_type = self._determine_entry_type(citation)

        # Generate citation key
        cite_key = self._generate_cite_key(authors, year, index, chapter_id)

        # Build BibTeX entry
        lines = [f"@{entry_type}{{{cite_key},"]

        # Add fields
        if authors and authors != 'Unknown':
            lines.append(f"  author = {{{self._format_authors(authors)}}},")

        if title and title != 'Untitled':
            lines.append(f"  title = {{{self._escape_bibtex(title)}}},")

        if journal:
            lines.append(f"  journal = {{{self._escape_bibtex(journal)}}},")

        if book_title:
            lines.append(f"  booktitle = {{{self._escape_bibtex(book_title)}}},")

        if editors:
            lines.append(f"  editor = {{{self._format_authors(editors)}}},")

        if year and year != 'n.d.':
            lines.append(f"  year = {{{year}}},")

        if volume:
            lines.append(f"  volume = {{{volume}}},")

        if pages:
            lines.append(f"  pages = {{{pages}}},")

        if edition:
            lines.append(f"  edition = {{{edition}}},")

        if publisher:
            lines.append(f"  publisher = {{{publisher}}},")

        if doi:
            lines.append(f"  doi = {{{doi}}},")

        if pmid:
            lines.append(f"  note = {{PMID: {pmid}}},")

        if url:
            lines.append(f"  url = {{{url}}},")

        # Remove trailing comma from last field
        if lines[-1].endswith(','):
            lines[-1] = lines[-1][:-1]

        lines.append("}")

        return "\n".join(lines)

    def _determine_entry_type(self, citation: Dict) -> str:
        """
        Determine BibTeX entry type based on citation fields

        Args:
            citation: Citation dictionary

        Returns:
            BibTeX entry type (article, book, inbook, etc.)
        """
        if citation.get('journal'):
            return "article"
        elif citation.get('book_title'):
            return "inbook"
        elif citation.get('publisher') and not citation.get('journal'):
            return "book"
        elif citation.get('conference'):
            return "inproceedings"
        else:
            # Default to article for medical literature
            return "article"

    def _generate_cite_key(
        self,
        authors: str,
        year: str,
        index: int,
        chapter_id: str
    ) -> str:
        """
        Generate unique BibTeX citation key

        Args:
            authors: Author string
            year: Publication year
            index: Citation index
            chapter_id: Chapter ID

        Returns:
            Citation key (e.g., "Smith2020_1")
        """
        # Extract first author's last name
        if authors and authors != 'Unknown':
            # Handle various author formats
            # "Smith J, Doe A" -> "Smith"
            # "Smith, J. and Doe, A." -> "Smith"
            # "John Smith" -> "Smith"
            first_author = authors.split(',')[0].split(' and ')[0].strip()

            # Get last name
            parts = first_author.split()
            if len(parts) > 1:
                last_name = parts[-1]  # Assume last part is last name
            else:
                last_name = parts[0]

            # Clean last name
            last_name = re.sub(r'[^a-zA-Z]', '', last_name)
        else:
            last_name = "Unknown"

        # Clean year
        year_str = str(year) if year and year != 'n.d.' else "NoDate"
        year_str = re.sub(r'[^0-9]', '', year_str)[:4]  # Take first 4 digits

        # Generate key
        cite_key = f"{last_name}{year_str}_{index}"

        return cite_key

    def _format_authors(self, authors: str) -> str:
        """
        Format authors for BibTeX

        Args:
            authors: Author string

        Returns:
            BibTeX formatted author string
        """
        if not authors or authors == 'Unknown':
            return 'Unknown'

        # If already in "LastName, FirstName" format with " and " separators, return as is
        if ' and ' in authors and ',' in authors:
            return authors

        # Try to convert "Smith J, Doe A" -> "Smith, J. and Doe, A."
        # Or "John Smith, Alice Doe" -> "Smith, John and Doe, Alice"

        # Split by comma or semicolon
        author_list = re.split(r'[,;]', authors)
        formatted_authors = []

        for author in author_list:
            author = author.strip()
            if not author:
                continue

            # Check if already in "Last, First" format
            if ',' in author:
                formatted_authors.append(author)
            else:
                # Assume "First Last" or "First Middle Last" format
                parts = author.split()
                if len(parts) >= 2:
                    # Last name is last part, everything else is first/middle
                    last = parts[-1]
                    first = ' '.join(parts[:-1])
                    formatted_authors.append(f"{last}, {first}")
                else:
                    formatted_authors.append(author)

        return " and ".join(formatted_authors)

    def _escape_bibtex(self, text: str) -> str:
        """
        Escape special characters for BibTeX

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        if not text:
            return ""

        # BibTeX special characters
        replacements = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    def _format_apa(self, citation: Dict) -> str:
        """
        Format citation in APA style (for future use)

        Args:
            citation: Citation dictionary

        Returns:
            APA formatted citation string
        """
        # Future enhancement: generate APA-style plain text citation
        pass

    def _format_vancouver(self, citation: Dict) -> str:
        """
        Format citation in Vancouver style (for future use)

        Args:
            citation: Citation dictionary

        Returns:
            Vancouver formatted citation string
        """
        # Future enhancement: generate Vancouver-style plain text citation
        pass

    def _format_chicago(self, citation: Dict) -> str:
        """
        Format citation in Chicago style (for future use)

        Args:
            citation: Citation dictionary

        Returns:
            Chicago formatted citation string
        """
        # Future enhancement: generate Chicago-style plain text citation
        pass

    def export_as_ris(self, chapter: Chapter) -> str:
        """
        Export citations as RIS format (Research Information Systems)

        This is an alternative format supported by many reference managers.

        Args:
            chapter: Chapter object

        Returns:
            RIS formatted string
        """
        logger.info(f"Exporting citations for chapter {chapter.id} to RIS format")

        if not chapter.citations:
            return ""

        citations = chapter.citations if isinstance(chapter.citations, list) else []

        ris_entries = []

        for citation in citations:
            if isinstance(citation, dict):
                ris_entry = self._create_ris_entry(citation)
                if ris_entry:
                    ris_entries.append(ris_entry)
                    ris_entries.append("")  # Blank line between entries

        return "\n".join(ris_entries)

    def _create_ris_entry(self, citation: Dict) -> str:
        """
        Create RIS format entry

        Args:
            citation: Citation dictionary

        Returns:
            RIS formatted string
        """
        lines = []

        # Type of reference
        if citation.get('journal'):
            lines.append("TY  - JOUR")  # Journal article
        else:
            lines.append("TY  - BOOK")

        # Authors
        authors = citation.get('authors', '')
        if authors:
            author_list = re.split(r'[,;]', authors)
            for author in author_list:
                if author.strip():
                    lines.append(f"AU  - {author.strip()}")

        # Title
        title = citation.get('title', '')
        if title:
            lines.append(f"TI  - {title}")

        # Journal
        journal = citation.get('journal', '')
        if journal:
            lines.append(f"JO  - {journal}")

        # Year
        year = citation.get('year', '')
        if year and year != 'n.d.':
            lines.append(f"PY  - {year}")

        # Volume
        volume = citation.get('volume', '')
        if volume:
            lines.append(f"VL  - {volume}")

        # Pages
        pages = citation.get('pages', '')
        if pages:
            lines.append(f"SP  - {pages}")

        # DOI
        doi = citation.get('doi', '')
        if doi:
            lines.append(f"DO  - {doi}")

        # URL
        url = citation.get('url', '')
        if url:
            lines.append(f"UR  - {url}")

        # End of reference
        lines.append("ER  - ")

        return "\n".join(lines)
