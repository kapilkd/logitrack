import io
import logging
import re
import urllib.request
from datetime import date
from pathlib import Path

FOREX_AVAILABLE = True
logger = logging.getLogger(__name__)

_HDFC_URL = "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf"

_RATES_DIR = Path(__file__).parent / "static" / "downloads" / "rates"

try:
    import pdfplumber
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _today_str():
    return date.today().strftime("%d_%m_%Y")


def _ensure_dir():
    _RATES_DIR.mkdir(parents=True, exist_ok=True)


def _pdf_path(date_str):
    return _RATES_DIR / f"rate_{date_str}.pdf"


def _normalise(cell):
    return " ".join(str(cell or "").split())


# ── PDF parsing ───────────────────────────────────────────────────────────────

def _parse_hdfc_table(pdf):
    """Extract USD T.T. Selling rate via table extraction (HDFC PDF format)."""
    for page in pdf.pages:
        for table in (page.extract_tables() or []):
            tt_col = header_idx = None
            for i, row in enumerate(table):
                cells = [_normalise(c) for c in row]
                cols = [j for j, c in enumerate(cells)
                        if "T.T." in c and "Selling" in c and "O/w" in c]
                if cols:
                    tt_col, header_idx = cols[0], i
                    break
            if tt_col is None:
                continue
            for row in table[header_idx + 1:]:
                cells = [_normalise(c) for c in row]
                if cells and ("United States Dollar" in cells[0]
                              or "UnitedStatesDollar" in cells[0].replace(" ", "")):
                    val = cells[tt_col] if tt_col < len(cells) else None
                    if val:
                        try:
                            return float(val.replace(",", ""))
                        except ValueError:
                            pass
    return None


def _parse_text_fallback(pdf):
    """Extract USD rate via text search (LogiTrack manual PDF format)."""
    for page in pdf.pages:
        text = page.extract_text() or ""
        m = re.search(r"United\s*States\s*Dollar\s+([\d,]+\.?\d*)", text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def _extract_rate_from_pdf(source):
    """
    Extract USD T.T. Selling rate from a PDF.
    source can be a Path (cached file) or raw bytes (live fetch).
    """
    if not _PDFPLUMBER_AVAILABLE:
        return None
    try:
        ctx = (pdfplumber.open(source) if isinstance(source, Path)
               else pdfplumber.open(io.BytesIO(source)))
        with ctx as pdf:
            return _parse_hdfc_table(pdf) or _parse_text_fallback(pdf)
    except Exception as e:
        logger.error("forex: PDF parse error — %s: %s", type(e).__name__, e)
        return None


# ── Minimal PDF writer ────────────────────────────────────────────────────────

def _write_rate_pdf(path, rate, date_str):
    """
    Write a minimal valid PDF-1.4 file containing the rate in a layout
    that _parse_text_fallback() can recover on subsequent reads.
    No external packages required — uses only Python built-ins.
    """
    lines = [
        "LOGITRACK FOREX RATE",
        f"Date: {date_str.replace('_', '-')}",
        "Source: Manual Entry",
        "T.T. Selling (O/w Rem)",
        f"United States Dollar {rate:.2f}",
    ]

    def _esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream_str = "BT\n/F1 11 Tf\n20 TL\n50 700 Td\n"
    for line in lines:
        stream_str += f"({_esc(line)}) Tj\nT*\n"
    stream_str += "ET\n"
    stream_b = stream_str.encode("latin-1")

    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    resources = b"<< /Font << /F1 " + font + b" >> >>"

    hdr  = b"%PDF-1.4\n"
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources " + resources + b" >>\nendobj\n")
    obj4 = (b"4 0 obj\n<< /Length " + str(len(stream_b)).encode() + b" >>\n"
            b"stream\n" + stream_b + b"endstream\nendobj\n")

    offsets, pos = [], len(hdr)
    for obj in [obj1, obj2, obj3, obj4]:
        offsets.append(pos)
        pos += len(obj)

    xref = b"xref\n0 5\n0000000000 65535 f \r\n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \r\n".encode()

    trailer = (b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n"
               + str(pos).encode() + b"\n%%EOF\n")

    with open(path, "wb") as f:
        f.write(hdr + obj1 + obj2 + obj3 + obj4 + xref + trailer)


# ── Cache read / write ────────────────────────────────────────────────────────

def _load_cached_rate(date_str):
    """Return (rate, 'cached') if today's PDF exists and is parseable."""
    pdf = _pdf_path(date_str)
    if pdf.exists():
        rate = _extract_rate_from_pdf(pdf)
        if rate is not None:
            logger.info("forex: cache hit — %.4f from %s", rate, pdf.name)
            return rate, "cached"
        logger.warning("forex: cache file %s exists but rate not parseable", pdf.name)
    return None, None


def _save_hdfc_pdf(data, date_str):
    """Persist the raw HDFC PDF bytes to the rates cache folder."""
    try:
        _ensure_dir()
        with open(_pdf_path(date_str), "wb") as f:
            f.write(data)
        logger.info("forex: HDFC PDF cached → rate_%s.pdf", date_str)
    except Exception as e:
        logger.warning("forex: could not cache HDFC PDF — %s", e)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_hdfc_usd_tt_selling_rate():
    """
    Return (rate: float, source: str) or (None, None).

    source values:
      'cached' — read from today's cached PDF in static/downloads/rates/
      'live'   — freshly fetched from HDFC and now cached for the day

    Lookup order:
      1. static/downloads/rates/rate_DD_MM_YYYY.pdf  (cache check)
      2. Live HDFC PDF download (result saved to cache)
    """
    date_str = _today_str()

    rate, source = _load_cached_rate(date_str)
    if rate is not None:
        return rate, source

    if not _PDFPLUMBER_AVAILABLE:
        logger.warning("forex: pdfplumber not installed — cannot fetch HDFC rate")
        return None, None

    try:
        req = urllib.request.Request(_HDFC_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
    except Exception as e:
        logger.error("forex: download failed — %s: %s", type(e).__name__, e)
        return None, None

    rate = _extract_rate_from_pdf(data)
    if rate is not None:
        _save_hdfc_pdf(data, date_str)
        return rate, "live"

    logger.warning("forex: PDF fetched but USD T.T. Selling rate not found")
    return None, None


def save_manual_rate(rate):
    """
    Persist a manually entered USD/INR rate for today as a PDF in
    static/downloads/rates/rate_DD_MM_YYYY.pdf so subsequent same-day
    requests return it without hitting HDFC's servers.
    Returns True on success.
    """
    date_str = _today_str()
    try:
        _ensure_dir()
        _write_rate_pdf(_pdf_path(date_str), float(rate), date_str)
        logger.info("forex: manual rate %.4f saved → rate_%s.pdf", float(rate), date_str)
        return True
    except Exception as e:
        logger.error("forex: could not save manual rate — %s", e)
        return False
