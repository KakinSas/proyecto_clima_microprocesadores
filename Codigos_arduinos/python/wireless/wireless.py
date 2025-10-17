import asyncio
import struct
import csv
import os
from datetime import datetime
from bleak import BleakClient, BleakScanner

# UUID del servicio y característica
SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"
BUFFER_CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"

# Ruta al archivo CSV (relativa al directorio del proyecto)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
CSV_FILENAME = os.path.join(PROJECT_DIR, 'data', 'sensor_data.csv')

# Variable para almacenar el cliente
client = None

def process_buffer_data(buffer_data):
    """
    Procesa el buffer de datos y extrae temperatura, humedad y presión
    Cada registro tiene 12 bytes: 4 bytes temp + 4 bytes hum + 4 bytes pres
    """
    record_size = 12  # 3 floats de 4 bytes cada uno
    num_records = len(buffer_data) // record_size
    
    records = []
    for i in range(num_records):
        offset = i * record_size
        
        # Extraer los 3 floats (temperatura, humedad, presión)
        temp = struct.unpack('<f', buffer_data[offset:offset+4])[0]
        hum = struct.unpack('<f', buffer_data[offset+4:offset+8])[0]
        pres = struct.unpack('<f', buffer_data[offset+8:offset+12])[0]
        
        records.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tipo': 'wireless',
            'temperatura': round(temp, 2),
            'humedad': round(hum, 2),
            'presion': round(pres, 2)
        })
    
    return records

def save_to_csv(records):
    """
    Guarda los registros en un archivo CSV
    """
    try:
        # Crear carpeta data si no existe
        os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)
        
        # Verificar si el archivo existe para agregar encabezado
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
            
            # Escribir registros
            for record in records:
                writer.writerow(record)
        
        print(f"✓ {len(records)} registros guardados en {CSV_FILENAME}")
        
    except Exception as e:
        print(f"✗ Error al guardar en CSV: {e}")

def notification_handler(sender, data):
    """
    Manejador de notificaciones cuando el buffer se actualiza
    """
    print(f"\n{'='*50}")
    print(f"Buffer recibido: {len(data)} bytes")
    print(f"{'='*50}")
    
    # Procesar datos
    records = process_buffer_data(data)
    
    # Mostrar en consola
    print(f"\nProcesando datos del buffer...")
    for i, record in enumerate(records, 1):
        print(f"Registro {i} - Temp: {record['temperatura']} °C, "
              f"Hum: {record['humedad']} %, Pres: {record['presion']} kPa")
    
    # Guardar en CSV
    save_to_csv(records)
    print()

async def find_arduino():
    """
    Busca el dispositivo ArduinoEsclavo
    """
    print("Buscando ArduinoEsclavo...")
    devices = await BleakScanner.discover()
    
    for device in devices:
        if device.name == "ArduinoEsclavo":
            print(f"✓ ArduinoEsclavo encontrado: {device.address}")
            return device.address
    
    print("✗ ArduinoEsclavo no encontrado")
    return None

async def connect_and_receive():
    """
    Conecta al Arduino y recibe datos
    """
    global client
    
    # Buscar dispositivo
    address = await find_arduino()
    if not address:
        return
    
    # Conectar
    try:
        async with BleakClient(address) as client:
            print(f"✓ Conectado a ArduinoEsclavo")
            
            # Suscribirse a notificaciones
            await client.start_notify(BUFFER_CHAR_UUID, notification_handler)
            print(f"✓ Suscrito a notificaciones del buffer")
            print(f"Esperando datos...\n")
            
            # Mantener conexión abierta
            while True:
                if not client.is_connected:
                    print("✗ Desconectado")
                    break
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"✗ Error: {e}")

async def main():
    """
    Función principal
    """
    print("="*50)
    print("Script de recepción de datos - ArduinoEsclavo")
    print("="*50)
    print(f"Guardando datos en: {CSV_FILENAME}\n")
    
    try:
        await connect_and_receive()
    except KeyboardInterrupt:
        print("\n✓ Programa terminado por el usuario")

if __name__ == "__main__":
    asyncio.run(main())
