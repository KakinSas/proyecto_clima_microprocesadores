"""
Crear scaler desde cero en Raspberry Pi con NumPy 1.x
Ejecutar este script EN LA RASPBERRY PI
"""
import joblib
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler

# Valores del scaler original (obtenidos del regenerar_scaler.py)
mean_values = np.array([16.59037105, 59.48897101, 955.49092561, 11.99185768])
scale_values = np.array([7.80603333, 23.97926202, 3.35269374, 6.92810062])
n_features = 4

# Crear scaler manualmente
scaler = StandardScaler()
scaler.mean_ = mean_values
scaler.scale_ = scale_values
scaler.var_ = scale_values ** 2  # var = scale^2
scaler.n_features_in_ = n_features
scaler.n_samples_seen_ = 1000  # Valor aproximado

# Ruta de salida
output_path = Path("/home/grupo1/proyecto/proyecto_clima_microprocesadores/modelos/modelo stefano/scaler_4_features_tflite.pkl")

# Guardar con NumPy 1.x
print(f"💾 Guardando scaler en: {output_path}")
joblib.dump(scaler, output_path, protocol=4)

print(f"✅ Scaler creado exitosamente con NumPy 1.x!")
print(f"   • Tamaño: {output_path.stat().st_size} bytes")
print(f"   • NumPy version: {np.__version__}")

# Verificar que funciona
print(f"\n🧪 Probando scaler...")
test_data = np.array([[20.0, 60.0, 950.0, 15.0]])
transformed = scaler.transform(test_data)
print(f"   • Test input: {test_data[0]}")
print(f"   • Transformed: {transformed[0]}")
print(f"\n🚀 Listo para usar!")
