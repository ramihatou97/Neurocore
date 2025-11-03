"""
LaTeX Templates for Chapter Export
Provides multiple professional templates for PDF generation
"""

from typing import Dict

class LaTeXTemplates:
    """Professional LaTeX templates for neurosurgical chapters"""

    @staticmethod
    def get_template(template_name: str = "academic") -> str:
        """Get LaTeX template by name"""
        templates = {
            "academic": LaTeXTemplates.academic_template(),
            "journal": LaTeXTemplates.journal_template(),
            "hospital": LaTeXTemplates.hospital_template()
        }
        return templates.get(template_name, LaTeXTemplates.academic_template())

    @staticmethod
    def academic_template() -> str:
        """Standard academic paper template"""
        return r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{cite}
\usepackage{amsmath}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{times}
\usepackage{setspace}
\usepackage{booktabs}
\usepackage{longtable}

% Page geometry
\geometry{
    a4paper,
    left=2.5cm,
    right=2.5cm,
    top=2.5cm,
    bottom=2.5cm
}

% Header and footer
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\leftmark}
\fancyhead[R]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% Hyperlink setup
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,
    urlcolor=cyan,
    citecolor=blue,
    pdftitle={%(title)s},
    pdfauthor={Neurosurgical Core of Knowledge},
}

% Spacing
\onehalfspacing

\begin{document}

% Title page
\begin{titlepage}
    \centering
    \vspace*{2cm}

    {\Huge\bfseries %(title)s\par}
    \vspace{1cm}

    {\Large Neurosurgical Core of Knowledge\par}
    \vspace{0.5cm}

    {\large Generated: %(date)s\par}
    \vspace{0.5cm}

    {\large Version: %(version)s\par}
    \vspace{2cm}

    \begin{abstract}
        %(summary)s
    \end{abstract}

    \vfill

    {\small AI-generated chapter with expert curation\par}
\end{titlepage}

% Table of contents
\tableofcontents
\newpage

% Quality metrics box
\begin{center}
\fbox{\begin{minipage}{0.9\textwidth}
    \textbf{Quality Metrics:}
    \begin{itemize}
        \item Overall Quality: %(overall_quality)s
        \item Generation Confidence: %(generation_confidence)s
        \item Depth Score: %(depth_score)s
        \item Coverage Score: %(coverage_score)s
        \item Currency Score: %(currency_score)s
        \item Evidence Score: %(evidence_score)s
    \end{itemize}
\end{minipage}}
\end{center}
\vspace{1cm}

% Main content
%(content)s

% Bibliography
\newpage
\bibliographystyle{plain}
\bibliography{references}

% Or if using inline bibliography
%(bibliography)s

\end{document}
"""

    @staticmethod
    def journal_template() -> str:
        """Medical journal submission template"""
        return r"""\documentclass[12pt,a4paper,twocolumn]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{natbib}
\usepackage{amsmath}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{times}
\usepackage{setspace}
\usepackage{booktabs}
\usepackage{longtable}

% Journal-style page geometry
\geometry{
    a4paper,
    left=2cm,
    right=2cm,
    top=2cm,
    bottom=2cm
}

% Running title
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textit{%(short_title)s}}
\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% Hyperlink setup
\hypersetup{
    colorlinks=true,
    linkcolor=black,
    filecolor=black,
    urlcolor=black,
    citecolor=black,
    pdftitle={%(title)s},
}

% Double spacing for review
\doublespacing

\begin{document}

% Title
\twocolumn[
\begin{@twocolumnfalse}
\begin{center}
    {\LARGE\bfseries %(title)s\par}
    \vspace{0.5cm}

    {\large Neurosurgical Core of Knowledge Consortium\par}
    \vspace{0.3cm}

    {\small Generated: %(date)s $\vert$ Version: %(version)s\par}
    \vspace{1cm}

    \begin{minipage}{0.9\textwidth}
        \textbf{Abstract}

        %(summary)s

        \vspace{0.5cm}
        \textbf{Keywords:} %(keywords)s
    \end{minipage}
\end{center}
\vspace{1cm}
\end{@twocolumnfalse}
]

% Main content
%(content)s

% References
\bibliographystyle{vancouver}
\bibliography{references}

%(bibliography)s

