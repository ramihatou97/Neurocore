"""
PDF Export Service
Converts chapters to professional PDF documents using LaTeX or WeasyPrint
"""

import os
import re
import logging
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import markdown2

# Make WeasyPrint optional (requires GTK+ system libraries on some platforms)
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"WeasyPrint not available: {e}. PDF export via WeasyPrint will not work.")

from backend.services.export.latex_templates import LaTeXTemplates
from backend.database.models.chapter import Chapter

logger = logging.getLogger(__name__)


class PDFExporter:
    """
    Export chapters to PDF using LaTeX or HTML conversion
    """

    def __init__(self):
        self.templates = LaTeXTemplates()

    def export_chapter_to_pdf(
        self,
        chapter: Chapter,
        template: str = "academic",
        include_images: bool = True,
        use_latex: bool = False
    ) -> bytes:
        """
        Export chapter to PDF

        Args:
            chapter: Chapter object to export
            template: Template name (academic, journal, hospital)
            include_images: Whether to include images
            use_latex: Use LaTeX (requires pdflatex) or WeasyPrint (HTML->PDF)

        Returns:
            PDF file as bytes

        Raises:
            RuntimeError: If PDF generation fails
        """
        logger.info(f"Exporting chapter {chapter.id} to PDF (template={template}, use_latex={use_latex})")

        if use_latex:
            return self._export_via_latex(chapter, template, include_images)
        else:
            return self._export_via_weasyprint(chapter, template, include_images)

    def _export_via_latex(
        self,
        chapter: Chapter,
        template: str,
        include_images: bool
    ) -> bytes:
        """
        Export via LaTeX compilation (requires pdflatex installed)

        Args:
            chapter: Chapter to export
            template: Template name
            include_images: Include images

        Returns:
            PDF bytes
        """
        logger.info(f"Exporting chapter {chapter.id} via LaTeX")

        # Get template
        latex_template = self.templates.get_template(template)

        # Prepare template variables
        template_vars = self._prepare_template_vars(chapter, template)

        # Convert sections to LaTeX
        latex_content = self._sections_to_latex(chapter.sections or [], include_images)
        template_vars["content"] = latex_content

        # Generate bibliography
        bibliography = self._generate_latex_bibliography(chapter)
        template_vars["bibliography"] = bibliography

        # Fill template
        latex_document = latex_template % template_vars

        # Compile to PDF
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write .tex file
            tex_file = tmpdir_path / "chapter.tex"
            tex_file.write_text(latex_document, encoding='utf-8')

            # Write bibliography if needed
            if chapter.citations:
                bib_file = tmpdir_path / "references.bib"
                bib_file.write_text(self._generate_bibtex(chapter), encoding='utf-8')

            # Run pdflatex (twice for references)
            for i in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "chapter.tex"],
                    cwd=tmpdir,
                    capture_output=True,
                    timeout=30
                )
                if result.returncode != 0:
                    logger.error(f"pdflatex failed: {result.stderr.decode()}")
                    raise RuntimeError(f"LaTeX compilation failed: {result.stderr.decode()}")

            # Read PDF
            pdf_file = tmpdir_path / "chapter.pdf"
            if not pdf_file.exists():
                raise RuntimeError("PDF file was not generated")

            return pdf_file.read_bytes()

    def _export_via_weasyprint(
        self,
        chapter: Chapter,
        template: str,
        include_images: bool
    ) -> bytes:
        """
        Export via WeasyPrint (HTML to PDF conversion, no LaTeX required)

        Args:
            chapter: Chapter to export
            template: Template name
            include_images: Include images

        Returns:
            PDF bytes

        Raises:
            RuntimeError: If WeasyPrint is not available or PDF generation fails
        """
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError(
                "WeasyPrint is not available. This likely means GTK+ system libraries are not installed. "
                "Please install GTK+ libraries or use use_latex=True for LaTeX-based PDF export."
            )

        logger.info(f"Exporting chapter {chapter.id} via WeasyPrint")

        # Generate HTML content
        html_content = self._generate_html_for_pdf(chapter, template, include_images)

        # CSS styling based on template
        css_styling = self._get_pdf_css(template)

        # Generate PDF
        try:
            pdf = HTML(string=html_content).write_pdf(
                stylesheets=[CSS(string=css_styling)]
            )
            return pdf
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation failed: {e}")
            raise RuntimeError(f"PDF generation failed: {str(e)}")

    def _sections_to_latex(
        self,
        sections: List[Dict[str, Any]],
        include_images: bool
    ) -> str:
        """
        Convert chapter sections to LaTeX format

        Args:
            sections: List of section dictionaries
            include_images: Whether to include images

        Returns:
            LaTeX formatted content
        """
        latex_parts = []

        for i, section in enumerate(sections, 1):
            title = section.get("title", f"Section {i}")
            content = section.get("content", "")

            # Add section heading
            latex_parts.append(f"\\section{{{self._escape_latex(title)}}}")

            # Convert markdown content to LaTeX
            latex_content = self._markdown_to_latex(content, include_images)
            latex_parts.append(latex_content)
            latex_parts.append("")  # Blank line

        return "\n".join(latex_parts)

    def _markdown_to_latex(self, markdown_text: str, include_images: bool) -> str:
        """
        Convert markdown to LaTeX

        Args:
            markdown_text: Markdown content
            include_images: Include images

        Returns:
            LaTeX formatted text
        """
        if not markdown_text:
            return ""

        # Basic conversions
        latex = markdown_text

        # Headers (## -> subsection, ### -> subsubsection)
        latex = re.sub(r'####\s+(.*?)$', r'\\paragraph{\1}', latex, flags=re.MULTILINE)
        latex = re.sub(r'###\s+(.*?)$', r'\\subsubsection{\1}', latex, flags=re.MULTILINE)
        latex = re.sub(r'##\s+(.*?)$', r'\\subsection{\1}', latex, flags=re.MULTILINE)

        # Bold and italic
        latex = re.sub(r'\*\*\*(.*?)\*\*\*', r'\\textbf{\\textit{\1}}', latex)
        latex = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', latex)
        latex = re.sub(r'\*(.*?)\*', r'\\textit{\1}', latex)

        # Inline code
        latex = re.sub(r'`(.*?)`', r'\\texttt{\1}', latex)

        # Citations [1] -> \cite{ref1}
        latex = re.sub(r'\[(\d+)\]', r'\\cite{ref\1}', latex)

        # Unordered lists
        latex = re.sub(r'^\s*[-*]\s+(.*?)$', r'\\item \1', latex, flags=re.MULTILINE)

        # Wrap lists in itemize environment
        latex = re.sub(
            r'((?:\\item .*\n?)+)',
            r'\\begin{itemize}\n\1\\end{itemize}\n',
            latex
        )

        # Tables (basic support for markdown tables)
        latex = self._convert_markdown_tables_to_latex(latex)

        # Images (if enabled)
        if include_images:
            latex = self._convert_markdown_images_to_latex(latex)
        else:
            # Remove image syntax
            latex = re.sub(r'!\[.*?\]\(.*?\)', '', latex)

        # Escape special LaTeX characters (but not in commands we just created)
        # This is tricky - we need to be selective
        latex = self._escape_latex_selective(latex)

        return latex

    def _convert_markdown_tables_to_latex(self, text: str) -> str:
        """Convert markdown tables to LaTeX tabular format"""
        # Simple implementation - handles basic tables
        # More complex tables would need a proper parser

        table_pattern = r'\|(.+)\|\n\|[-:\s|]+\|\n((?:\|.+\|\n?)+)'
        matches = re.finditer(table_pattern, text)

        for match in matches:
            header = match.group(1)
            rows = match.group(2)

            # Parse header
            headers = [h.strip() for h in header.split('|') if h.strip()]
            num_cols = len(headers)

            # Build LaTeX table
            latex_table = f"\\begin{{tabular}}{{{'|'.join(['l'] * num_cols)}}}\n"
            latex_table += "\\toprule\n"
            latex_table += " & ".join(headers) + " \\\\\n"
            latex_table += "\\midrule\n"

            # Parse rows
            for row_line in rows.strip().split('\n'):
                if row_line.strip():
                    cells = [c.strip() for c in row_line.split('|') if c.strip()]
                    latex_table += " & ".join(cells) + " \\\\\n"

            latex_table += "\\bottomrule\n"
            latex_table += "\\end{tabular}\n"

            text = text.replace(match.group(0), latex_table)

        return text

    def _convert_markdown_images_to_latex(self, text: str) -> str:
        """Convert markdown image syntax to LaTeX includegraphics"""
        # ![alt text](image_url)
        image_pattern = r'!\[(.*?)\]\((.*?)\)'

        def replace_image(match):
            alt_text = match.group(1)
            image_url = match.group(2)

            return f"""\\begin{{figure}}[h]
\\centering
\\includegraphics[width=0.8\\textwidth]{{{image_url}}}
\\caption{{{alt_text}}}
\\end{{figure}}
"""

        return re.sub(image_pattern, replace_image, text)

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters"""
        if not text:
            return ""

        # Characters that need escaping in LaTeX
        replacements = {
            '\\': r'\textbackslash{}',
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

    def _escape_latex_selective(self, text: str) -> str:
        """
        Selectively escape LaTeX - don't escape our LaTeX commands
        This is a simplified version - in production you'd want a proper parser
        """
        # For now, we'll assume our markdown_to_latex already handles most escaping
        # This is a placeholder for more sophisticated escaping
        return text

    def _generate_latex_bibliography(self, chapter: Chapter) -> str:
        """Generate LaTeX bibliography section"""
        if not chapter.citations:
            return ""

        bib_items = []
        citations = chapter.citations if isinstance(chapter.citations, list) else []

        for i, citation in enumerate(citations, 1):
            if isinstance(citation, dict):
                authors = citation.get('authors', 'Unknown')
                title = citation.get('title', 'Untitled')
                year = citation.get('year', 'n.d.')
                journal = citation.get('journal', '')

                bib_entry = f"\\bibitem{{ref{i}}} {authors}. {title}. "
                if journal:
                    bib_entry += f"{journal}. "
                bib_entry += f"{year}."

                bib_items.append(bib_entry)

        if bib_items:
            return "\\begin{thebibliography}{99}\n" + "\n".join(bib_items) + "\n\\end{thebibliography}"
        return ""

    def _generate_bibtex(self, chapter: Chapter) -> str:
        """Generate BibTeX file content"""
        # This will be enhanced in Part 5C
        return ""

    def _prepare_template_vars(
        self,
        chapter: Chapter,
        template: str
    ) -> Dict[str, str]:
        """
        Prepare variables for template substitution

        Args:
            chapter: Chapter object
            template: Template name

        Returns:
            Dictionary of template variables
        """
        # Basic variables
        vars_dict = {
            "title": self._escape_latex(chapter.title or "Untitled"),
            "date": datetime.now().strftime("%B %d, %Y"),
            "version": str(chapter.version or "1.0"),
            "summary": self._escape_latex(chapter.summary or "No summary available"),
            "content": "",  # Will be filled later
            "bibliography": "",  # Will be filled later
        }

        # Quality scores
        quality_scores = chapter.quality_scores or {}
        vars_dict["overall_quality"] = f"{quality_scores.get('overall', 0) * 100:.1f}\\% ({quality_scores.get('rating', 'N/A')})"
        vars_dict["depth_score"] = f"{quality_scores.get('depth', 0) * 100:.1f}\\%"
        vars_dict["coverage_score"] = f"{quality_scores.get('coverage', 0) * 100:.1f}\\%"
        vars_dict["currency_score"] = f"{quality_scores.get('currency', 0) * 100:.1f}\\%"
        vars_dict["evidence_score"] = f"{quality_scores.get('evidence', 0) * 100:.1f}\\%"

        # Generation confidence
        gen_conf = chapter.generation_confidence_data or {}
        vars_dict["generation_confidence"] = f"{gen_conf.get('overall', 0) * 100:.1f}\\% ({gen_conf.get('rating', 'N/A')})"

        # Template-specific variables
        if template == "journal":
            vars_dict["short_title"] = self._escape_latex(chapter.title[:50] if chapter.title else "")
            vars_dict["keywords"] = "neurosurgery, clinical practice"  # Could be enhanced

        elif template == "hospital":
            vars_dict["hospital_name"] = "Medical Center"  # Could be configurable
            vars_dict["hospital_address"] = "Department of Neurosurgery"
            vars_dict["hospital_phone"] = "+1-XXX-XXX-XXXX"
            vars_dict["hospital_email"] = "neurosurgery@hospital.edu"
            vars_dict["document_id"] = f"NCK-{chapter.id[:8]}"
            vars_dict["review_status"] = "AI-Generated, Pending Review"
            vars_dict["source_year_range"] = "2015-2025"  # Could calculate from actual sources

        return vars_dict

    def _generate_html_for_pdf(
        self,
        chapter: Chapter,
        template: str,
        include_images: bool
    ) -> str:
        """
        Generate HTML content for PDF conversion

        Args:
            chapter: Chapter object
            template: Template name
            include_images: Include images

        Returns:
            HTML string
        """
        # Convert markdown sections to HTML
        html_sections = []

        for i, section in enumerate(chapter.sections or [], 1):
            title = section.get("title", f"Section {i}")
            content = section.get("content", "")

            # Convert markdown to HTML
            html_content = markdown2.markdown(
                content,
                extras=["tables", "fenced-code-blocks", "break-on-newline"]
            )

            html_sections.append(f"""
                <section>
                    <h2>{title}</h2>
                    {html_content}
                </section>
            """)

        # Quality metrics
        quality_scores = chapter.quality_scores or {}
        gen_conf = chapter.generation_confidence_data or {}

        # Build HTML document
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{chapter.title or 'Untitled'}</title>
        </head>
        <body>
            <div class="title-page">
                <h1>{chapter.title or 'Untitled'}</h1>
                <p class="subtitle">Neurosurgical Core of Knowledge</p>
                <p class="meta">Generated: {datetime.now().strftime("%B %d, %Y")} | Version: {chapter.version or '1.0'}</p>

                <div class="abstract">
                    <h3>Summary</h3>
                    <p>{chapter.summary or 'No summary available'}</p>
                </div>

                <div class="quality-metrics">
                    <h3>Quality Metrics</h3>
                    <ul>
                        <li>Overall Quality: {quality_scores.get('overall', 0) * 100:.1f}% ({quality_scores.get('rating', 'N/A')})</li>
                        <li>Generation Confidence: {gen_conf.get('overall', 0) * 100:.1f}% ({gen_conf.get('rating', 'N/A')})</li>
                        <li>Depth: {quality_scores.get('depth', 0) * 100:.1f}%</li>
                        <li>Coverage: {quality_scores.get('coverage', 0) * 100:.1f}%</li>
                        <li>Currency: {quality_scores.get('currency', 0) * 100:.1f}%</li>
                        <li>Evidence: {quality_scores.get('evidence', 0) * 100:.1f}%</li>
                    </ul>
                </div>
            </div>

            <div class="content">
                {''.join(html_sections)}
            </div>

            <div class="references">
                <h2>References</h2>
                {self._generate_html_bibliography(chapter)}
            </div>
        </body>
        </html>
        """

        return html

    def _generate_html_bibliography(self, chapter: Chapter) -> str:
        """Generate HTML bibliography"""
        if not chapter.citations:
            return "<p>No references</p>"

        citations = chapter.citations if isinstance(chapter.citations, list) else []
        bib_items = []

        for i, citation in enumerate(citations, 1):
            if isinstance(citation, dict):
                authors = citation.get('authors', 'Unknown')
                title = citation.get('title', 'Untitled')
                year = citation.get('year', 'n.d.')
                journal = citation.get('journal', '')

                bib_html = f"<li>[{i}] {authors}. <em>{title}</em>. "
                if journal:
                    bib_html += f"{journal}. "
                bib_html += f"{year}.</li>"

                bib_items.append(bib_html)

        return "<ol>" + "".join(bib_items) + "</ol>"

    def _get_pdf_css(self, template: str) -> str:
        """
        Get CSS styling for PDF export

        Args:
            template: Template name

        Returns:
            CSS string
        """
        base_css = """
        @page {
            size: A4;
            margin: 2.5cm;
        }

        body {
            font-family: 'Times New Roman', Times, serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #000;
        }

        h1 {
            font-size: 24pt;
            font-weight: bold;
            text-align: center;
            margin-bottom: 0.5cm;
        }

        h2 {
            font-size: 16pt;
            font-weight: bold;
            margin-top: 1cm;
            margin-bottom: 0.5cm;
            page-break-after: avoid;
        }

        h3 {
            font-size: 14pt;
            font-weight: bold;
            margin-top: 0.5cm;
            margin-bottom: 0.3cm;
        }

        .title-page {
            page-break-after: always;
            text-align: center;
        }

        .subtitle {
            font-size: 14pt;
            margin-top: 0.5cm;
        }

        .meta {
            font-size: 10pt;
            color: #666;
            margin-top: 0.5cm;
        }

        .abstract {
            margin: 2cm 2cm;
            text-align: left;
            border: 1px solid #ccc;
            padding: 1cm;
            background: #f9f9f9;
        }

        .quality-metrics {
            margin: 1cm 2cm;
            text-align: left;
            border: 1px solid #999;
            padding: 0.5cm;
        }

        .quality-metrics ul {
            list-style-type: none;
            padding-left: 0;
        }

        .quality-metrics li {
            margin: 0.2cm 0;
        }

        .content {
            margin-top: 1cm;
        }

        section {
            margin-bottom: 1cm;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.5cm 0;
        }

        table th, table td {
            border: 1px solid #999;
            padding: 0.3cm;
            text-align: left;
        }

        table th {
            background: #f0f0f0;
            font-weight: bold;
        }

        code {
            font-family: 'Courier New', monospace;
            background: #f5f5f5;
            padding: 0.1cm 0.2cm;
            font-size: 9pt;
        }

        pre {
            background: #f5f5f5;
            padding: 0.5cm;
            overflow-x: auto;
            font-size: 9pt;
        }

        .references {
            margin-top: 2cm;
            page-break-before: always;
        }

        .references ol {
            font-size: 9pt;
            line-height: 1.3;
        }
        """

        return base_css
