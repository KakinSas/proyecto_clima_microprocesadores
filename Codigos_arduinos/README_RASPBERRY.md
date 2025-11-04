# Instrucciones para Raspberry Pi

## 1. Instalación de Dependencias

```bash
# Instalar pymongo y numpy
pip3 install pymongo numpy pyserial bleak

# O si usas el entorno virtual
source venv/bin/activate
pip install pymongo numpy pyserial bleak
```

## 2. Compilar y Subir Arduino (Wired)

```bash
# Compilar y subir el código al Arduino Nano 33 BLE
arduino-cli compile --fqbn arduino:mbed_nano:nano33ble slave_wired/slave_wired.ino --upload -p /dev/ttyACM0
```

## 3. Compilar y Subir Arduino (Wireless)

```bash
# Compilar y subir el código al Arduino Nano 33 BLE
arduino-cli compile --fqbn arduino:mbed_nano:nano33ble slave_wireless/slave_wireless.ino --upload -p /dev/ttyACM1
```

## 4. Ejecutar el Sistema

```bash
# Opción 1: Ejecutar directamente
python3 python/main.py

# Opción 2: Ejecutar con supervisión (reinicio automático ante fallos)
python3 python/main.py &

# Opción 3: Ejecutar en background con nohup
nohup python3 python/main.py > output.log 2>&1 &

# Ver el proceso
ps aux | grep main.py

# Ver logs en tiempo real
tail -f output.log
```

## 5. Detener el Sistema

```bash
# Encontrar el proceso
ps aux | grep main.py

# Matar el proceso (reemplaza PID con el número del proceso)
kill -9 PID
```

## 6. Estructura del Sistema

```
Codigos_arduinos/
├── slave_wired/
│   └── slave_wired.ino          # Arduino conectado por cable (cada 10 min)
├── slave_wireless/
│   └── slave_wireless.ino       # Arduino conectado por Bluetooth (cada 10 min)
├── python/
│   ├── main.py                  # Programa principal
│   ├── db/
│   │   └── mongodb_handler.py   # Gestor de MongoDB con buffer horario
│   ├── wired/
│   │   └── wired.py            # Lector serial (puerto /dev/ttyACM0)
│   └── wireless/
│       └── wireless.py         # Lector Bluetooth
└── data/
    └── sensor_data.csv         # Datos individuales (backup local)
```

## 7. Funcionamiento del Sistema

### Arduinos:
- **Envían datos cada 10 minutos** en formato: `T:25.5,H:60.0,P:1013.25`
- El wired envía por Serial
- El wireless envía por Bluetooth BLE

### Python:
- **Recibe datos** de ambos Arduinos
- **Guarda en CSV local** cada dato individual
- **Buffer sincronizado por hora**: Acumula datos durante cada hora del reloj (15:00-15:59, 16:00-16:59, etc.)
- **Procesamiento automático al cambio de hora**: Al llegar a las 16:00, procesa datos de las 15:xx automáticamente
- **Promedio horario**: Calcula promedio y sube a MongoDB
- **Interpolación**: Si faltan datos (5 en vez de 6), interpola linealmente
- **Detección de fallos**: Si hay <5 datos al cambiar la hora, marca como N/A

### MongoDB:
- **Promedios horarios** con status OK o FAILURE
- **N/A automático** cuando hay fallos de sensor
- **Registro completo** de start_time, end_time, muestras recibidas

## 8. Verificar Funcionamiento

```bash
# Ver datos en CSV
tail -20 data/sensor_data.csv

# Verificar conexión serial
ls -l /dev/ttyACM*

# Ver dispositivos Bluetooth
sudo hcitool lescan

# Monitorear salida del programa
tail -f output.log
```

## 9. Troubleshooting

### Error: Puerto serial ocupado
```bash
# Ver qué proceso está usando el puerto
lsof /dev/ttyACM0

# Matar ese proceso
kill -9 PID
```

### Error: No se encuentra dispositivo Bluetooth
```bash
# Reiniciar Bluetooth
sudo systemctl restart bluetooth

# Escanear dispositivos
sudo hcitool lescan

# Verificar que el Arduino wireless esté encendido
```

### Error: MongoDB no conecta
```bash
# Verificar conexión a internet
ping google.com

# Verificar que dnspython esté instalado
pip3 list | grep dnspython

# Si no está instalado:
pip3 install --user dnspython

# El sistema hará 3 intentos con timeout de 30 segundos
# Si falla, continuará funcionando y guardando solo en CSV local
# Verás: "⚠️ El sistema continuará funcionando sin MongoDB"
```

## 10. Configuración Automática al Inicio

Para que se ejecute al iniciar la Raspberry Pi:

```bash
# Editar crontab
crontab -e

# Agregar esta línea al final:
@reboot sleep 60 && cd /home/grupo1/proyecto/proyecto_clima_microprocesadores/Codigos_arduinos && python3 python/main.py > /home/grupo1/proyecto/output.log 2>&1
```

## 11. Variables de Configuración

### Para cambiar puerto serial (wired.py):
```python
SERIAL_PORT = "/dev/ttyACM0"  # Cambiar si es necesario
```

### Para cambiar intervalo de muestreo (slave_wired.ino y slave_wireless.ino):
```cpp
const unsigned long INTERVALO_LECTURA = 600000; // 10 min = 600,000 ms
```

### MongoDB URI (main.py):
```python
MONGODB_URI = "mongodb+srv://benjotenks:msfaObufcIQ6IP6d@cluster0.d18af.mongodb.net/microprocesadores"
```
