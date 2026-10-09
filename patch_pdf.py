import re
with open("src/reporting/pdf_exporter.py", "r") as f:
    content = f.read()

replacement = """        for item in result["conclusion"]["opportunities"][:(8 if full else 3)]:text("• "+item)
    if "macro_industry" in selected:
        heading(SECTION_LABELS["macro_industry"])
        text("Vĩ mô: " + result["conclusion"].get("macro", "Chưa có thông tin"))
        text("Ngành: " + result["conclusion"].get("industry", "Chưa có thông tin"))
    if "market" in selected:"""

content = content.replace('        for item in result["conclusion"]["opportunities"][:(8 if full else 3)]:text("• "+item)\n    if "market" in selected:', replacement)

with open("src/reporting/pdf_exporter.py", "w") as f:
    f.write(content)
