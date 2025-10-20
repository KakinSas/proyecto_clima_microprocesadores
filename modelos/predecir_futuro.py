"""
Script para predecir las siguientes 6 horas de temperatura
usando el modelo LSTM entrenado con 3 features (ts, hr, p0).

El script toma los últimos datos de sensor_data.csv y genera
predicciones iterativas hacia el futuro.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore", category=FutureWarning)
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

def main():
    # Rutas
    base_dir = Path(__file__).resolve().parent
    model_path = base_dir / "modelo_lstm_3_features(1).h5"
    scaler_path = base_dir / "scaler_4_features.pkl"
    csv_path = base_dir.parent / "Codigos_arduinos" / "data" / "sensor_data.csv"
    
    print("=" * 70)
    print("🔮 PREDICCIÓN DE TEMPERATURA A FUTURO (6 HORAS)")
    print("=" * 70)
    
    # 1. Verificar archivos
    if not model_path.exists():
        print(f"\n❌ Modelo no encontrado: {model_path}")
        print(f"\n💡 Por favor, entrena el modelo primero ejecutando:")
        print(f"   Abre y ejecuta: entrenar_modelo_simple.ipynb")
        sys.exit(1)
    
    if not scaler_path.exists():
        print(f"❌ Scaler no encontrado: {scaler_path}")
        print(f"\n💡 Por favor, entrena el modelo primero.")
        sys.exit(1)
    
    if not csv_path.exists():
        print(f"❌ CSV no encontrado: {csv_path}")
        sys.exit(1)
    
    print(f"✅ Modelo: {model_path.name}")
    print(f"✅ Scaler: {scaler_path.name}")
    print(f"✅ Datos: {csv_path}")
    
    # 2. Cargar modelo
    try:
        import tensorflow as tf
        from tensorflow import keras
        model = keras.models.load_model(model_path, compile=False)
        print(f"\n✅ Modelo cargado correctamente")
        print(f"   Entrada: {model.input_shape}")
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        sys.exit(1)
    
    # 3. Cargar scaler
    try:
        import joblib
        scaler = joblib.load(scaler_path)
        print(f"✅ Scaler cargado")
    except Exception as e:
        print(f"❌ Error cargando scaler: {e}")
        sys.exit(1)
    
    # 4. Cargar CSV
    print(f"\n📊 Cargando datos...")
    df = pd.read_csv(csv_path)
    print(f"   Total de registros (raw): {len(df):,}")

    # Intentar parsear timestamp y resamplear a 1 minuto (promediando cada ~60s)
    # Notas: los datos originales tienen un registro por segundo, pero hay 12 datos por segundo
    # según la descripción; para obtener 1 dato por minuto se toma la media de los 60*12=720 registros
    # por minuto si corresponde. Aquí manejamos casos donde la densidad no sea exacta usando resample.
    if 'timestamp' in df.columns:
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')

            # Si hay múltiples columnas no-numéricas, se intentará convertir sólo las features necesarias
            # Resample a 1 minuto y tomar la media. Esto producirá 1 fila por minuto.
            df_min = df.resample('1T').mean()

            # Eliminar filas NaN que puedan aparecer por huecos
            df_min = df_min.dropna()

            print(f"   Registros después de resample a 1 minuto: {len(df_min):,}")
            df = df_min.reset_index()
        except Exception as e:
            print(f"   ⚠️ Error al parsear/resamplear timestamps: {e}")
            print("   Usando los datos raw sin resampleo")
    else:
        print("   ⚠️ No hay columna 'timestamp' en el CSV; usando datos sin resampleo")
    
    # Mapeo de columnas: sensor_data.csv → modelo (ts, hr, p0)
    feature_mapping = {
        'temperatura': 'ts',  # Temperatura del aire seco
        'humedad': 'hr',      # Humedad relativa
        'presion': 'p0'       # Presión del sensor
    }
    
    # Verificar columnas
    missing = [col for col in feature_mapping.keys() if col not in df.columns]
    if missing:
        print(f"❌ Columnas faltantes: {missing}")
        sys.exit(1)
    
    # Extraer features y mapear nombres
    X_raw = df[list(feature_mapping.keys())].astype(float).to_numpy()
    print(f"   Features: {list(feature_mapping.keys())}")
    print(f"   Mapeadas a: {list(feature_mapping.values())}")
    
    # 5. Configuración de predicción
    n_pasos = 24  # Ventana de tiempo que usa el modelo (ahora cada paso es 1 minuto)
    horas_futuro = 6
    minutos_por_hora = 60
    n_predicciones = horas_futuro * minutos_por_hora  # 1 predicción por minuto
    
    print(f"\n⚙️  CONFIGURACIÓN DE PREDICCIÓN")
    print(f"   Ventana temporal (timesteps): {n_pasos}")
    print(f"   Horas a predecir: {horas_futuro}")
    print(f"   Predicciones totales: {n_predicciones:,} (1 por minuto)")
    
    # 6. Verificar que hay suficientes datos
    if len(X_raw) < n_pasos:
        print(f"\n❌ Datos insuficientes. Se necesitan al menos {n_pasos} registros (1 por minuto después del resample)")
        sys.exit(1)
    
    # 7. Escalar datos históricos
    X_scaled = scaler.transform(X_raw)
    
    # 8. Obtener la última ventana disponible
    ultima_ventana = X_scaled[-n_pasos:].copy()  # Últimos 24 registros
    
    print(f"\n🔄 Generando predicciones iterativas...")
    print(f"   (Esto debería ser rápido: {n_predicciones:,} predicciones por minuto)")
    
    # 9. Predicción iterativa
    predicciones_temp = []
    ventana_actual = ultima_ventana.copy()
    
    # Para progreso
    progreso_cada = n_predicciones // 10 if n_predicciones >= 10 else 1
    
    for i in range(n_predicciones):
        # Mostrar progreso
        if (i + 1) % progreso_cada == 0 or i == 0:
            progreso = ((i + 1) / n_predicciones) * 100
            print(f"   Progreso: {progreso:.1f}% ({i+1:,}/{n_predicciones:,})")
        
    # Preparar entrada para el modelo (1, n_pasos, 3)
        X_input = ventana_actual.reshape(1, n_pasos, 3)
        
        # Predecir siguiente valor (temperatura escalada)
        pred_scaled = model.predict(X_input, verbose=0)[0][0]
        
        # Para la siguiente predicción, necesitamos estimar hr y p0
        # Usamos los últimos valores conocidos como aproximación
        ultima_hr_scaled = ventana_actual[-1, 1]
        ultima_p0_scaled = ventana_actual[-1, 2]
        
        # Crear el nuevo registro escalado [ts_pred, hr_last, p0_last]
        nuevo_registro_scaled = np.array([pred_scaled, ultima_hr_scaled, ultima_p0_scaled])
        
        # Actualizar ventana: eliminar el primero, agregar el nuevo al final
        ventana_actual = np.vstack([ventana_actual[1:], nuevo_registro_scaled])
        
        # Guardar predicción escalada
        predicciones_temp.append(pred_scaled)
    
    print(f"   ✅ Predicción completada: {len(predicciones_temp):,} valores")
    
    # 10. Desescalar predicciones
    print(f"\n📈 Convirtiendo a temperatura real...")
    
    # Crear array dummy para inverse_transform
    predicciones_array = np.array(predicciones_temp).reshape(-1, 1)
    dummy = np.zeros((len(predicciones_array), 3))
    dummy[:, 0] = predicciones_array.flatten()
    
    # Usar hr y p0 del último registro como referencia
    dummy[:, 1] = X_scaled[-1, 1]
    dummy[:, 2] = X_scaled[-1, 2]
    
    predicciones_reales = scaler.inverse_transform(dummy)[:, 0]
    
    # 11. Crear timestamps para las predicciones
    print(f"\n📅 Generando timestamps...")
    
    if 'timestamp' in df.columns:
        try:
            ultimo_timestamp = pd.to_datetime(df['timestamp'].iloc[-1])
            print(f"   Último timestamp en dataset: {ultimo_timestamp}")
        except:
            ultimo_timestamp = datetime.now()
            print(f"   Usando timestamp actual: {ultimo_timestamp}")
    else:
        ultimo_timestamp = datetime.now()
        print(f"   No hay columna timestamp, usando: {ultimo_timestamp}")
    
    # Generar timestamps futuros (1 por minuto)
    timestamps_futuros = [ultimo_timestamp + timedelta(minutes=i+1) for i in range(n_predicciones)]
    
    # 12. Crear DataFrame de resultados
    resultado_df = pd.DataFrame({
        'timestamp': timestamps_futuros,
        'temperatura_predicha': predicciones_reales,
        'segundos_desde_inicio': [ (i+1)*60 for i in range(n_predicciones)],
        'minutos_desde_inicio': range(1, n_predicciones + 1),
        'horas_desde_inicio': [(i + 1) / 60 for i in range(n_predicciones)]
    })
    
    # 13. Guardar resultados
    output_path = base_dir / "predicciones_6_horas.csv"
    resultado_df.to_csv(output_path, index=False)
    print(f"\n💾 Predicciones guardadas en: {output_path.name}")
    
    # 14. Estadísticas y resumen
    print(f"\n" + "=" * 70)
    print("📊 RESUMEN DE PREDICCIONES")
    print("=" * 70)
    
    ultima_temp_real = df['temperatura'].iloc[-1]
    primera_pred = predicciones_reales[0]
    ultima_pred = predicciones_reales[-1]
    temp_min = predicciones_reales.min()
    temp_max = predicciones_reales.max()
    temp_media = predicciones_reales.mean()
    temp_std = predicciones_reales.std()
    
    print(f"\n🌡️  Temperatura actual (última en dataset): {ultima_temp_real:.2f} °C")
    print(f"🔮 Primera predicción (+1s):               {primera_pred:.2f} °C")
    print(f"🔮 Última predicción (+6h):                {ultima_pred:.2f} °C")
    print(f"\n📈 Estadísticas de las próximas 6 horas:")
    print(f"   Temperatura mínima:    {temp_min:.2f} °C")
    print(f"   Temperatura máxima:    {temp_max:.2f} °C")
    print(f"   Temperatura promedio:  {temp_media:.2f} °C")
    print(f"   Desviación estándar:   {temp_std:.2f} °C")
    
    # Cambio total
    cambio_total = ultima_pred - ultima_temp_real
    print(f"\n📊 Cambio predicho en 6 horas: {cambio_total:+.2f} °C")
    
    # 15. Muestras de predicciones en diferentes momentos
    print(f"\n🔍 MUESTRAS DE PREDICCIONES:")
    print(f"\n{'Tiempo':<15} {'Timestamp':<20} {'Temp (°C)':<10}")
    print("-" * 50)
    
    momentos = [
        (0, "Inicio (+1min)"),
        (15-1, "+15 minutos"),
        (30-1, "+30 minutos"),
        (60-1, "+1 hora"),
        (60*2-1, "+2 horas"),
        (60*3-1, "+3 horas"),
        (60*6-1, "+6 horas")
    ]
    
    for idx, label in momentos:
        if idx < len(resultado_df):
            ts = resultado_df.iloc[idx]['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            temp = resultado_df.iloc[idx]['temperatura_predicha']
            print(f"{label:<15} {ts:<20} {temp:>8.2f}")
    
    print(f"\n" + "=" * 70)
    print("✅ Proceso completado exitosamente")
    print("=" * 70)
    
    print(f"\n💡 Puedes visualizar los resultados con:")
    print(f"   python visualizar_predicciones.py")

if __name__ == "__main__":
    main()
