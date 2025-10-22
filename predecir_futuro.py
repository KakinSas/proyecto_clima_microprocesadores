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
    
    # Rutas de modelos
    model_tflite_path = base_dir / "modelos" / "modelo stefano" / "modelo_lstm_3_features.tflite"
    model_h5_path = base_dir / "modelos" / "modelo stefano" / "modelo_lstm_3_features (1).h5"
    scaler_path = base_dir / "modelos" / "modelo stefano" / "scaler_4_features.pkl"
    csv_path = base_dir / "Codigos_arduinos" / "data" / "sensor_data.csv"

    # Comprobaciones
    if not scaler_path.exists():
        raise FileNotFoundError(f"Scaler no encontrado: {scaler_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    # Intentar cargar modelo TFLite primero (aunque falle con Flex ops)
    model_predict = None
    
    if model_tflite_path.exists():
        try:
            print(f"🔄 Intentando cargar modelo TFLite...")
            
            # Intentar con tflite_runtime primero
            try:
                import tflite_runtime.interpreter as tflite
                print(f"✅ Usando tflite_runtime")
            except ImportError:
                print(f"⚠️  tflite_runtime no disponible, usando tensorflow.lite")
                import tensorflow as tf
                tflite = tf.lite
            
            interpreter = tflite.Interpreter(model_path=str(model_tflite_path))
            interpreter.allocate_tensors()
            
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            
            def predict_tflite(X_input):
                interpreter.set_tensor(input_details[0]['index'], X_input.astype(np.float32))
                interpreter.invoke()
                return interpreter.get_tensor(output_details[0]['index'])
            
            model_predict = predict_tflite
            print(f"✅ Modelo TFLite cargado exitosamente")
            
        except Exception as e:
            print(f"❌ Error al cargar TFLite: {type(e).__name__}: {str(e)[:100]}")
            print(f"🔄 Fallback: Intentando cargar modelo .h5 con TensorFlow...")
    
    # Si TFLite falló o no existe, usar .h5
    if model_predict is None:
        if not model_h5_path.exists():
            raise FileNotFoundError(f"Modelo .h5 no encontrado: {model_h5_path}")
        
        print(f"🚀 Cargando modelo Keras (.h5) con TensorFlow completo")
        import tensorflow as tf
        from tensorflow import keras
        model = keras.models.load_model(model_h5_path, compile=False)
        model_predict = lambda X: model.predict(X, verbose=0)
        print(f"✅ Modelo Keras cargado exitosamente")
    import joblib
    scaler = joblib.load(scaler_path)

    df = pd.read_csv(csv_path)
    
    # Verificar columnas requeridas
    feature_mapping = {'temperatura': 'ts', 'humedad': 'hr', 'presion': 'p0'}
    missing = [col for col in feature_mapping.keys() if col not in df.columns]
    if missing:
        raise ValueError(f"Columnas faltantes en CSV: {missing}")
    
    # Verificar que exista timestamp
    if 'timestamp' not in df.columns:
        raise ValueError("CSV debe contener columna 'timestamp'")
    
    # Convertir timestamp a datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Extraer hora_decimal del timestamp (igual que en el entrenamiento)
    df['hora_decimal'] = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60.0
    
    # Preparar datos con las 4 features (temperatura, humedad, presión, hora_decimal)
    feature_cols = list(feature_mapping.keys()) + ['hora_decimal']
    X_raw = df[feature_cols].astype(float).to_numpy()
    
    n_pasos = 24
    n_features = 4  # ts, hr, p0, hora_decimal
    # ahora por minuto
    n_predicciones = horas_futuro * 60

    if len(X_raw) < n_pasos:
        raise ValueError("Datos insuficientes para la ventana del modelo")

    X_scaled = scaler.transform(X_raw)
    ventana_actual = X_scaled[-n_pasos:].copy()
    
    # Obtener último timestamp para calcular timestamps futuros
    ultimo_timestamp = df['timestamp'].iloc[-1]

    predicciones_temp = []
    for i in range(n_predicciones):
        X_input = ventana_actual.reshape(1, n_pasos, n_features)
        pred_scaled = model_predict(X_input)[0][0]
        
        # Calcular timestamp futuro
        timestamp_futuro = ultimo_timestamp + timedelta(minutes=i+1)
        hora_decimal_futuro = timestamp_futuro.hour + timestamp_futuro.minute / 60.0
        
        # Mantener últimos valores de humedad y presión (escalados)
        ultima_hr_scaled = ventana_actual[-1, 1]
        ultima_p0_scaled = ventana_actual[-1, 2]
        
        # Crear nuevo registro con las 4 features
        nuevo_registro_scaled = np.array([
            pred_scaled,           # temperatura predicha (escalada)
            ultima_hr_scaled,      # humedad (escalada)
            ultima_p0_scaled,      # presión (escalada)
            hora_decimal_futuro    # hora_decimal (no escalada, ya está en [0, 24))
        ])
        
        ventana_actual = np.vstack([ventana_actual[1:], nuevo_registro_scaled])
        predicciones_temp.append(pred_scaled)

    predicciones_array = np.array(predicciones_temp).reshape(-1, 1)
    dummy = np.zeros((len(predicciones_array), n_features))
    dummy[:, 0] = predicciones_array.flatten()
    dummy[:, 1] = X_scaled[-1, 1]  # última humedad
    dummy[:, 2] = X_scaled[-1, 2]  # última presión
    dummy[:, 3] = 0  # hora_decimal (no afecta al inverse_transform de temperatura)
    predicciones_reales = scaler.inverse_transform(dummy)[:, 0]

    # timestamps por minuto a partir del último timestamp en CSV
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
