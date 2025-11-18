import re
from pdfminer.high_level import extract_pages, extract_text

text = extract_text("scan.pdf")
print(text)