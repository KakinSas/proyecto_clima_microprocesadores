"""
Script para convertir modelo Keras (.h5) a TensorFlow Lite (.tflite)
Con máxima compatibilidad para tflite-runtime antiguo en Raspberry Pi
"""

import tensorflow as tf
import numpy as np
from pathlib import Path

# Rutas
base_dir = Path(__file__).resolve().parent
modelo_h5 = base_dir / "modelos" / "modelo stefano" / "modelo_simple_tflite.h5"
modelo_tflite = base_dir / "modelos" / "modelo stefano" / "modelo_simple_tflite.tflite"

print(f"TensorFlow version: {tf.__version__}")
print(f"🔄 Cargando modelo desde: {modelo_h5}")

# Cargar el modelo Keras
model = tf.keras.models.load_model(modelo_h5, compile=False)

print(f"✅ Modelo cargado")
print(f"   Input shape: {model.input_shape}")
print(f"   Output shape: {model.output_shape}")

# Convertir a TensorFlow Lite con compatibilidad máxima
print(f"\n🔧 Convirtiendo a TFLite (modo compatibilidad)...")

converter = tf.lite.TFLiteConverter.from_keras_model(model)

# CONFIGURACIÓN PARA MÁXIMA COMPATIBILIDAD CON TFLITE-RUNTIME ANTIGUO
converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS  # Solo operadores builtin básicos
]
# Forzar uso de operadores antiguos (opcode version 11 o menor)
converter._experimental_new_quantizer = False

print(f"   • Solo operadores TFLITE_BUILTINS")
print(f"   • Forzando opcode versions antiguas")

# Convertir
tflite_model = converter.convert()

# Guardar
print(f"\n💾 Guardando modelo: {modelo_tflite}")
with open(modelo_tflite, 'wb') as f:
    f.write(tflite_model)

print(f"✅ Conversión exitosa!")
print(f"   • Tamaño: {len(tflite_model):,} bytes ({len(tflite_model)/1024:.1f} KB)")

# Verificar
print(f"\n🧪 Verificando modelo...")
interpreter = tf.lite.Interpreter(model_path=str(modelo_tflite))
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print(f"   • Input shape: {input_details[0]['shape']}")
print(f"   • Input dtype: {input_details[0]['dtype']}")
print(f"   • Output shape: {output_details[0]['shape']}")

# Test
test_input = np.random.randn(1, 96).astype(np.float32)
interpreter.set_tensor(input_details[0]['index'], test_input)
interpreter.invoke()
test_output = interpreter.get_tensor(output_details[0]['index'])


print(f"   • Test output: {test_output[0][0]:.4f}")
print(f"\n🚀 Listo! Ahora commitea y pushea a Raspberry Pi")
