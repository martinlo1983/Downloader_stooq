from pathlib import Path
import time
import traceback
import pandas as pd
import yfinance as yf

# ============================================================
# CONFIGURACION
# ============================================================

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

OUTPUT_DIR = Path("data/stooq")
PERIOD = "max"
SECONDS_BETWEEN_DOWNLOADS = 5
DEBUG = True

# Si True, borra CSV anteriores antes de descargar
CLEAN_BEFORE_DOWNLOAD = True


# ============================================================
# FUNCIONES
# ============================================================

def debug_print(title, value=None):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if value is not None:
        print(value)


def clean_output_directory():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if CLEAN_BEFORE_DOWNLOAD:
        print(f"\nLimpiando CSV anteriores en: {OUTPUT_DIR}")
        for file in OUTPUT_DIR.glob("*.csv"):
            print(f"Eliminando: {file}")
            file.unlink()


def flatten_yfinance_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def daily_to_monthly_shifted(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Construye velas mensuales desde datos diarios.

    Regla:
    - La vela de marzo se guarda con fecha 1 de abril.
    - La vela de abril se guarda con fecha 1 de mayo.
    - El Close es el cierre del último día hábil del mes anterior.
    """

    if df is None or df.empty:
        raise ValueError(f"{ticker}: yfinance devolvió datos vacíos")

    df = flatten_yfinance_columns(df)
    df = df.reset_index()

    if "Date" not in df.columns:
        raise ValueError(f"{ticker}: no encuentro columna Date. Columnas: {list(df.columns)}")

    required = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"{ticker}: faltan columnas {missing}. Columnas: {list(df.columns)}")

    df = df[required].copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df.sort_values("Date")

    df = df.set_index("Date")

    monthly = df.resample("ME").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    })

    monthly = monthly.dropna(subset=["Open", "High", "Low", "Close"])

    # Cambia la etiqueta:
    # 2026-03-31 -> 2026-04-01
    monthly.index = monthly.index + pd.offsets.MonthBegin(1)

    monthly = monthly.reset_index()
    monthly["Date"] = monthly["Date"].dt.strftime("%Y-%m-%d")
    monthly["Volume"] = monthly["Volume"].fillna(0).astype("int64")

    monthly = monthly[["Date", "Open", "High", "Low", "Close", "Volume"]]

    if DEBUG:
        debug_print(f"{ticker}: preview mensual generado", monthly.tail(6))

    return monthly


def download_one(ticker_yahoo: str, output_filename: str):
    output_path = OUTPUT_DIR / output_filename

    debug_print(f"DESCARGANDO {ticker_yahoo}")
    print(f"Archivo destino: {output_path}")

    df = yf.download(
        tickers=ticker_yahoo,
        period=PERIOD,
        interval="1d",
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=False,
        group_by="column",
    )

    if DEBUG:
        debug_print(f"{ticker_yahoo}: columnas originales", df.columns)
        debug_print(f"{ticker_yahoo}: últimas filas diarias", df.tail(5))

    df_out = daily_to_monthly_shifted(df, ticker_yahoo)

    df_out.to_csv(output_path, index=False, encoding="utf-8")

    print(f"\nOK {ticker_yahoo}")
    print(f"Filas guardadas: {len(df_out)}")
    print(f"Desde: {df_out['Date'].iloc[0]}")
    print(f"Hasta: {df_out['Date'].iloc[-1]}")
    print(f"Archivo: {output_path}")


def main():
    debug_print("CONFIGURACION")
    print(f"Tickers: {len(TICKERS)}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Periodo diario descargado: {PERIOD}")
    print("Regla mensual: fecha = primer día del mes siguiente")
    print("Ejemplo: 2026-04-01 = vela cerrada de marzo")

    clean_output_directory()

    errors = []

    for i, (ticker_yahoo, output_filename) in enumerate(TICKERS.items()):
        try:
            download_one(ticker_yahoo, output_filename)
        except Exception as e:
            print("\n" + "!" * 70)
            print(f"ERROR {ticker_yahoo}")
            print("!" * 70)
            print(str(e))

            if DEBUG:
                traceback.print_exc()

            errors.append((ticker_yahoo, str(e)))

        if i < len(TICKERS) - 1:
            print(f"\nEsperando {SECONDS_BETWEEN_DOWNLOADS} segundos...")
            time.sleep(SECONDS_BETWEEN_DOWNLOADS)

    debug_print("RESUMEN FINAL")

    if errors:
        print("Errores:")
        for ticker, error in errors:
            print(f"- {ticker}: {error}")
        raise SystemExit(1)

    print("Descarga finalizada correctamente.")


if __name__ == "__main__":
    main()
