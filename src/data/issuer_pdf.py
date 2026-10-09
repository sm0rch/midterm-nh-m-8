"""Extract the latest HPG reviewed interim statement; preserve OCR evidence and checks."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata

from src.data.providers import DataSourceError


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d")) if unicodedata.category(c) != "Mn")


def amounts(line):
    values = re.findall(r"\(?\d{1,3}(?:[.,]\s*\d{3}){2,}\)?", line)
    return [(-1 if value.startswith("(") else 1) * int(re.sub(r"\D", "", value)) for value in values]


def parse_interim_text(pages: list[dict], source_id: str, published_at: str) -> dict:
    patterns = {"revenue": "doanh thu thuan ve ban hang", "gross_profit": "loi nhuan gop ve ban hang",
                "net_profit": "18. loi nhuan sau thue thu nhap", "parent_profit": "18.1 loi nhuan sau thue",
                "cfo": "luu chuyen tien thuan tu hoat dong kinh", "assets": "tong cong tai san",
                "equity": "d. von chu so huu", "liabilities": "c. no",
                "short_debt": "vay va no thue tai chinh ngan", "long_debt": "vay va no thue tai chinh dai",
                "non_controlling_equity": "loi ich cua co dong khong kiem soat"}
    found, period = {}, None
    for page in pages:
        text = fold(page["text"])
        if "bao cao" not in text or "vnd" not in text:
            continue
        match = re.search(r"ket thuc ngay\s+(\d+)\s+thang\s+(\d+)\s+nam\s+(\d{4})", text)
        if match:
            period = date(int(match[3]), int(match[2]), int(match[1])).isoformat()
        # Restrict to statement pages, not notes with unrelated comparative columns.
        if "thuyet minh bao cao" in text[:600]:
            continue
        for line in page["text"].splitlines():
            normalized = re.sub(r"\s+", " ", fold(line))
            for key, pattern in patterns.items():
                # OCR can join words and lose punctuation; normalize both for matching.
                compact = re.sub(r"[^a-z0-9]", "", normalized)
                if re.sub(r"[^a-z0-9]", "", pattern) in compact and key not in found:
                    pair = amounts(line)
                    if len(pair) >= 2:
                        found[key] = {"value": pair[0], "previous": pair[1], "unit": "VND",
                                      "source_id": source_id, "page": page["page"], "ocr_line": line,
                                      "published_at": published_at, "statement_scope": "consolidated"}
    checks = []
    if all(k in found for k in ["assets", "liabilities", "equity"]):
        deviation = abs(found["assets"]["value"] - found["liabilities"]["value"] - found["equity"]["value"])
        checks.append({"name": "assets=liabilities+equity", "valid": deviation / found["assets"]["value"] < 0.0001})
    valid = period is not None and all(k in found for k in ["revenue", "net_profit", "cfo"]) and bool(checks) and all(c["valid"] for c in checks)
    for field in found.values():
        field["period"] = period
    return {"period_end": period, "period_type": "half_year" if period and period[5:7] == "06" else "interim",
            "fields": found, "checks": checks, "valid": valid,
            "note": "OCR từ tài liệu công bố; giá trị và dòng văn bản/trang gốc được lưu để kiểm tra. Không cộng với báo cáo quý có kỳ chồng lấp."}


def extract_hpg_interim(document: dict, root: Path) -> dict:
    path = root / document["file"]
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    cache = root / "data/processed" / f"{checksum[:16]}_issuer_ocr.json"
    if cache.exists():
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if saved.get("sha256") == checksum:
            return parse_interim_text(saved["pages"], document["source_id"], document["published_at"])
    import pymupdf
    engine = shutil.which("tesseract")
    if engine is None and Path("C:/Program Files/Tesseract-OCR/tesseract.exe").exists():
        engine = "C:/Program Files/Tesseract-OCR/tesseract.exe"
    folder = root / "tmp/pdfs" / checksum[:16]
    folder.mkdir(parents=True, exist_ok=True)
    def extract(index):
        pdf = pymupdf.open(path)
        page = pdf[index]
        text = page.get_text()
        if len(text.strip()) < 200:
            if engine is None:
                raise DataSourceError("PDF scan cần Tesseract OCR vie+eng; hiện chưa cài công cụ OCR")
            image = folder / f"page_{index+1}.png"
            page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(image)
            completed = subprocess.run([engine, str(image), "stdout", "-l", "vie+eng", "--psm", "6"],
                capture_output=True, encoding="utf-8", timeout=45, env={**os.environ, "OMP_THREAD_LIMIT": "2"})
            if completed.returncode:
                raise DataSourceError(f"OCR lỗi: {completed.stderr[:200]}")
            text = completed.stdout
        pdf.close()
        return {"page": index + 1, "text": text}
    with pymupdf.open(path) as pdf:
        indices = list(range(min(len(pdf), 18)))
    with ThreadPoolExecutor(max_workers=2) as pool:
        pages = list(pool.map(extract, indices))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"sha256": checksum, "pages": pages}, ensure_ascii=False, indent=2), encoding="utf-8")
    return parse_interim_text(pages, document["source_id"], document["published_at"])
