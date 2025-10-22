# predecir_futuro_mod.py
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

# Configurar logger
logger = logging.getLogger(__name__)

def run_prediction(horas_futuro=6):
    base_dir = Path(__file__).resolve().parent
    
    # Rutas de modelos (prioridad: TFLite compatible > LSTM .h5)
    model_tflite_simple_path = base_dir / "modelos" / "modelo stefano" / "modelo_simple_tflite.tflite"
    model_h5_simple_path = base_dir / "modelos" / "modelo stefano" / "modelo_simple_tflite.h5"
    scaler_tflite_path = base_dir / "modelos" / "modelo stefano" / "scaler_4_features_tflite.pkl"
    
    # Fallback: LSTM antiguo (requiere TensorFlow completo)
    model_h5_lstm_path = base_dir / "modelos" / "modelo stefano" / "modelo_lstm_3_features (1).h5"
    scaler_lstm_path = base_dir / "modelos" / "modelo stefano" / "scaler_4_features.pkl"
    
    csv_path = base_dir / "Codigos_arduinos" / "data" / "sensor_data.csv"

    # Comprobaciones
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    # ===== ESTRATEGIA DE CARGA DE MODELOS =====
    # 1. Intentar modelo TFLite simple (compatible con tflite-runtime)
    # 2. Si falla, intentar modelo LSTM .h5 (requiere TensorFlow)
    
    model_predict = None
    scaler = None
    usar_flatten = False  # Flag para saber si necesitamos aplanar las secuencias
    
    import joblib
    
    # === INTENTO 1: Modelo Simple TFLite (sin TensorFlow) ===
    if model_tflite_simple_path.exists() and scaler_tflite_path.exists():
        try:
            logger.info(f"🔄 Intentando modelo TFLite simple: {model_tflite_simple_path.name}")
            
            # Cargar scaler
            scaler = joblib.load(scaler_tflite_path)
            logger.info(f"✅ Scaler cargado: {scaler_tflite_path.name}")
            
            # Intentar cargar con tflite_runtime (sin TensorFlow)
            try:
                import tflite_runtime.interpreter as tflite
                logger.info(f"✅ Usando tflite_runtime (sin TensorFlow)")
            except ImportError:
                # Fallback a tensorflow.lite
                import tensorflow as tf
                tflite = tf.lite
                logger.info(f"⚠️  tflite_runtime no disponible, usando tensorflow.lite")
            
            logger.info(f"📂 Cargando modelo desde: {model_tflite_simple_path}")
            interpreter = tflite.Interpreter(model_path=str(model_tflite_simple_path))
            interpreter.allocate_tensors()
            
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            logger.info(f"📊 Input shape: {input_details[0]['shape']}, dtype: {input_details[0]['dtype']}")
            logger.info(f"📊 Output shape: {output_details[0]['shape']}, dtype: {output_details[0]['dtype']}")
            
            def predict_tflite(X_input):
                interpreter.set_tensor(input_details[0]['index'], X_input.astype(np.float32))
                interpreter.invoke()
                return interpreter.get_tensor(output_details[0]['index'])
            
            model_predict = predict_tflite
            usar_flatten = True  # Modelo Dense necesita entrada aplanada
            logger.info(f"✅ Modelo TFLite simple cargado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error cargando TFLite simple: {type(e).__name__}: {str(e)}")
            logger.exception("Traceback completo del error TFLite:")
            model_predict = None
    
    # === INTENTO 2: Modelo LSTM .h5 (requiere TensorFlow) ===
    if model_predict is None:
        if model_h5_lstm_path.exists() and scaler_lstm_path.exists():
            try:
                logger.info(f"🔄 Fallback: Cargando modelo LSTM .h5 con TensorFlow...")
                
                import tensorflow as tf
                from tensorflow import keras
                
                model = keras.models.load_model(model_h5_lstm_path, compile=False)
                scaler = joblib.load(scaler_lstm_path)
                
                model_predict = lambda X: model.predict(X, verbose=0)
                usar_flatten = False  # LSTM usa secuencias 3D
                logger.info(f"✅ Modelo LSTM .h5 cargado exitosamente")
                
            except ImportError:
                logger.error("❌ TensorFlow no está instalado, no se puede cargar LSTM")
                raise ImportError(
                    "❌ No se pudo cargar ningún modelo.\n"
                    "   • TFLite simple no está disponible o falló\n"
                    "   • LSTM .h5 requiere TensorFlow (no instalado)\n"
                    "   Solución: Instala 'tensorflow' o entrena el modelo TFLite simple"
                )
            except Exception as e:
                raise RuntimeError(f"❌ Error cargando modelo LSTM: {e}")
        else:
            raise FileNotFoundError(
                "❌ No se encontró ningún modelo disponible:\n"
                f"   • TFLite simple: {model_tflite_simple_path.name} ({'✅' if model_tflite_simple_path.exists() else '❌'})\n"
                f"   • LSTM .h5: {model_h5_lstm_path.name} ({'✅' if model_h5_lstm_path.exists() else '❌'})"
            )
    
    # Verificar que tenemos modelo y scaler
    if model_predict is None or scaler is None:
        raise RuntimeError("No se pudo inicializar el modelo correctamente")

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
        # Preparar input según el tipo de modelo
        if usar_flatten:
            # Modelo Dense (TFLite simple): aplanar ventana
            X_input = ventana_actual.flatten().reshape(1, -1)
        else:
            # Modelo LSTM: mantener forma 3D
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
