#!/usr/bin/env python3
"""Generate PDF from markdown using weasyprint"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path

# Read markdown
md_content = Path("AI-Agent-Liability-Shield.md").read_text()

# Convert to HTML with extensions
html_content = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'toc']
)

# Add CSS styling
css_style = """
@page {
    size: Letter;
    margin: 1in;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #666;
    }
}

body {
    font-family: 'Helvetica', 'Arial', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
}

h1 {
    font-size: 24pt;
    color: #1a1a1a;
    border-bottom: 3px solid #0066cc;
    padding-bottom: 10px;
    margin-top: 30px;
    page-break-before: always;
}

h1:first-of-type {
    page-break-before: avoid;
    font-size: 32pt;
    text-align: center;
    border-bottom: none;
}

h2 {
    font-size: 18pt;
    color: #0066cc;
    margin-top: 25px;
    border-bottom: 1px solid #ccc;
    padding-bottom: 5px;
}

h3 {
    font-size: 14pt;
    color: #333;
    margin-top: 20px;
}

h4 {
    font-size: 12pt;
    color: #666;
    margin-top: 15px;
}

code {
    background-color: #f5f5f5;
    padding: 2px 6px;
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    border-radius: 3px;
}

pre {
    background-color: #f5f5f5;
    padding: 15px;
    border-left: 4px solid #0066cc;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.4;
}

pre code {
    background-color: transparent;
    padding: 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 10pt;
}

th {
    background-color: #0066cc;
    color: white;
    padding: 10px;
    text-align: left;
    font-weight: bold;
}

td {
    padding: 8px;
    border: 1px solid #ddd;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

blockquote {
    border-left: 4px solid #0066cc;
    padding-left: 15px;
    margin-left: 0;
    color: #666;
    font-style: italic;
}

strong {
    color: #000;
}

a {
    color: #0066cc;
    text-decoration: none;
}

hr {
    border: none;
    border-top: 2px solid #ccc;
    margin: 30px 0;
}

.toc {
    background-color: #f9f9f9;
    padding: 20px;
    border: 1px solid #ddd;
    margin: 20px 0;
}
"""

# Wrap in full HTML document
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AI Agent Liability Shield - SOC2 Compliance Guide</title>
</head>
<body>
{html_content}
</body>
</html>
"""

# Generate PDF
HTML(string=full_html).write_pdf(
    'AI-Agent-Liability-Shield.pdf',
    stylesheets=[CSS(string=css_style)]
)

print("✅ PDF generated: AI-Agent-Liability-Shield.pdf")
