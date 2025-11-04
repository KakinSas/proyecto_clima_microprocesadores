import serial
import csv
import os
from datetime import datetime

# Configuración del puerto serial
SERIAL_PORT = "/dev/ttyACM0"  # Puerto para Raspberry Pi (cambiar a COM5 en Windows)
BAUD_RATE = 9600

# Ruta al archivo CSV (relativa al directorio del proyecto)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
CSV_FILENAME = os.path.join(PROJECT_DIR, 'data', 'sensor_data.csv')

def parse_sensor_data(line):
    """
    Parsea la línea de datos del sensor
    Formato esperado: T:25.5,H:60.0,P:1013.25
    """
    try:
        parts = line.split(',')
        data = {}
        for part in parts:
            key, value = part.split(':')
            data[key.strip()] = float(value.strip())
        
        return {
            'temperature': data.get('T', 0),
            'humidity': data.get('H', 0),
            'pressure': data.get('P', 0)
        }
    except Exception as e:
        print(f"✗ Error parseando datos: {e}")
        return None

def save_to_csv(data, source, timestamp):
    """Guarda los datos en CSV local"""
    try:
        # Crear carpeta data si no existe
        os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)
        
        file_exists = os.path.isfile(CSV_FILENAME)
        
        with open(CSV_FILENAME, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'source', 'temperature', 'humidity', 'pressure'])
            
            writer.writerow([
                timestamp,
                source,
                data['temperature'],
                data['humidity'],
                data['pressure']
            ])
    except Exception as e:
        print(f"✗ Error guardando en CSV: {e}")

def should_accept_sample():
    """Verifica si estamos en un minuto válido para tomar muestras (10, 20, 30, 40, 50, 00)"""
    now = datetime.now()
    minute = now.minute
    return minute % 10 == 0

def main(db_handler=None):
    """Función principal - Lee datos cuando el Arduino los envía"""
    print(f"🔌 Conectando a puerto serial {SERIAL_PORT}...")
    
    last_accepted_minute = -1
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✓ Conectado a {SERIAL_PORT}")
        print("⏳ Esperando minutos válidos (xx:00, xx:10, xx:20, xx:30, xx:40, xx:50)...")
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                
                if line and line.startswith('T:'):
                    now = datetime.now()
                    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
                    current_minute = now.minute
                    
                    # Verificar si estamos en un minuto válido
                    if should_accept_sample() and current_minute != last_accepted_minute:
                        print(f"📥 WIRED [{timestamp}]: {line}")
                        
                        # Parsear los datos
                        data = parse_sensor_data(line)
                        
                        if data:
                            # Agregar al buffer de MongoDB
                            if db_handler:
                                db_handler.add_sample_to_buffer(
                                    source='wired',
                                    temperature=data['temperature'],
                                    humidity=data['humidity'],
                                    pressure=data['pressure']
                                )
                            
                            # Guardar en CSV local (opcional)
                            save_to_csv(data, 'wired', timestamp)
                            
                            last_accepted_minute = current_minute
                    else:
                        print(f"⏭️ WIRED [{timestamp}]: Dato ignorado (minuto {current_minute:02d} no válido)")
                    
    except serial.SerialException as e:
        print(f"✗ Error de conexión serial: {e}")
        raise
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        raise
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("✓ Puerto serial cerrado")

if __name__ == "__main__":
    main()
