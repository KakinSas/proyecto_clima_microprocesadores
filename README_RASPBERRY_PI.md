# Instrucciones para Raspberry Pi Zero 2 W

## ✅ SOLUCIÓN IMPLEMENTADA

Ahora existen **DOS modelos** para máxima compatibilidad:

1. **Modelo Simple TFLite** (⭐ RECOMENDADO PARA RASPBERRY PI):
   - Archivo: `modelo_simple_tflite.tflite`
   - Arquitectura: Dense (sin LSTM)
   - Compatible con: `tflite-runtime` (sin TensorFlow)
   - Ventajas: ✅ Ligero, ✅ Rápido, ✅ Sin dependencias pesadas

2. **Modelo LSTM** (Fallback, requiere TensorFlow):
   - Archivo: `modelo_lstm_3_features (1).h5`
   - Arquitectura: LSTM
   - Requiere: TensorFlow completo
   - Ventajas: ⚡ Mayor precisión temporal

## 🔄 Flujo de Carga del Modelo

El código `predecir_futuro.py` sigue esta estrategia automática:

### Intento 1: Modelo TFLite Simple (PRIORITARIO)
```
🔄 Intentando modelo TFLite simple: modelo_simple_tflite.tflite
✅ Usando tflite_runtime (sin TensorFlow)
✅ Modelo TFLite simple cargado exitosamente
```
- ✅ Funciona con **solo** `tflite-runtime`
- ✅ No requiere TensorFlow
- ✅ Ligero y rápido

### Intento 2: Modelo LSTM .h5 (FALLBACK)
```
🔄 Fallback: Cargando modelo LSTM .h5 con TensorFlow...
✅ Modelo LSTM .h5 cargado exitosamente
```
- ⚠️ Requiere TensorFlow completo
- ⚡ Mayor precisión temporal

## 📦 Instalación en Raspberry Pi

### Opción A: Solo tflite-runtime (⭐ RECOMENDADO - Ligero y rápido)

```bash
cd ~/proyecto/proyecto_clima_microprocesadores
git pull

# 1. Entrenar modelo TFLite simple (HACER EN TU PC, NO EN RASPBERRY)
# Ve a modelos/modelo stefano/ y ejecuta el notebook:
# entrenar_modelo_simple_tflite.ipynb

# 2. Copiar archivos generados a Raspberry Pi (después de entrenar):
# - modelo_simple_tflite.tflite
# - modelo_simple_tflite.h5 (opcional, backup)
# - scaler_4_features_tflite.pkl

# 3. Instalar tflite-runtime en Raspberry Pi
pip3 install tflite-runtime --break-system-packages

# 4. Instalar otras dependencias
pip3 install Flask flask-cors python-dotenv pytz bleak pandas scikit-learn joblib numpy --break-system-packages

# 5. Ejecutar
python3 app.py
```

**Resultado esperado**: 
```
🔄 Intentando modelo TFLite simple: modelo_simple_tflite.tflite
✅ Usando tflite_runtime (sin TensorFlow)
✅ Modelo TFLite simple cargado exitosamente
[PREDICCIONES FUNCIONARÁN ✅]
```

### Opción B: TensorFlow completo (Solo si quieres usar el modelo LSTM)

```bash
cd ~/proyecto/proyecto_clima_microprocesadores
git pull

# Instalar TensorFlow 2.8.0 (tardará 15-20 minutos)
pip3 install tensorflow==2.8.0 --break-system-packages

# Instalar otras dependencias
pip3 install Flask flask-cors python-dotenv pytz bleak pandas scikit-learn joblib numpy --break-system-packages

# Ejecutar
python3 app.py
```

**Resultado esperado**: 
```
🔄 Intentando modelo TFLite simple: modelo_simple_tflite.tflite
✅ Modelo TFLite simple cargado exitosamente
[O si no existe el TFLite simple:]
🔄 Fallback: Cargando modelo LSTM .h5 con TensorFlow...
✅ Modelo LSTM .h5 cargado exitosamente
```

## 🧪 Logs Esperados

### Con solo tflite-runtime:
```
🔄 Intentando cargar modelo TFLite...
✅ Usando tflite_runtime
❌ Error al cargar TFLite: RuntimeError: Encountered unresolved custom op: FlexTensorListReserve
🔄 Fallback: Intentando cargar modelo .h5 con TensorFlow...
❌ Error: Modelo .h5 no encontrado: [path] o tensorflow no instalado
```

### Con TensorFlow completo:
```
🔄 Intentando cargar modelo TFLite...
⚠️  tflite_runtime no disponible, usando tensorflow.lite
❌ Error al cargar TFLite: RuntimeError: Encountered unresolved custom op: FlexTensorListReserve
🔄 Fallback: Intentando cargar modelo .h5 con TensorFlow...
🚀 Cargando modelo Keras (.h5) con TensorFlow completo
✅ Modelo Keras cargado exitosamente
```

## 💾 Consumo de Recursos

### Con TensorFlow 2.8.0:
- **Instalación**: ~500 MB de espacio en disco
- **RAM en reposo**: ~100 MB
- **RAM durante predicción**: ~300-400 MB
- **Tiempo de predicción**: ~2-3 minutos para 6 horas (360 predicciones)

### Frontend configurado:
- **Timeout**: 5 minutos (60 intentos × 5 segundos)
- **Polling**: Cada 5 segundos
- **Mensaje**: Muestra progreso en formato "Xm Ys / 5min"

## 🎯 Recomendación Final

**Instala TensorFlow 2.8.0** en la Raspberry Pi. Aunque el código intentará usar TFLite primero, sabemos que fallará y usará el .h5 como fallback. Es la única forma de que funcione con el modelo LSTM actual.

## 🔧 Soluciones Alternativas (Futuro)

Si el rendimiento es inaceptable:

1. **Re-entrenar sin LSTM**: Usar solo capas Dense/CNN (compatible con TFLite puro)
2. **Arquitectura cliente-servidor**: Raspberry Pi solo recolecta datos, servidor externo predice
3. **Modelo más simple**: Reducir ventana temporal o features
