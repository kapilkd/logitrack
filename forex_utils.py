import io
import urllib.request

FOREX_AVAILABLE = False
try:
    import pdfplumber
    FOREX_AVAILABLE = True
except ImportError:
    pass

_HDFC_URL = (
    "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking"
    "/discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf"
)


def fetch_hdfc_usd_tt_selling_rate():
    """Return USD T.T. Selling (O/w Rem) rate as float, or None on any error."""
    if not FOREX_AVAILABLE:
        return None
    try:
        req = urllib.request.Request(_HDFC_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    tt_col = None
                    header_idx = None
                    for i, row in enumerate(table):
                        cells = [str(c or "").strip() for c in row]
                        matching = [j for j, c in enumerate(cells) if "T.T. Selling" in c]
                        if matching:
                            tt_col = matching[0]
                            header_idx = i
                            break
                    if tt_col is None:
                        continue
                    for row in table[header_idx + 1:]:
                        cells = [str(c or "").strip() for c in row]
                        if cells and "United States Dollar" in cells[0]:
                            val = cells[tt_col] if tt_col < len(cells) else None
                            if val:
                                return float(val.replace(",", ""))
    except Exception:
        pass
    return None
