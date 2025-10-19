# 📊 Sistema de Predicción de Temperatura con LSTM

Este módulo contiene un sistema completo de predicción de temperatura basado en redes neuronales LSTM (Long Short-Term Memory), diseñado específicamente para trabajar con datos de sensores meteorológicos.

---

## 📁 Estructura de Archivos

```
modelos/
├── entrenar_modelo_simple.ipynb    # Notebook para entrenar el modelo
├── predecir_futuro.py              # Script para predicciones futuras (6 horas)
├── visualizar_predicciones.py      # Script para visualizar resultados
├── modelo_lstm_3_features.h5       # Modelo entrenado (generado)
├── scaler_3_features.pkl           # Normalizador de datos (generado)
├── predicciones_6_horas.csv        # Predicciones generadas (output)
├── predicciones_6_horas.png        # Gráficas de visualización (output)
└── modelo stefano/
    ├── dataset_ml.csv              # Dataset de entrenamiento
    └── trabajo.ipynb               # Notebook original (referencia)
```

---

## 🎯 Flujo de Trabajo Completo

### **Paso 1: Entrenar el Modelo** 🎓

**Archivo:** `entrenar_modelo_simple.ipynb`

#### ¿Qué hace?
Entrena una red neuronal LSTM para predecir temperatura usando solo 3 variables meteorológicas.

#### Proceso detallado:

1. **Carga de Datos**
   - Lee `modelo stefano/dataset_ml.csv` (datos meteorológicos reales)
   - Dataset con separador `;` y 16 columnas originales
   - Selecciona solo 3 columnas relevantes:
     - `ts` - Temperatura del Aire Seco (°C) [OBJETIVO]
     - `hr` - Humedad Relativa (%)
     - `p0` - Presión del Sensor (hPa)

2. **Preprocesamiento**
   - Normaliza los datos con `StandardScaler` (media=0, desviación=1)
   - Crea secuencias de 24 pasos temporales (24 observaciones → 1 predicción)
   - Divide datos: 80% entrenamiento, 20% validación

3. **Arquitectura del Modelo**
   ```
   Entrada: (24 timesteps, 3 features)
        ↓
   LSTM(128 unidades) → Aprende patrones temporales largos
        ↓
   Dropout(0.2) → Previene sobreajuste
        ↓
   LSTM(64 unidades) → Refina patrones temporales
        ↓
   Dropout(0.2) → Regularización adicional
        ↓
   Dense(1) → Predicción final de temperatura
   ```

4. **Entrenamiento**
   - Optimizador: Adam
   - Función de pérdida: MSE (Mean Squared Error)
   - Épocas: Configurable (recomendado: 50-100)
   - Early stopping: Detiene si no mejora en 10 épocas
   - Guarda el mejor modelo automáticamente

5. **Salidas Generadas**
   - `modelo_lstm_3_features.h5` - Modelo entrenado en formato Keras
   - `scaler_3_features.pkl` - Normalizador entrenado con los mismos datos

#### Cómo ejecutar:
```powershell
# Abrir en VS Code y ejecutar todas las celdas
# O usar Jupyter:
jupyter notebook entrenar_modelo_simple.ipynb
```

#### ⚠️ Configuración importante:
En la celda de entrenamiento, ajustar épocas para mejor precisión:
```python
history = modelo.fit(
    X_train, y_train,
    epochs=50,  # Cambiar de 1 a 50-100 para producción
    batch_size=32,
    validation_data=(X_val, y_val),
    callbacks=[early_stopping, checkpoint],
    verbose=1
)
```

---

### **Paso 2: Generar Predicciones Futuras** 🔮

**Archivo:** `predecir_futuro.py`

#### ¿Qué hace?
Genera predicciones de temperatura para las próximas **6 horas** (21,600 predicciones = 1 por segundo).

#### Proceso detallado:

