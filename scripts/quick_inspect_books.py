"""Quick inspection script for the books folder."""
import sys
from pathlib import Path
import PyPDF2

books_dir = Path(r"C:\Users\WDAGUtilityAccount\Downloads\Nova pasta\darkfactory\livros")
if not books_dir.exists():
    print(f"Directory not found: {books_dir}")
    sys.exit(1)

pdf_files = list(books_dir.glob("*.pdf"))
print(f"Found {len(pdf_files)} PDF files in {books_dir}\n")

for pdf in sorted(pdf_files):
    try:
        reader = PyPDF2.PdfReader(str(pdf))
        num_pages = len(reader.pages)
        title = reader.metadata.title if reader.metadata and reader.metadata.title else pdf.stem
        print(f"OK: {pdf.name[:50]:<50} | Pages: {num_pages:4d} | Title: {str(title)[:30]}")
    except Exception as e:
        print(f"ERR: {pdf.name[:50]:<50} | Error: {e}")
