#!/usr/bin/env python3
"""
Extract text from PDF files.

Usage:
    python extract_text.py <input.pdf> [--output <output.txt>] [--pages 1-5]
"""

import argparse
import sys
from pathlib import Path


def extract_text(pdf_path: str, pages: str = None) -> str:
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        pages: Page range (e.g., "1-5" or "1,3,5").

    Returns:
        Extracted text content.
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return "Error: PyPDF2 not installed. Run: pip install PyPDF2"

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Parse page range
        if pages:
            page_nums = parse_page_range(pages, total_pages)
        else:
            page_nums = range(total_pages)

        # Extract text
        text_parts = []
        for i in page_nums:
            page = reader.pages[i]
            text = page.extract_text()
            text_parts.append(f"--- Page {i + 1} ---\n{text}")

        return "\n\n".join(text_parts)

    except Exception as e:
        return f"Error extracting text: {e}"


def parse_page_range(pages: str, total: int) -> list:
    """Parse page range string into list of page indices."""
    result = []

    for part in pages.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start = int(start) - 1
            end = min(int(end), total)
            result.extend(range(start, end))
        else:
            idx = int(part) - 1
            if 0 <= idx < total:
                result.append(idx)

    return sorted(set(result))


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("--output", "-o", help="Output text file")
    parser.add_argument("--pages", "-p", help="Page range (e.g., 1-5 or 1,3,5)")

    args = parser.parse_args()

    # Check input file
    if not Path(args.input).exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Extract text
    text = extract_text(args.input, args.pages)

    # Output
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Text extracted to: {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