1. **Carga de Recursos**
   - Lee `modelo_lstm_3_features.h5` (modelo entrenado)
   - Lee `scaler_3_features.pkl` (normalizador)
   - Carga últimos datos de `Codigos_arduinos/data/sensor_data.csv`

2. **Mapeo de Columnas**
   ```python
   sensor_data.csv → modelo
   temperatura     → ts (Temperatura)
   humedad         → hr (Humedad Relativa)
   presion         → p0 (Presión)
   ```

3. **Predicción Iterativa** (Técnica de Ventana Deslizante)
   ```
   Iteración 1: [datos históricos: 24 valores] → predicción t+1
   Iteración 2: [datos históricos: 23 valores + predicción t+1] → predicción t+2
   Iteración 3: [datos históricos: 22 valores + pred t+1,t+2] → predicción t+3
   ...
   Iteración 21,600: → predicción t+21600 (6 horas)
   ```

4. **Características Clave**
   - **Progreso en tiempo real**: Muestra % completado cada 10%
   - **Timestamps generados**: Calcula fecha/hora de cada predicción
   - **Manejo de features auxiliares**: Usa últimos valores conocidos de humedad y presión
   - **Desnormalización**: Convierte predicciones normalizadas a °C reales

5. **Salida Generada**
   `predicciones_6_horas.csv`:
   ```csv
   timestamp,temperatura_predicha,segundos_desde_inicio,minutos_desde_inicio,horas_desde_inicio
   2025-10-19 14:30:01,22.45,1,0.02,0.00
   2025-10-19 14:30:02,22.46,2,0.03,0.00
   ...
   2025-10-19 20:30:00,21.89,21600,360.00,6.00
   ```

6. **Estadísticas Generadas**
   - Temperatura mínima predicha
   - Temperatura máxima predicha
   - Temperatura promedio
   - Desviación estándar
   - Cambio total en 6 horas
   - Muestras en +15min, +30min, +1h, +2h, +3h, +6h

#### Cómo ejecutar:
```powershell
cd modelos
python predecir_futuro.py
```

#### Tiempo estimado:
5-10 minutos para 21,600 predicciones

---

### **Paso 3: Visualizar Resultados** 📊

**Archivo:** `visualizar_predicciones.py`

#### ¿Qué hace?
Crea visualizaciones interactivas de las predicciones generadas.

#### Gráficas Generadas:

1. **📈 Serie Temporal Completa**
   - Muestra las 6 horas de predicción
   - Línea de temperatura media como referencia
   - Eje X: Horas desde ahora (0-6)
   - Eje Y: Temperatura (°C)

2. **🔍 Detalle: Primeros 30 Minutos**
   - Zoom en los primeros 30 minutos
   - Marcadores en cada punto para mejor detalle
   - Útil para ver cambios a corto plazo

3. **📊 Distribución de Temperaturas**
   - Histograma con 50 bins
   - Muestra la frecuencia de cada rango de temperatura
   - Línea vertical en la media
   - Útil para detectar patrones o anomalías

4. **📉 Cambio Acumulado**
   - Referencia: Temperatura inicial (t=0)
   - Muestra cuánto aumenta o disminuye la temperatura
   - Áreas coloreadas: rojo=aumento, azul=disminución
   - Útil para ver tendencias

#### Resumen Estadístico por Hora:
```
Hora       Temp Min     Temp Max     Temp Prom    Cambio      
------------------------------------------------------------
0-1h          21.23°C      22.15°C      21.67°C      +0.12°C
1-2h          21.45°C      22.34°C      21.89°C      +0.34°C
2-3h          21.12°C      22.01°C      21.56°C      +0.01°C
...
```

#### Salida Generada:
- **Ventana interactiva**: Gráficas en matplotlib
- **predicciones_6_horas.png**: Imagen guardada (150 DPI)

#### Cómo ejecutar:
```powershell
cd modelos
python visualizar_predicciones.py
```

---

## 🧠 Conceptos Técnicos

