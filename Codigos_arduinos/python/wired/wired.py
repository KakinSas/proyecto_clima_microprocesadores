import serial
import csv
import os
from datetime import datetime

# Configuración del puerto serial
SERIAL_PORT = "COM5"
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

def main(db_handler=None):
    """Función principal - Lee datos cuando el Arduino los envía"""
    print(f"🔌 Conectando a puerto serial {SERIAL_PORT}...")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✓ Conectado a {SERIAL_PORT}")
        print("⏳ Esperando datos del Arduino (cada 10 minutos)...")
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                
                if line and line.startswith('T:'):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
