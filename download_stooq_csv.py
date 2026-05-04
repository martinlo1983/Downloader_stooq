from pathlib import Path
import time
import requests

# =========================
# CONFIGURACION PRINCIPAL
# =========================

TICKERS = [
    "acwi.us",
    "spy.us",
    "qqq.us",
    # agregar más tickers acá
]

INTERVAL = "m"  # d = daily, w = weekly, m = monthly

OUTPUT_DIR = Path("data/stooq")

# Opcional. Usar formato YYYYMMDD o dejar en None.
DATE_FROM = None      # ejemplo: "20250101"
DATE_TO = None        # ejemplo: "20260430"

SECONDS_BETWEEN_DOWNLOADS = 8

# =========================
# CODIGO
# =========================

def stooq_filename(ticker: str, interval: str) -> str:
    """
    acwi.us + m -> acwi_us_m.csv
    spy.us + d  -> spy_us_d.csv
    """
    clean = ticker.lower().replace(".", "_")
    return f"{clean}_{interval}.csv"


def build_stooq_url(ticker: str, interval: str) -> str:
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}&i={interval}"

    if DATE_FROM:
        url += f"&d1={DATE_FROM}"
    if DATE_TO:
        url += f"&d2={DATE_TO}"

    return url


def download_one_ticker(session: requests.Session, ticker: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    url = build_stooq_url(ticker, INTERVAL)
    filename = stooq_filename(ticker, INTERVAL)
    output_path = OUTPUT_DIR / filename

    print(f"Descargando {ticker} -> {output_path}")

    response = session.get(url, timeout=30)
    response.raise_for_status()

    text = response.text.strip()

    if not text:
        raise ValueError(f"Respuesta vacía para {ticker}")

    if not text.startswith("Date,Open,High,Low,Close"):
        raise ValueError(
            f"Formato inesperado para {ticker}. Primeros caracteres: {text[:120]}"
        )

    output_path.write_text(text + "\n", encoding="utf-8")

    rows = text.count("\n")
    print(f"OK {ticker}: {rows} filas guardadas")


def main():
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/csv,text/plain,*/*",
    })

    errors = []

    for i, ticker in enumerate(TICKERS):
        try:
            download_one_ticker(session, ticker)
        except Exception as e:
            print(f"ERROR {ticker}: {e}")
            errors.append((ticker, str(e)))

        if i < len(TICKERS) - 1:
            time.sleep(SECONDS_BETWEEN_DOWNLOADS)

    if errors:
        print("\nErrores:")
        for ticker, error in errors:
            print(f"- {ticker}: {error}")

        raise SystemExit(1)

    print("\nDescarga finalizada correctamente.")


if __name__ == "__main__":
    main()