### ¿Qué es LSTM?
**Long Short-Term Memory** es un tipo de red neuronal recurrente especializada en:
- Aprender patrones en secuencias temporales
- Recordar información relevante a largo plazo
- Olvidar información irrelevante

**Ideal para:** Series temporales, predicción meteorológica, análisis de tendencias

### ¿Por qué 24 Timesteps?
- Representa 24 observaciones históricas
- En sensor_data.csv: 24 segundos de datos (1 fila/segundo)
- Suficiente contexto para capturar patrones de corto plazo
- Balance entre memoria y capacidad de generalización

### ¿Cómo Funciona la Normalización?
**StandardScaler** transforma los datos:
```python
x_normalizado = (x - media) / desviación_estándar
```

**Ventajas:**
- Acelera el entrenamiento
- Mejora la estabilidad numérica
- Todos los features tienen la misma escala

**Importante:** El mismo scaler debe usarse para entrenar y predecir

### Predicción Iterativa vs. Directa
**Iterativa (usado aquí):**
- Predice 1 paso a la vez
- Usa predicciones anteriores como entrada
- Ventaja: Flexible para cualquier horizonte temporal
- Desventaja: Los errores se acumulan

**Directa (alternativa):**
- Predice múltiples pasos simultáneamente
- No acumula errores
- Desventaja: Necesita reentrenar para cada horizonte

---

## 🔧 Requisitos del Sistema

### Librerías Python:
```bash
pip install tensorflow numpy pandas scikit-learn matplotlib joblib
```

### Versiones recomendadas:
- Python: 3.8 - 3.11
- TensorFlow: 2.x
- NumPy: 1.21+
- Pandas: 1.3+
- scikit-learn: 1.0+

### Hardware:
- **CPU**: Cualquier procesador moderno (entrenamiento ~10-20 min)
- **RAM**: Mínimo 4GB, recomendado 8GB
- **GPU** (opcional): Acelera entrenamiento ~5x con CUDA

---

## 📊 Formato de Datos

### Dataset de Entrenamiento (`dataset_ml.csv`):
```csv
fecha;hora;t;tc;tmax;tmin;hr;pp;vmax10;vv;dv;dmax10;ts;td;qfe1;qfe2;qff;qnh;p0
2023-01-01;00:00:00;15.2;10.1;18.5;12.3;65;0.0;5.2;3.1;180;15.0;14.8;8.9;1013.2;1013.1;1013.5;1014.0;1013.0
...
```

**Columnas usadas:**
- `ts`: Temperatura del Aire Seco (°C) → **OBJETIVO**
- `hr`: Humedad Relativa (%) → Feature
- `p0`: Presión del Sensor (hPa) → Feature

### Datos del Sensor (`sensor_data.csv`):
```csv
temperatura,humedad,presion,timestamp
22.5,60.2,1013.25,2025-10-19 14:30:00
22.6,60.1,1013.30,2025-10-19 14:30:01
...
```

**Frecuencia:** 1 fila por segundo

---

## 🚀 Ejemplo de Uso Completo

```powershell
# 1. Entrenar el modelo (solo una vez, o cuando se actualice el dataset)
# Abrir entrenar_modelo_simple.ipynb y ejecutar todas las celdas

# 2. Generar predicciones para las próximas 6 horas
cd modelos
python predecir_futuro.py

# Salida esperada:
# ✅ Modelo cargado correctamente: modelo_lstm_3_features.h5
# ✅ Scaler cargado correctamente: scaler_3_features.pkl
# ✅ Datos del sensor cargados: 1000 filas
# 
# 🔮 Generando predicciones futuras...
# [10%] 2,160 predicciones - Tiempo transcurrido: 0.5 min
# [20%] 4,320 predicciones - Tiempo transcurrido: 1.0 min
# ...
# [100%] 21,600 predicciones - Tiempo transcurrido: 5.2 min
# 
# 📊 ESTADÍSTICAS:
#    Temperatura mínima: 21.23°C
#    Temperatura máxima: 22.89°C
#    Temperatura promedio: 22.05°C
# 
# 💾 Predicciones guardadas en: predicciones_6_horas.csv

# 3. Visualizar resultados
python visualizar_predicciones.py

# Salida esperada:
# ✅ Cargadas 21,600 predicciones
#    Desde: 2025-10-19 14:30:01
#    Hasta: 2025-10-19 20:30:00
# 
# 📊 RESUMEN POR HORA:
# Hora       Temp Min     Temp Max     Temp Prom    Cambio      
# ------------------------------------------------------------
# 0-1h          21.23°C      22.15°C      21.67°C      +0.12°C
# ...
# 
# 💾 Gráfica guardada en: predicciones_6_horas.png
# ✅ Visualización completada
```

