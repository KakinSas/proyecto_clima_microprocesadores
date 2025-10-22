"""
Script para convertir modelo Keras (.h5) a TensorFlow Lite (.tflite)
Para optimizar el rendimiento en Raspberry Pi Zero 2 W
"""

import tensorflow as tf
import numpy as np
from pathlib import Path

# Rutas
base_dir = Path(__file__).resolve().parent
modelo_h5 = base_dir / "modelos" / "modelo stefano" / "modelo_lstm_3_features (1).h5"
modelo_tflite = base_dir / "modelos" / "modelo stefano" / "modelo_lstm_3_features.tflite"

print(f"🔄 Cargando modelo desde: {modelo_h5}")

# Cargar el modelo Keras sin compilar (ignora métricas y optimizadores incompatibles)
model = tf.keras.models.load_model(modelo_h5, compile=False)

print(f"📊 Arquitectura del modelo:")
model.summary()

# Convertir a TensorFlow Lite
print(f"\n🔧 Convirtiendo a TensorFlow Lite...")

# Método 1: Intentar cuantización completa (más compatible con tflite-runtime)
try:
    print("🔄 Intento 1: Conversión con cuantización INT8 (máxima compatibilidad)...")
    
    # Necesitamos un dataset representativo para cuantización
    import pandas as pd
    csv_path = base_dir / "Codigos_arduinos" / "data" / "sensor_data.csv"
    
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['hora_decimal'] = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60.0
        
        feature_mapping = {'temperatura': 'ts', 'humedad': 'hr', 'presion': 'p0'}
        feature_cols = list(feature_mapping.keys()) + ['hora_decimal']
        X_raw = df[feature_cols].astype(float).to_numpy()
        
        # Tomar muestras para calibración
        import joblib
        scaler_path = base_dir / "modelos" / "modelo stefano" / "scaler_4_features.pkl"
        scaler = joblib.load(scaler_path)
        X_scaled = scaler.transform(X_raw)
        
        # Dataset representativo (últimas 100 ventanas)
        def representative_dataset():
            for i in range(min(100, len(X_scaled) - 24)):
                yield [X_scaled[i:i+24].astype(np.float32).reshape(1, 24, 4)]
        
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = representative_dataset
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.int8
        converter.inference_output_type = tf.int8
        
        tflite_model = converter.convert()
        print("✅ Conversión exitosa con INT8! (Compatible con tflite-runtime)")
        
    else:
        raise FileNotFoundError("CSV no encontrado para cuantización")
    
except Exception as e:
    print(f"❌ Falló conversión INT8: {str(e)[:150]}")
    print("\n🔄 Intento 2: Conversión con SELECT_TF_OPS (requiere TensorFlow completo)...")
    
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # Configuración para modelos LSTM (permite operaciones TF select)
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,  # Operaciones básicas de TFLite
        tf.lite.OpsSet.SELECT_TF_OPS      # Operaciones TensorFlow necesarias para LSTM
    ]
    converter._experimental_lower_tensor_list_ops = False
    
    # Optimizaciones para Raspberry Pi
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    
    # Convertir
    print(f"⚠️  ADVERTENCIA: Este modelo requiere TensorFlow completo en Raspberry Pi")
    tflite_model = converter.convert()

# Guardar
print(f"💾 Guardando modelo TFLite en: {modelo_tflite}")
with open(modelo_tflite, 'wb') as f:
    f.write(tflite_model)

# Verificar tamaño
import os
size_h5 = os.path.getsize(modelo_h5) / (1024 * 1024)  # MB
size_tflite = os.path.getsize(modelo_tflite) / (1024 * 1024)  # MB

print(f"\n✅ Conversión completada!")
print(f"📦 Tamaño modelo .h5: {size_h5:.2f} MB")
print(f"📦 Tamaño modelo .tflite: {size_tflite:.2f} MB")
print(f"🎯 Reducción: {((size_h5 - size_tflite) / size_h5 * 100):.1f}%")
