from pathlib import Path
import time
import pandas as pd
import yfinance as yf

# =========================
# CONFIGURACION
# =========================

TICKERS = {
    # "ticker_yahoo": "nombre_archivo_stooq"
    "ACWI": "acwi_us_m.csv",
    "SPY": "spy_us_m.csv",
    "QQQ": "qqq_us_m.csv",
}

INTERVAL = "1mo"          # 1d, 1wk, 1mo
PERIOD = "max"            # max, 10y, 5y, etc.
OUTPUT_DIR = Path("data/stooq")

SECONDS_BETWEEN_DOWNLOADS = 5

# =========================
# CODIGO
# =========================

def normalize_yfinance_to_stooq_format(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("DataFrame vacío")

    df = df.reset_index()

    # yfinance puede devolver Date o Datetime
    date_col = "Date" if "Date" in df.columns else "Datetime"
    df["Date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")

    required = ["Date", "Open", "High", "Low", "Close", "Volume"]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}")

    df = df[required].copy()

    # Evita filas incompletas
    df = df.dropna(subset=["Open", "High", "Low", "Close"])

    # Stooq suele venir sin decimales fijos obligatorios.
    # Dejamos floats limpios y volumen entero.
    df["Volume"] = df["Volume"].fillna(0).astype("int64")

    return df


def download_one(ticker_yahoo: str, output_filename: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Descargando {ticker_yahoo} -> {OUTPUT_DIR / output_filename}")

    df = yf.download(
        ticker_yahoo,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=False,
    )

    df_out = normalize_yfinance_to_stooq_format(df)

    output_path = OUTPUT_DIR / output_filename
    df_out.to_csv(output_path, index=False)

    print(f"OK {ticker_yahoo}: {len(df_out)} filas")


def main():
    errors = []

    for i, (ticker_yahoo, output_filename) in enumerate(TICKERS.items()):
        try:
            download_one(ticker_yahoo, output_filename)
        except Exception as e:
            print(f"ERROR {ticker_yahoo}: {e}")
            errors.append((ticker_yahoo, str(e)))

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