---

## ⚠️ Solución de Problemas

### Error: "No module named 'tensorflow'"
```powershell
pip install tensorflow
```

### Error: "Model file not found"
**Causa:** No se ha entrenado el modelo  
**Solución:** Ejecutar `entrenar_modelo_simple.ipynb` primero

### Error: "Predictions file not found" (visualizar_predicciones.py)
**Causa:** No se han generado predicciones  
**Solución:** Ejecutar `predecir_futuro.py` primero

### Predicciones constantes o poco realistas
**Causas posibles:**
1. Modelo entrenado con muy pocas épocas (ej: epochs=1)
2. Dataset insuficiente
3. Datos de entrada fuera del rango de entrenamiento

**Solución:**
- Aumentar épocas a 50-100 en el notebook
- Verificar que sensor_data.csv tenga valores razonables
- Reentrenar el modelo con más datos históricos

### Proceso muy lento en CPU
**Normal:** 21,600 predicciones toman 5-10 minutos en CPU  
**Acelerar:**
- Usar GPU con TensorFlow-GPU
- Reducir horizonte de predicción
- Optimizar batch size

---

## 📈 Mejoras Futuras

### Corto Plazo:
- [ ] Integración con API en tiempo real (`app.py`)
- [ ] Predicciones de humedad y presión adicionales
- [ ] Intervalos de confianza (±error)
- [ ] Exportar a JSON para frontend

### Mediano Plazo:
- [ ] Modelo con más features (velocidad viento, radiación solar)
- [ ] Predicciones multi-paso directas (sin iteración)
- [ ] Comparación con otros modelos (ARIMA, Prophet, GRU)
- [ ] Validación cruzada temporal

### Largo Plazo:
- [ ] Transfer learning con datos de otras estaciones
- [ ] Ensemble de múltiples modelos
- [ ] Explicabilidad con SHAP/LIME
- [ ] Detección de anomalías

---

## 📚 Referencias

- [TensorFlow Time Series Tutorial](https://www.tensorflow.org/tutorials/structured_data/time_series)
- [LSTM Networks - Understanding](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)
- [Scikit-learn StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html)

---

## 👥 Autores

**Proyecto:** Sistema de Monitoreo Climático con Microprocesadores  
**Curso:** Microprocesadores - Semestre 8  
**Universidad:** UNAB  
**Fecha:** Octubre 2025

---

## 📝 Notas Adicionales

### Diferencias con `modelo stefano/trabajo.ipynb`:
- Modelo original: 15 features, más complejo
- Modelo simple: 3 features, optimizado para sensor básico
- Mismo dataset base, columnas reducidas
- Misma arquitectura LSTM, ajustada a menos inputs

### ¿Cuándo Reentrenar?
- Cada 1-2 meses con nuevos datos históricos
- Si las predicciones se vuelven inexactas
- Al cambiar el sensor o ubicación
- Si cambian las condiciones climáticas regionales

### Backup Recomendado:
Guardar regularmente:
- `modelo_lstm_3_features.h5`
- `scaler_3_features.pkl`
- `dataset_ml.csv` actualizado
- Configuración de entrenamiento (epochs, batch_size, etc.)

---

**¿Preguntas o problemas?** Consulta el código fuente con comentarios detallados en cada archivo.
