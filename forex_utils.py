import io
import urllib.request

FOREX_AVAILABLE = True

_HDFC_URL = (
    "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking"
    "/discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf"
)

try:
    import pdfplumber
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False


def _normalise(cell):
    """Collapse all whitespace (including newlines) to a single space."""
    return " ".join(str(cell or "").split())


def _fetch_hdfc_rate():
    """Extract USD T.T. Selling (O/w Rem) rate from the HDFC Treasury Forex PDF."""
    if not _PDFPLUMBER_AVAILABLE:
        return None
    try:
        req = urllib.request.Request(_HDFC_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    tt_col = None
                    header_idx = None
                    for i, row in enumerate(table):
                        # normalise so "T.T.\nSelling\n(O/w\nRem)" → "T.T. Selling (O/w Rem)"
                        cells = [_normalise(c) for c in row]
                        matching = [j for j, c in enumerate(cells)
                                    if "T.T." in c and "Selling" in c and "O/w" in c]
                        if matching:
                            tt_col = matching[0]
                            header_idx = i
                            break
                    if tt_col is None:
                        continue
                    for row in table[header_idx + 1:]:
                        cells = [_normalise(c) for c in row]
                        if cells and "United States Dollar" in cells[0]:
                            val = cells[tt_col] if tt_col < len(cells) else None
                            if val:
                                return float(val.replace(",", ""))
    except Exception:
        pass
    return None


def fetch_hdfc_usd_tt_selling_rate():
    """Return USD TT Selling rate from HDFC PDF, or None if unavailable."""
    return _fetch_hdfc_rate()
