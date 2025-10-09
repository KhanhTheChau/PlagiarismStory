# code here

import fitz  

doc = fitz.open("") # Open a PDF file

extracted_text = ""

for page in doc:
    extracted_text += page.get_text() + "\n"

print(extracted_text)

with open("output.txt", "w", encoding="utf-8") as f:
    f.write(extracted_text)

doc.close()