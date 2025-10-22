"""
Script para convertir modelo Keras (.h5) a TensorFlow Lite (.tflite)
Para optimizar el rendimiento en Raspberry Pi Zero 2 W
"""

import tensorflow as tf
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
print(f"⚙️  Nota: Usando SELECT_TF_OPS para compatibilidad con LSTM")
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