\end{document}
"""

    @staticmethod
    def hospital_template() -> str:
        """Hospital letterhead template"""
        return r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{cite}
\usepackage{amsmath}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{times}
\usepackage{setspace}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{xcolor}

% Page geometry with letterhead space
\geometry{
    a4paper,
    left=2.5cm,
    right=2.5cm,
    top=4cm,
    bottom=2.5cm
}

% Custom header for letterhead
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{
    \begin{minipage}{0.6\textwidth}
        \includegraphics[height=1.5cm]{hospital_logo.png}
    \end{minipage}
}
\fancyhead[R]{
    \begin{minipage}{0.35\textwidth}
        \raggedleft
        \small
        \textbf{%(hospital_name)s}\\
        Department of Neurosurgery\\
        %(hospital_address)s
    \end{minipage}
}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}

% First page header
\fancypagestyle{firstpage}{
    \fancyhf{}
    \fancyhead[L]{
        \begin{minipage}{0.6\textwidth}
            \includegraphics[height=2cm]{hospital_logo.png}
        \end{minipage}
    }
    \fancyhead[R]{
        \begin{minipage}{0.35\textwidth}
            \raggedleft
            \textbf{\large %(hospital_name)s}\\
            \textbf{Department of Neurosurgery}\\
            \vspace{0.2cm}
            %(hospital_address)s\\
            Tel: %(hospital_phone)s\\
            Email: %(hospital_email)s
        \end{minipage}
    }
    \fancyfoot[C]{\thepage}
    \renewcommand{\headrulewidth}{0.4pt}
    \renewcommand{\footrulewidth}{0.4pt}
}

% Hyperlink setup
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,
    urlcolor=cyan,
    citecolor=blue,
    pdftitle={%(title)s},
}

% Spacing
\onehalfspacing

\begin{document}
\thispagestyle{firstpage}

% Document header
\vspace{1cm}
\begin{center}
    {\LARGE\bfseries %(title)s\par}
    \vspace{0.5cm}

    {\large Clinical Reference Document\par}
    \vspace{0.3cm}

    {\normalsize Document ID: %(document_id)s $\vert$ Generated: %(date)s\par}
    \vspace{0.3cm}

    {\normalsize Version: %(version)s $\vert$ Confidential - Internal Use Only\par}
\end{center}

\vspace{0.5cm}

% Summary box
\begin{center}
\colorbox{gray!10}{\begin{minipage}{0.9\textwidth}
    \vspace{0.3cm}
    \textbf{Clinical Summary}

    %(summary)s
    \vspace{0.3cm}
\end{minipage}}
\end{center}

\vspace{0.5cm}

% Quality and Confidence Metrics
\begin{center}
\fbox{\begin{minipage}{0.9\textwidth}
    \small
    \textbf{Document Quality Assurance:}
    \begin{itemize}
        \item Overall Quality Rating: %(overall_quality)s
        \item Generation Confidence: %(generation_confidence)s (AI-powered QA)
        \item Medical Evidence Level: %(evidence_score)s
        \item Literature Currency: %(currency_score)s (%(source_year_range)s)
        \item Review Status: %(review_status)s
    \end{itemize}
\end{minipage}}
\end{center}

\vspace{1cm}

% Main content
%(content)s

% References
\newpage
\section*{References}
%(bibliography)s

% Footer disclaimer
\vspace{2cm}
\begin{center}
\colorbox{yellow!20}{\begin{minipage}{0.9\textwidth}
    \small\centering
    \textbf{Disclaimer:} This document was generated using AI-powered medical literature synthesis with expert oversight.
    All clinical decisions should be made based on individual patient assessment and current clinical guidelines.
    Last reviewed: %(date)s
\end{minipage}}
\end{center}

\end{document}
"""

    @staticmethod
    def get_template_vars() -> Dict[str, str]:
        """
        Get available template variables

        Returns:
            Dictionary of variable names and descriptions
        """
        return {
            # Common to all templates
            "title": "Chapter title",
            "date": "Generation date",
            "version": "Chapter version",
            "summary": "Chapter summary/abstract",
            "content": "Main chapter content",
            "bibliography": "Bibliography section",

            # Quality metrics
            "overall_quality": "Overall quality score and rating",
            "generation_confidence": "Generation confidence score and rating",
            "depth_score": "Content depth score",
            "coverage_score": "Topic coverage score",
            "currency_score": "Literature currency score",
            "evidence_score": "Evidence strength score",

            # Journal-specific
            "short_title": "Short running title (journal)",
            "keywords": "Keywords for indexing (journal)",

            # Hospital-specific
            "hospital_name": "Hospital/Institution name",
            "hospital_address": "Hospital address",
            "hospital_phone": "Hospital phone number",
            "hospital_email": "Hospital email",
            "document_id": "Internal document ID",
            "review_status": "Review/approval status",
            "source_year_range": "Year range of cited sources"
        }
