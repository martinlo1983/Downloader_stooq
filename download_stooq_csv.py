from pathlib import Path
import time
import traceback
import pandas as pd
import yfinance as yf

# ============================================================
# CONFIGURACION
# ============================================================

# Formato:
# "TICKER_YAHOO": "nombre_archivo_final.csv"
#
# El nombre final replica el formato que venías usando de Stooq.
TICKERS = {
    "SPY": "spy_us_m.csv",
    "VEA": "vea_us_m.csv",
    "EEM": "eem_us_m.csv",
    "IEMG": "iemg_us_m.csv",
    "IWM": "iwm_us_m.csv",
    "IVV": "ivv_us_m.csv",
    "QQQ": "qqq_us_m.csv",
    "VGT": "vgt_us_m.csv",
    "SMH": "smh_us_m.csv",
    "IGV": "igv_us_m.csv",
    "IBB": "ibb_us_m.csv",
    "EWJ": "ewj_us_m.csv",
    "EFA": "efa_us_m.csv",
    "IEUR": "ieur_us_m.csv",
    "ILF": "ilf_us_m.csv",
    "VGK": "vgk_us_m.csv",
    "INDA": "inda_us_m.csv",
    "FXI": "fxi_us_m.csv",
    "EWZ": "ewz_us_m.csv",
    "XLE": "xle_us_m.csv",
    "XLF": "xlf_us_m.csv",
    "XLV": "xlv_us_m.csv",
    "XLP": "xlp_us_m.csv",
    "ITA": "ita_us_m.csv",
    "XLU": "xlu_us_m.csv",
    "MTUM": "mtum_us_m.csv",
    "DIA": "dia_us_m.csv",
    "IJH": "ijh_us_m.csv",
    "IVE": "ive_us_m.csv",
    "GLD": "gld_us_m.csv",
    "SLV": "slv_us_m.csv",
    "XME": "xme_us_m.csv",
    "URA": "ura_us_m.csv",
    "USO": "uso_us_m.csv",
}

# Intervalos yfinance:
# 1d  = diario
# 1wk = semanal
# 1mo = mensual
INTERVAL = "1mo"

# max, 20y, 10y, 5y, 2y, 1y, etc.
PERIOD = "max"

OUTPUT_DIR = Path("data/stooq")

SECONDS_BETWEEN_DOWNLOADS = 5

# Si True, muestra más detalle de columnas y primeras filas
DEBUG = True


# ============================================================
# FUNCIONES
# ============================================================

def debug_print(title, value=None):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if value is not None:
        print(value)


def flatten_yfinance_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    yfinance a veces devuelve columnas normales:
        Open, High, Low, Close, Volume

    Y a veces devuelve MultiIndex:
        ('Open', 'ACWI'), ('High', 'ACWI'), etc.

    Esta función normaliza eso.
    """
    if isinstance(df.columns, pd.MultiIndex):
        debug_print("Columnas MultiIndex detectadas", df.columns)

        # Caso típico: primer nivel = Price, segundo nivel = Ticker
        # Nos quedamos con el primer nivel.
        df = df.copy()
        df.columns = df.columns.get_level_values(0)

        debug_print("Columnas luego de aplanar MultiIndex", list(df.columns))

    return df


def normalize_yfinance_to_stooq_format(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df is None:
        raise ValueError(f"{ticker}: yfinance devolvió None")

    if df.empty:
        raise ValueError(f"{ticker}: DataFrame vacío")

    if DEBUG:
        debug_print(f"{ticker}: shape original", df.shape)
        debug_print(f"{ticker}: columnas originales", df.columns)
        debug_print(f"{ticker}: primeras filas originales", df.head(3))

    df = flatten_yfinance_columns(df)

    df = df.reset_index()

    if DEBUG:
        debug_print(f"{ticker}: columnas luego de reset_index", list(df.columns))
        debug_print(f"{ticker}: primeras filas luego de reset_index", df.head(3))

    if "Date" in df.columns:
        date_col = "Date"
    elif "Datetime" in df.columns:
        date_col = "Datetime"
    else:
        raise ValueError(
            f"{ticker}: no encuentro columna Date/Datetime. Columnas recibidas: {list(df.columns)}"
        )

    df["Date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")

    required = ["Date", "Open", "High", "Low", "Close", "Volume"]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"{ticker}: faltan columnas {missing}. Columnas recibidas: {list(df.columns)}"
        )

    df = df[required].copy()

    before_drop = len(df)
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    after_drop = len(df)

    if DEBUG:
        debug_print(
            f"{ticker}: filas descartadas por OHLC incompleto",
            before_drop - after_drop
        )

    df["Volume"] = df["Volume"].fillna(0).astype("int64")

    # Orden cronológico ascendente, como suele venir Stooq
    df = df.sort_values("Date").reset_index(drop=True)

    if DEBUG:
        debug_print(f"{ticker}: CSV final preview", df.head(5))
        debug_print(f"{ticker}: últimas filas CSV final", df.tail(5))

    return df


def download_one(ticker_yahoo: str, output_filename: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / output_filename

    debug_print(f"INICIO DESCARGA: {ticker_yahoo}")
    print(f"Archivo destino: {output_path}")
    print(f"Intervalo: {INTERVAL}")
    print(f"Periodo: {PERIOD}")

    df = yf.download(
        tickers=ticker_yahoo,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=False,
        group_by="column",
    )

    df_out = normalize_yfinance_to_stooq_format(df, ticker_yahoo)

    if df_out.empty:
        raise ValueError(f"{ticker_yahoo}: luego de normalizar, el CSV quedó vacío")

    df_out.to_csv(output_path, index=False, encoding="utf-8")

    print(f"\nOK {ticker_yahoo}")
    print(f"Filas guardadas: {len(df_out)}")
    print(f"Desde: {df_out['Date'].iloc[0]}")
    print(f"Hasta: {df_out['Date'].iloc[-1]}")
    print(f"Archivo: {output_path}")

def clean_output_directory():
    if OUTPUT_DIR.exists():
        print(f"\nLimpiando carpeta: {OUTPUT_DIR}")
        for file in OUTPUT_DIR.glob("*.csv"):
            print(f"Eliminando: {file}")
            file.unlink()
    else:
        print(f"\nCreando carpeta: {OUTPUT_DIR}")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    clean_output_directory()
    debug_print("CONFIGURACION GENERAL")
    print(f"Tickers configurados: {TICKERS}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Intervalo: {INTERVAL}")
    print(f"Periodo: {PERIOD}")
    print(f"Debug: {DEBUG}")

    errors = []

    for i, (ticker_yahoo, output_filename) in enumerate(TICKERS.items()):
        try:
            download_one(ticker_yahoo, output_filename)

        except Exception as e:
            print("\n" + "!" * 70)
            print(f"ERROR DESCARGANDO {ticker_yahoo}")
            print("!" * 70)
            print(str(e))

            if DEBUG:
                print("\nTraceback completo:")
                traceback.print_exc()

            errors.append((ticker_yahoo, str(e)))

        if i < len(TICKERS) - 1:
            print(f"\nEsperando {SECONDS_BETWEEN_DOWNLOADS} segundos...")
            time.sleep(SECONDS_BETWEEN_DOWNLOADS)

    debug_print("RESUMEN FINAL")

    if errors:
        print("Descarga terminada con errores:")
        for ticker, error in errors:
            print(f"- {ticker}: {error}")

        raise SystemExit(1)

    print("Descarga finalizada correctamente.")
    print(f"Archivos generados en: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
