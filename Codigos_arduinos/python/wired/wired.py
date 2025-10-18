import serial
import csv
import re
import os
from datetime import datetime

# Configuración del puerto serial
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 9600

# Ruta al archivo CSV (relativa al directorio del proyecto)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
CSV_FILENAME = os.path.join(PROJECT_DIR, 'data', 'sensor_data.csv')

def parse_registro(line):
    """
    Parsea una línea de registro del formato:
    Registro N - Temp: X.XX °C, Hum: X.XX %, Pres: X.XX kPa
    """
    # Patrón regex para extraer los valores
    pattern = r'Registro\s+(\d+)\s+-\s+Temp:\s+([\d.]+)\s+°C,\s+Hum:\s+([\d.]+)\s+%,\s+Pres:\s+([\d.]+)\s+kPa'
    match = re.match(pattern, line)
    
    if match:
        temp = float(match.group(2))
        hum = float(match.group(3))
        pres = float(match.group(4))
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tipo': 'wired',
            'temperatura': temp,
            'humedad': hum,
            'presion': pres
        }
    return None

def save_to_csv(record):
    """
    Guarda un registro en el archivo CSV
    """
    try:
        # Verificar si el archivo existe
        try:
            with open(CSV_FILENAME, 'r') as f:
                file_exists = True
        except FileNotFoundError:
            file_exists = False
        
        # Abrir archivo en modo append
        with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'tipo', 'temperatura', 'humedad', 'presion']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Escribir encabezado solo si el archivo es nuevo
            if not file_exists:
                writer.writeheader()
            
            # Escribir registro
            writer.writerow(record)
        
    except Exception as e:
        print(f"✗ Error al guardar en CSV: {e}")

def main():
    """
    Función principal que lee del puerto serial y guarda en CSV
    """
    print("="*60)
    print("Script de recepción de datos - Arduino Cableado (Wired)")
    print("="*60)
    print(f"Puerto Serial: {SERIAL_PORT}")
    print(f"Baud Rate: {BAUD_RATE}")
    print(f"Guardando datos en: {CSV_FILENAME}\n")
    
    try:
        # Abrir puerto serial
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✓ Conectado a {SERIAL_PORT}")
        print("Esperando datos...\n")
        
        buffer_count = 0
        registro_count = 0
        
        while True:
            try:
                # Leer línea del serial
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        # Detectar inicio de buffer
                        if "Buffer lleno" in line:
                            buffer_count += 1
                            print(f"\n{'='*60}")
                            print(f"📦 Buffer #{buffer_count} recibido")
                            print(f"{'='*60}")
                            registro_count = 0
                        
                        # Detectar fin de buffer
                        elif "---FIN_BUFFER---" in line:
                            print(f"✓ {registro_count} registros guardados en {CSV_FILENAME}")
                            print()
                        
                        # Parsear y guardar registros
                        else:
                            record = parse_registro(line)
                            if record:
                                registro_count += 1
                                # Mostrar en consola (innecesario)
                                #print(f"Registro {registro_count} - Temp: {record['temperatura']} °C, "
                                #      f"Hum: {record['humedad']} %, Pres: {record['presion']} kPa")
                                
                                # Guardar en CSV
                                save_to_csv(record)
                
            except UnicodeDecodeError:
                # Ignorar errores de decodificación
                pass
                
    except serial.SerialException as e:
        print(f"✗ Error al abrir el puerto serial: {e}")
        print(f"  Asegúrate de que el Arduino esté conectado a {SERIAL_PORT}")
    except KeyboardInterrupt:
        print("\n✓ Programa terminado por el usuario")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("✓ Puerto serial cerrado")

if __name__ == "__main__":
    main()
