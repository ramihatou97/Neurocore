-- Migration: Export Templates and Citation Styles
-- Description: Add support for export templates, citation styles, and export history
-- Date: 2025-10-27

-- ==================== Citation Styles Table ====================

CREATE TABLE IF NOT EXISTS citation_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    format_template JSONB NOT NULL,
    -- Example format_template:
    -- {
    --   "in_text": "{authors} ({year})",
    --   "bibliography": "{authors}. ({year}). {title}. {journal}, {volume}({issue}), {pages}. {doi}",
    --   "author_separator": ", ",
    --   "et_al_threshold": 3
    -- }

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_citation_style_name UNIQUE (name)
);

-- Create index
CREATE INDEX idx_citation_styles_active ON citation_styles(is_active);

-- ==================== Export Templates Table ====================

CREATE TABLE IF NOT EXISTS export_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    format VARCHAR(20) NOT NULL, -- pdf, docx, html

    -- Template content
    template_content TEXT NOT NULL,
    -- For HTML: Jinja2 template
    -- For PDF: HTML template that will be converted
    -- For DOCX: Template structure in JSON

    -- Styling
    styles JSONB DEFAULT '{}',
    -- {
    --   "font_family": "Arial",
    --   "font_size": 12,
    --   "line_height": 1.5,
    --   "margin_top": 1,
    --   "margin_bottom": 1,
    --   "margin_left": 1,
    --   "margin_right": 1,
    --   "header_footer": true,
    --   "page_numbers": true,
    --   "toc": false
    -- }

    -- Template variables
    required_variables JSONB DEFAULT '[]',
    -- ["title", "author", "date", "content", "citations"]

    -- Ownership
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_export_format CHECK (format IN ('pdf', 'docx', 'html'))
);

-- Create indexes
CREATE INDEX idx_export_templates_format ON export_templates(format);
CREATE INDEX idx_export_templates_public ON export_templates(is_public);
CREATE INDEX idx_export_templates_creator ON export_templates(created_by);

-- ==================== Export History Table ====================

CREATE TABLE IF NOT EXISTS export_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_id UUID REFERENCES export_templates(id) ON DELETE SET NULL,
    citation_style_id UUID REFERENCES citation_styles(id) ON DELETE SET NULL,

    -- Export details
    export_format VARCHAR(20) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size BIGINT,
    file_path TEXT, -- Storage path if files are kept

    -- Options used
    export_options JSONB DEFAULT '{}',
    -- {
    --   "include_toc": true,
    --   "include_images": true,
    --   "include_citations": true,
    --   "page_size": "A4",
    --   "orientation": "portrait"
    -- }

    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_export_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Create indexes
CREATE INDEX idx_export_history_chapter ON export_history(chapter_id);
CREATE INDEX idx_export_history_user ON export_history(user_id);
CREATE INDEX idx_export_history_status ON export_history(status);
CREATE INDEX idx_export_history_created ON export_history(created_at DESC);

-- ==================== Default Citation Styles ====================

-- APA 7th Edition
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('apa', 'APA 7th Edition', 'American Psychological Association 7th edition style',
'{
  "in_text": {
    "one_author": "({author}, {year})",
    "two_authors": "({author1} & {author2}, {year})",
    "multiple": "({first_author} et al., {year})"
  },
  "bibliography": "{authors}. ({year}). {title}. {journal}, {volume}({issue}), {pages}. https://doi.org/{doi}",
  "author_separator": ", & ",
  "et_al_threshold": 3,
  "sort_by": "author"
}'::jsonb);

-- MLA 9th Edition
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('mla', 'MLA 9th Edition', 'Modern Language Association 9th edition style',
'{
  "in_text": {
    "one_author": "({author} {page})",
    "two_authors": "({author1} and {author2} {page})",
    "multiple": "({first_author} et al. {page})"
  },
  "bibliography": "{authors}. \"{title}.\" {journal}, vol. {volume}, no. {issue}, {year}, pp. {pages}.",
  "author_separator": ", and ",
  "et_al_threshold": 3,
  "sort_by": "author"
}'::jsonb);

-- Chicago 17th Edition
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('chicago', 'Chicago 17th Edition', 'Chicago Manual of Style 17th edition',
'{
  "in_text": {
    "one_author": "({author} {year}, {page})",
    "two_authors": "({author1} and {author2} {year}, {page})",
    "multiple": "({first_author} et al. {year}, {page})"
  },
  "bibliography": "{authors}. {year}. \"{title}.\" {journal} {volume} ({issue}): {pages}. https://doi.org/{doi}.",
  "author_separator": ", and ",
  "et_al_threshold": 4,
  "sort_by": "author"
}'::jsonb);

-- Vancouver
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('vancouver', 'Vancouver', 'Vancouver citation style for medical journals',
'{
  "in_text": {
    "format": "[{number}]"
  },
  "bibliography": "{authors}. {title}. {journal}. {year};{volume}({issue}):{pages}. doi:{doi}",
  "author_separator": ", ",
  "et_al_threshold": 6,
  "sort_by": "appearance",
  "numbered": true
}'::jsonb);

-- ==================== Default Export Templates ====================

