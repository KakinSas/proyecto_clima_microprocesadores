# predecir_futuro_mod.py
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

def run_prediction(horas_futuro=6):
    base_dir = Path(__file__).resolve().parent
    model_path = base_dir / "modelos\modelo stefano\modelo_lstm_3_features.h5"
    scaler_path = base_dir / "modelos\modelo stefano\scaler_3_features.pkl"
    csv_path = base_dir / "Codigos_arduinos\data\sensor_data.csv"

    # comprobaciones (omito prints para brevedad)
    if not model_path.exists():
        raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
    if not scaler_path.exists():
        raise FileNotFoundError(f"Scaler no encontrado: {scaler_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    import tensorflow as tf
    from tensorflow import keras
    model = keras.models.load_model(model_path, compile=False)
    import joblib
    scaler = joblib.load(scaler_path)

    df = pd.read_csv(csv_path)
    feature_mapping = {'temperatura': 'ts', 'humedad': 'hr', 'presion': 'p0'}
    missing = [col for col in feature_mapping.keys() if col not in df.columns]
    if missing:
        raise ValueError(f"Columnas faltantes en CSV: {missing}")

    X_raw = df[list(feature_mapping.keys())].astype(float).to_numpy()
    n_pasos = 24
    # ahora por minuto
    n_predicciones = horas_futuro * 60

    if len(X_raw) < n_pasos:
        raise ValueError("Datos insuficientes para la ventana del modelo")

    X_scaled = scaler.transform(X_raw)
    ventana_actual = X_scaled[-n_pasos:].copy()

    predicciones_temp = []
    for i in range(n_predicciones):
        X_input = ventana_actual.reshape(1, n_pasos, 3)
        pred_scaled = model.predict(X_input, verbose=0)[0][0]
        ultima_hr_scaled = ventana_actual[-1, 1]
        ultima_p0_scaled = ventana_actual[-1, 2]
        nuevo_registro_scaled = np.array([pred_scaled, ultima_hr_scaled, ultima_p0_scaled])
        ventana_actual = np.vstack([ventana_actual[1:], nuevo_registro_scaled])
        predicciones_temp.append(pred_scaled)

    predicciones_array = np.array(predicciones_temp).reshape(-1, 1)
    dummy = np.zeros((len(predicciones_array), 3))
    dummy[:, 0] = predicciones_array.flatten()
    dummy[:, 1] = X_scaled[-1, 1]
    dummy[:, 2] = X_scaled[-1, 2]
    predicciones_reales = scaler.inverse_transform(dummy)[:, 0]

    # timestamps por minuto a partir del último timestamp en CSV (si existe)
    if 'timestamp' in df.columns:
        try:
            ultimo_timestamp = pd.to_datetime(df['timestamp'].iloc[-1])
        except:
            ultimo_timestamp = datetime.now()
    else:
        ultimo_timestamp = datetime.now()

    timestamps_futuros = [ultimo_timestamp + timedelta(minutes=i+1) for i in range(n_predicciones)]
    resultado_df = pd.DataFrame({
        'timestamp': timestamps_futuros,
        'temperatura_predicha': predicciones_reales,
        'minutos_desde_inicio': range(1, n_predicciones + 1),
        'horas_desde_inicio': [ (i+1)/60 for i in range(n_predicciones) ]
    })

    output_path = base_dir / f"predicciones_{horas_futuro}_horas_por_minuto.csv"
    resultado_df.to_csv(output_path, index=False)
    return str(output_path)
