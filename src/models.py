"""Validated user request and stable report-section identifiers."""
from dataclasses import dataclass, field, asdict
from datetime import date

SECTION_LABELS = {"overview": "Tổng quan", "market": "Giá và giao dịch", "financial": "Tài chính",
                  "valuation": "Định giá theo giả định", "news": "Tin tức", "risks": "Cơ hội và rủi ro"}


@dataclass
class AnalysisRequest:
    ticker: str
    start: date
    as_of: date
    mode: str = "full"
    sections: list[str] = field(default_factory=lambda: list(SECTION_LABELS))
    target_pb: float = 1.5

    def __post_init__(self):
        if self.mode not in {"summary", "full"}:
            raise ValueError("Chế độ báo cáo không hợp lệ.")
        if not self.sections or set(self.sections) - set(SECTION_LABELS):
            raise ValueError("Chọn ít nhất một phần báo cáo hợp lệ.")
        if not 0 < self.target_pb <= 20:
            raise ValueError("P/B giả định phải lớn hơn 0 và không quá 20.")

    def to_dict(self):
        return {**asdict(self), "start": self.start.isoformat(), "as_of": self.as_of.isoformat()}