-- Default PDF Template
INSERT INTO export_templates (name, description, format, template_content, styles, required_variables, is_default, is_public)
VALUES (
    'Academic Paper (PDF)',
    'Professional academic paper template with header, footer, and citations',
    'pdf',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        @page {
            size: {{ page_size|default("A4") }};
            margin: {{ margin_top|default("2.5cm") }} {{ margin_right|default("2.5cm") }}
                    {{ margin_bottom|default("2.5cm") }} {{ margin_left|default("2.5cm") }};
            @top-right {
                content: "{{ title|truncate(50) }}";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
            }
        }
        body {
            font-family: {{ font_family|default("Times New Roman") }}, serif;
            font-size: {{ font_size|default("12pt") }};
            line-height: {{ line_height|default("1.5") }};
            color: #333;
        }
        h1 {
            font-size: 20pt;
            text-align: center;
            margin-bottom: 0.5em;
        }
        .metadata {
            text-align: center;
            margin-bottom: 2em;
            color: #666;
        }
        .content {
            text-align: justify;
        }
        .citation {
            margin-left: 2em;
            text-indent: -2em;
            margin-bottom: 0.5em;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="metadata">
        <p>{{ author_name }}<br>{{ date }}</p>
    </div>
    <div class="content">
        {{ content|safe }}
    </div>
    {% if bibliography %}
    <h2>References</h2>
    <div class="bibliography">
        {% for citation in bibliography %}
        <div class="citation">{{ citation|safe }}</div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>',
    '{"page_size": "A4", "font_family": "Times New Roman", "font_size": "12pt", "line_height": "1.5", "margins": {"top": "2.5cm", "bottom": "2.5cm", "left": "2.5cm", "right": "2.5cm"}}',
    '["title", "author_name", "date", "content"]',
    true,
    true
);

-- Default HTML Template
INSERT INTO export_templates (name, description, format, template_content, styles, required_variables, is_default, is_public)
VALUES (
    'Web Article (HTML)',
    'Clean web article template with responsive design',
    'html',
    '<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: {{ font_family|default("Georgia") }}, serif;
            font-size: {{ font_size|default("16px") }};
            line-height: {{ line_height|default("1.6") }};
            color: #333;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 0.2em;
        }
        .metadata {
            color: #666;
            margin-bottom: 2em;
            padding-bottom: 1em;
            border-bottom: 1px solid #ddd;
        }
        .content img {
            max-width: 100%;
            height: auto;
        }
        .bibliography {
            margin-top: 3em;
            padding-top: 2em;
            border-top: 2px solid #333;
        }
        .citation {
            margin-bottom: 1em;
        }
    </style>
</head>
<body>
    <article>
        <header>
            <h1>{{ title }}</h1>
            <div class="metadata">
                <p>By {{ author_name }} | {{ date }}</p>
            </div>
        </header>
        <div class="content">
            {{ content|safe }}
        </div>
        {% if bibliography %}
        <section class="bibliography">
            <h2>References</h2>
            {% for citation in bibliography %}
            <div class="citation">{{ citation|safe }}</div>
            {% endfor %}
        </section>
        {% endif %}
    </article>
</body>
</html>',
    '{"font_family": "Georgia", "font_size": "16px", "line_height": "1.6", "max_width": "800px"}',
    '["title", "author_name", "date", "content"]',
    true,
    true
);

-- ==================== Helper Functions ====================

-- Function to get default template for format
CREATE OR REPLACE FUNCTION get_default_template(export_format VARCHAR)
RETURNS UUID AS $$
DECLARE
    template_id UUID;
BEGIN
    SELECT id INTO template_id
    FROM export_templates
    WHERE format = export_format
      AND is_default = true
      AND is_public = true
    LIMIT 1;

    RETURN template_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get export statistics for user
CREATE OR REPLACE FUNCTION get_user_export_stats(user_uuid UUID)
RETURNS TABLE (
    total_exports BIGINT,
    pdf_exports BIGINT,
    docx_exports BIGINT,
    html_exports BIGINT,
    last_export_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) AS total_exports,
        COUNT(*) FILTER (WHERE export_format = 'pdf') AS pdf_exports,
        COUNT(*) FILTER (WHERE export_format = 'docx') AS docx_exports,
        COUNT(*) FILTER (WHERE export_format = 'html') AS html_exports,
        MAX(created_at) AS last_export_date
    FROM export_history
    WHERE user_id = user_uuid
      AND status = 'completed';
END;
$$ LANGUAGE plpgsql;

-- ==================== Indexes for Performance ====================

-- Composite index for user export history
CREATE INDEX idx_export_history_user_status_date
ON export_history(user_id, status, created_at DESC);

-- Index for finding popular templates
CREATE INDEX idx_export_history_template
ON export_history(template_id)
WHERE status = 'completed';

-- ==================== Rollback Script ====================

/*
-- To rollback this migration:

DROP FUNCTION IF EXISTS get_user_export_stats(UUID);
DROP FUNCTION IF EXISTS get_default_template(VARCHAR);

DROP TABLE IF EXISTS export_history;
DROP TABLE IF EXISTS export_templates;
DROP TABLE IF EXISTS citation_styles;
*/
