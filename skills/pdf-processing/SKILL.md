---
name: pdf-processing
description: >
  Extract text, tables, and metadata from PDF files. Process, analyze, merge,
  split, or convert PDF documents. Use when user mentions .pdf files,
  "extract from PDF", "parse PDF", "read PDF content", "analyze PDF",
  "merge PDFs", "split PDF", or any PDF-related document processing tasks.
license: Apache-2.0
allowed-tools:
  - python-executor
metadata:
  dependencies:
    - PyPDF2
    - pdfplumber
  file_types:
    - .pdf
---

# PDF Processing Skill

Comprehensive toolkit for PDF document manipulation and analysis.

## Capabilities

1. **Text Extraction** - Extract all text content from PDF pages
2. **Table Extraction** - Extract tables and structured data
3. **Metadata Access** - Read PDF properties (author, title, pages)
4. **Page Operations** - Split, merge, rotate, extract pages
5. **Content Analysis** - Analyze document structure and content

## Usage Guide

### Extract Text

To extract text from a PDF:

1. Load the PDF file
2. Iterate through pages
3. Extract text from each page
4. Combine and clean the output

**Example approach**:
```python
# Using PyPDF2
from PyPDF2 import PdfReader

reader = PdfReader("document.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text()
```

### Extract Tables

For table extraction, pdfplumber provides better results:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            # Process table data
            pass
```

### Get Metadata

```python
from PyPDF2 import PdfReader

reader = PdfReader("document.pdf")
info = reader.metadata
print(f"Title: {info.title}")
print(f"Author: {info.author}")
print(f"Pages: {len(reader.pages)}")
```

### Merge PDFs

```python
from PyPDF2 import PdfMerger

merger = PdfMerger()
merger.append("file1.pdf")
merger.append("file2.pdf")
merger.write("merged.pdf")
merger.close()
```

### Split PDF

```python
from PyPDF2 import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as f:
        writer.write(f)
```

## Output Formats

When extracting content, provide output in these formats:

### Text Output
```
Page 1:
[Text content...]

Page 2:
[Text content...]
```

### Table Output (Markdown)
```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
```

### Metadata Output
```yaml
title: Document Title
author: Author Name
pages: 10
created: 2024-01-01
modified: 2024-01-15
```

## Best Practices

1. **Large Files**: Process page by page for large PDFs
2. **Scanned PDFs**: Note that scanned PDFs need OCR (not covered here)
3. **Encoding**: Handle text encoding issues gracefully
4. **Tables**: Verify table extraction accuracy manually
5. **Error Handling**: Always handle corrupted/password-protected PDFs

## Limitations

- Cannot process password-protected PDFs without the password
- Scanned PDFs require OCR (separate tool needed)
- Complex layouts may not extract perfectly
- Some fonts may cause character encoding issues
