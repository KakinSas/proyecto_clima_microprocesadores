import pandas as pd
import sys
from pathlib import Path

p = r'd:\proyecto_clima_microprocesadores\Codigos_arduinos\data\sensor_data.csv'
if not Path(p).exists():
    print(f"ERROR: CSV not found: {p}")
    sys.exit(1)

try:
    df = pd.read_csv(p)
except Exception as e:
    print("ERROR leyendo CSV:", e)
    sys.exit(1)

print("raw rows:", len(df))

if 'timestamp' in df.columns:
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Seleccionar solo las columnas numéricas de interés antes de resamplear
        cols = ['timestamp', 'temperatura', 'humedad', 'presion']
        missing = [c for c in cols if c not in df.columns]
        if missing:
            print(f"Faltan columnas necesarias para resample: {missing}")
            sys.exit(1)

        df_num = df[cols].copy()
        # Forzar conversión a numérico; valores no convertibles pasarán a NaN
        for c in ['temperatura', 'humedad', 'presion']:
            df_num[c] = pd.to_numeric(df_num[c], errors='coerce')

        df2 = df_num.set_index('timestamp').resample('1min').mean().dropna().reset_index()
        print("resampled rows:", len(df2))
        print('\nFirst 10 resampled rows:')
        print(df2.head(10).to_string(index=False))
        outp = r'd:\proyecto_clima_microprocesadores\modelos\sensor_data_resampled_sample.csv'
        df2.head(100).to_csv(outp, index=False)
        print(f"\nSample saved to {outp}")
    except Exception as e:
        print("Resample error:", e)
else:
    print("No 'timestamp' column in CSV. Columns:", df.columns.tolist())
