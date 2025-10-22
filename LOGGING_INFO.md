# 📋 Sistema de Logging - App.py

## 📁 Archivos de Log

Los logs se guardan en el archivo `app.log` en el directorio raíz del proyecto.

### Formato de Log
```
2025-10-21 14:30:45,123 [INFO] 🚀 Sincronización automática iniciada exitosamente
2025-10-21 14:31:45,456 [INFO] 📥 Sincronizando Codigos_arduinos/data/sensor_data.csv a la base de datos...
2025-10-21 14:31:46,789 [INFO] ✅ Sincronización completada: 25 registros nuevos agregados
```

---

## 🎯 Niveles de Log

| Nivel | Emoji | Descripción |
|-------|-------|-------------|
| **INFO** | ✅ 🚀 📊 | Operaciones exitosas y eventos normales |
| **DEBUG** | 🔍 📄 | Información detallada para debugging |
| **WARNING** | ⚠️ | Advertencias que no detienen la ejecución |
| **ERROR** | ❌ | Errores que afectan funcionalidad |
| **CRITICAL** | 🔥 | Errores críticos que detienen la app |

---

## 📊 Eventos Registrados

### Inicialización
- ✅ Base de datos inicializada
- 🚀 Sincronización automática iniciada
- 📁 Directorio de trabajo y rutas

### Sincronización Automática
- 🔄 Inicio del proceso de sincronización
- 📥 Lectura del archivo CSV
- ✅ Registros agregados exitosamente
- ⚠️ Archivo CSV no encontrado
- ❌ Errores de lectura o formato

### Endpoints API
- 📄 Carga de página principal
- 📊 Consulta de datos del sensor
- 🔮 Solicitud y proceso de predicciones
- ⚡ Sincronización forzada
- ▶️ Inicio/parada de sincronización

### Errores Capturados
- ❌ Errores de archivo no encontrado (`FileNotFoundError`)
- ❌ Errores de formato de datos (`ValueError`)
- ❌ Errores de base de datos
- ❌ Errores inesperados con stack trace completo

---

## 🔧 API de Logs

### Ver logs en tiempo real

```bash
GET /api/logs?lines=50
```

**Respuesta:**
```json
{
  "status": "ok",
  "total_lines": 150,
  "returned_lines": 50,
  "logs": [
    "2025-10-21 14:30:45,123 [INFO] 🚀 Sincronización automática iniciada",
    "2025-10-21 14:31:45,456 [INFO] ✅ Sincronización completada: 25 registros"
  ]
}
```

**Parámetros:**
- `lines` (opcional): Número de líneas a devolver (default: 50)

**Ejemplos:**
```bash
# Ver últimas 100 líneas
curl http://localhost:5000/api/logs?lines=100

# Ver últimas 50 líneas (default)
curl http://localhost:5000/api/logs
```

---

## 🚨 Monitoreo de Errores

### En consola
Los logs se muestran automáticamente en la consola cuando ejecutas:
```bash
python app.py
```

### En archivo
Revisa el archivo `app.log` con:
```bash
# Ver todo el archivo
cat app.log

# Ver últimas 50 líneas
tail -n 50 app.log

# Seguir logs en tiempo real
tail -f app.log

# Buscar errores
grep ERROR app.log
grep -i "error\|warning" app.log
```

### En Windows PowerShell
```powershell
# Ver últimas 50 líneas
Get-Content app.log -Tail 50

# Seguir logs en tiempo real
Get-Content app.log -Wait -Tail 50

# Buscar errores
Select-String -Path app.log -Pattern "ERROR|WARNING"
```

---

## 🔍 Ejemplos de Logs Comunes

### ✅ Operación Normal
```
2025-10-21 14:30:00,000 [INFO] 🗄️  Inicializando base de datos...
2025-10-21 14:30:01,000 [INFO] ✅ Base de datos inicializada correctamente
2025-10-21 14:30:02,000 [INFO] 🚀 Sincronización automática iniciada exitosamente
2025-10-21 14:30:03,000 [INFO] 🔄 Iniciando sincronización automática cada 60s
2025-10-21 14:31:03,000 [INFO] 📥 Sincronizando CSV a la base de datos...
2025-10-21 14:31:04,000 [INFO] ✅ Sincronización completada: 45 registros nuevos
```

### ⚠️ Archivo CSV No Encontrado
```
2025-10-21 14:32:00,000 [WARNING] ⚠️  Archivo Codigos_arduinos/data/sensor_data.csv no encontrado
```

### ❌ Error de Base de Datos
```
2025-10-21 14:33:00,000 [ERROR] ❌ Error al obtener datos del sensor: database is locked
Traceback (most recent call last):
  File "app.py", line 85, in api_latest_sensor
    data = database.get_latest_sensor_data(limit=limit)
sqlite3.OperationalError: database is locked
```

### 🔮 Predicción Ejecutada
```
2025-10-21 14:35:00,000 [INFO] 🔮 Predicción solicitada para 6 horas futuras
2025-10-21 14:35:01,000 [INFO] 🚀 Iniciando proceso de predicción...
2025-10-21 14:35:30,000 [INFO] 📊 Predicción completada, guardando en DB
2025-10-21 14:35:31,000 [INFO] ✅ Predicciones guardadas exitosamente
```

---

## 🛠️ Configuración Avanzada

### Cambiar nivel de logging

Edita en `app.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Cambiar a DEBUG para más detalle
    # level=logging.INFO,   # INFO (default)
    # level=logging.WARNING, # Solo warnings y errores
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### Rotar logs automáticamente

Para evitar que `app.log` crezca demasiado:
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5  # Mantener 5 archivos
)
```

---

## 📝 Mejores Prácticas

1. **Revisa logs regularmente** en la Raspberry Pi
2. **Monitorea errores** con `grep ERROR app.log`
3. **Usa `/api/logs`** para debugging remoto
4. **Mantén logs limpios** eliminando archivos antiguos periódicamente

---

## 🚀 Comandos Rápidos

```bash
# Ver estado de sincronización
curl http://localhost:5000/api/sync/status

# Ver últimos 20 logs
curl http://localhost:5000/api/logs?lines=20

# Monitorear logs en tiempo real
tail -f app.log

# Buscar solo errores
grep ERROR app.log
```
