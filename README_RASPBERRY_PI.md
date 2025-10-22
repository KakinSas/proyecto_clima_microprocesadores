# Instrucciones para Raspberry Pi Zero 2 W

## ⚠️ ADVERTENCIA IMPORTANTE

El modelo LSTM utilizado en este proyecto contiene operaciones **Flex** que requieren TensorFlow completo para funcionar. Aunque el código intentará usar TensorFlow Lite primero, **fallará** con este error:

```
RuntimeError: Encountered unresolved custom op: FlexTensorListReserve
Node number 0 (FlexTensorListReserve) failed to prepare.
```

## 🔄 Flujo de Carga del Modelo

El código `predecir_futuro.py` sigue esta estrategia:

1. **Intento 1**: Cargar `modelo_lstm_3_features.tflite` con `tflite-runtime`
   - ❌ **Fallará** por operaciones Flex
   
2. **Intento 2**: Cargar `modelo_lstm_3_features.tflite` con `tensorflow.lite`
   - ❌ **Fallará** si TensorFlow no está instalado
   
3. **Fallback**: Cargar `modelo_lstm_3_features (1).h5` con TensorFlow completo
   - ✅ **Funcionará** si TensorFlow está instalado

## 📦 Instalación en Raspberry Pi

### Opción A: Solo tflite-runtime (FALLARÁ, pero lo intentará)

```bash
cd ~/proyecto/proyecto_clima_microprocesadores
git pull

# Instalar tflite-runtime (funcionará la instalación)
pip3 install tflite-runtime --break-system-packages

# Instalar otras dependencias
pip3 install Flask flask-cors python-dotenv pytz bleak pandas scikit-learn joblib numpy --break-system-packages

# Ejecutar (fallará al predecir, mostrará error de Flex ops)
python3 app.py
```

**Resultado esperado**: El servidor Flask arrancará, pero las predicciones fallarán con:
```
❌ Error al cargar TFLite: RuntimeError: Encountered unresolved custom op: FlexTensorListReserve
❌ Modelo .h5 no encontrado o TensorFlow no instalado
```

### Opción B: TensorFlow completo (RECOMENDADO, funcionará)

```bash
cd ~/proyecto/proyecto_clima_microprocesadores
git pull

# Instalar TensorFlow 2.8.0 (tardará 15-20 minutos)
pip3 install tensorflow==2.8.0 --break-system-packages

# Instalar otras dependencias
pip3 install Flask flask-cors python-dotenv pytz bleak pandas scikit-learn joblib numpy --break-system-packages

# Ejecutar (funcionará completamente)
python3 app.py
```

**Resultado esperado**: 
```
🔄 Intentando cargar modelo TFLite...
❌ Error al cargar TFLite: RuntimeError: Encountered unresolved custom op...
🔄 Fallback: Intentando cargar modelo .h5 con TensorFlow...
✅ Modelo Keras cargado exitosamente
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
