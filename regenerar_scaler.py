"""
Regenerar scaler compatible con NumPy 1.x para Raspberry Pi
"""
import joblib
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler

# Rutas
base_dir = Path(__file__).parent
scaler_path = base_dir / "modelos" / "modelo stefano" / "scaler_4_features_tflite.pkl"

print(f"📂 Cargando scaler desde: {scaler_path}")

# Cargar scaler existente
scaler = joblib.load(scaler_path)

print(f"✅ Scaler cargado exitosamente")
print(f"   • mean_: {scaler.mean_}")
print(f"   • scale_: {scaler.scale_}")
print(f"   • n_features_in_: {scaler.n_features_in_}")

# Guardar de nuevo con protocolo compatible
print(f"\n💾 Guardando scaler con protocolo pickle 4 (compatible NumPy 1.x)...")
joblib.dump(scaler, scaler_path, protocol=4)

print(f"✅ Scaler regenerado exitosamente!")
print(f"   • Tamaño: {scaler_path.stat().st_size} bytes")
print(f"\n🚀 Ahora commitea y pushea este archivo a la Raspberry Pi")
