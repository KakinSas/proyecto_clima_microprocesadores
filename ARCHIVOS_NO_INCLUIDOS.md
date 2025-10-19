# ⚠️ Archivos No Incluidos en el Repositorio

Por limitaciones de tamaño de GitHub, los siguientes archivos **NO están incluidos** en el repositorio y deben ser generados localmente:

## 📦 Archivos Excluidos (demasiado grandes)

### Modelos Entrenados:
- `modelos/modelo_lstm_3_features.h5` (~75 MB)
- `modelos/modelo_lstm_3_features_best.h5` (~75 MB)
- `modelos/scaler_3_features.pkl` (~2 KB)

### Datasets:
- `modelos/modelo stefano/dataset_ml.csv` (~varios MB)

### Predicciones Generadas:
- `modelos/predicciones_6_horas.csv`
- `modelos/predicciones_6_horas.png`

---

## 🚀 Cómo Generar los Archivos Localmente

### 1. Entrenar el Modelo

```powershell
# Abrir el notebook en VS Code
code modelos/entrenar_modelo_simple.ipynb

# Ejecutar todas las celdas
# Esto generará:
#   - modelo_lstm_3_features.h5
#   - modelo_lstm_3_features_best.h5
#   - scaler_3_features.pkl
```

**Tiempo estimado:** 10-20 minutos (dependiendo de las épocas configuradas)

### 2. Generar Predicciones

```powershell
cd modelos
python predecir_futuro.py

# Esto generará:
#   - predicciones_6_horas.csv
```

**Tiempo estimado:** 5-10 minutos

### 3. Visualizar Resultados

```powershell
python visualizar_predicciones.py

# Esto generará:
#   - predicciones_6_horas.png
```

---

## 💾 Alternativas para Compartir Modelos Grandes

Si necesitas compartir los modelos entrenados con el equipo:

### Opción 1: Google Drive / OneDrive
```
1. Sube los archivos .h5 y .pkl a la nube
2. Comparte el link con el equipo
3. Descarga y coloca en la carpeta modelos/
```

### Opción 2: Git LFS (Git Large File Storage)
```powershell
# Instalar Git LFS
git lfs install

# Trackear archivos grandes
git lfs track "*.h5"
git lfs track "*.pkl"

# Commit y push normal
git add .gitattributes
git commit -m "Add Git LFS tracking"
git push
```

### Opción 3: Releases de GitHub
```
1. Crear un Release en GitHub
2. Adjuntar los archivos .h5 y .pkl como assets
3. El equipo descarga desde la sección Releases
```

---

## 📝 Notas Importantes

- Los archivos `.h5` son demasiado grandes para Git normal (límite ~100 MB)
- El `.gitignore` está configurado para ignorar estos archivos automáticamente
- Cada desarrollador debe entrenar su propio modelo localmente
- El dataset `dataset_ml.csv` debe obtenerse de la fuente original

---

## 🆘 Si Encuentras Problemas

### Error: "Model file not found"
**Solución:** Ejecuta `entrenar_modelo_simple.ipynb` primero

### Error: "Dataset not found"
**Solución:** Asegúrate de tener `dataset_ml.csv` en `modelos/modelo stefano/`

### Error: Git push con archivos grandes
**Solución:** Los archivos ya están en `.gitignore`, verifica que no estén staged:
```powershell
git status
# Si ves archivos .h5 o .pkl, remuévelos:
git rm --cached modelos/*.h5 modelos/*.pkl
```

---

## 📚 Documentación Completa

Para más detalles sobre el sistema de predicción, consulta:
- `modelos/README.md` - Guía completa del sistema LSTM
