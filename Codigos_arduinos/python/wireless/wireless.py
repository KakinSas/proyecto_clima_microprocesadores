import asyncio
import struct
import csv
import os
from datetime import datetime
from bleak import BleakClient, BleakScanner
from typing import Optional, List

# UUID del servicio y característica
SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"
BUFFER_CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
TARGET_NAME = "ArduinoEsclavo"

# Ruta al archivo CSV (relativa al directorio del proyecto)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
CSV_FILENAME = os.path.join(PROJECT_DIR, 'data', 'sensor_data.csv')

# Estado de la dirección/MAC conocida (puede cambiar en BLE)
known_address: Optional[str] = None

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
        # Mostrar en consola (innecesario por el momento)
        #print(f"Registro {i} - Temp: {record['temperatura']} °C, "
        #      f"Hum: {record['humedad']} %, Pres: {record['presion']} kPa")
        pass 
    # Guardar en CSV
    save_to_csv(records)
    print()

async def find_arduino(timeout: float = 8.0):
    """
    Busca el dispositivo por nombre y (si es posible) por UUID de servicio.
    Devuelve el objeto BLEDevice si lo encuentra, de lo contrario None.
    """
    print(f"🔎 Buscando {TARGET_NAME}...")
    candidates = await BleakScanner.discover(timeout=timeout)

    # Filtrar por nombre (algunos dispositivos pueden publicar None como nombre)
    named: List = [d for d in candidates if (d.name or '').strip() == TARGET_NAME]

    if not named:
        print("✗ Dispositivo no encontrado en este escaneo")
        return None

    # Priorizar los que anuncian el servicio esperado si está disponible en metadata
    def has_service(d) -> int:
        try:
            uuids = (d.metadata or {}).get('uuids') or []
            return 1 if SERVICE_UUID.lower() in [u.lower() for u in uuids] else 0
        except Exception:
            return 0

    # Orden: primero con servicio, luego por RSSI más fuerte
    named.sort(key=lambda d: (has_service(d), getattr(d, 'rssi', -9999)), reverse=True)
    device = named[0]

    print(f"✓ {TARGET_NAME} candidato: {device.address} (RSSI {getattr(device, 'rssi', 'NA')})")
    return device

async def connect_and_receive():
    """
    Conecta al Arduino y recibe datos, verificando cambios de MAC y reconectando automáticamente.
    """
    global known_address

    backoff = 2  # segundos, con tope
    max_backoff = 30

    while True:
        try:
            device = await find_arduino(timeout=8)
            if not device:
                # Incrementar backoff cuando no se encuentra
                print(f"⏳ Reintentando escaneo en {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(max_backoff, backoff * 2)
                continue

            # Verificar cambio de MAC/dirección
            if known_address and device.address != known_address:
                print(f"⚠ Dirección/MAC cambió: {known_address} → {device.address}")
            elif not known_address:
                print(f"✓ Dirección/MAC inicial: {device.address}")
            else:
                print(f"✓ Dirección/MAC coincide: {device.address}")

            known_address = device.address

            disconnected_event = asyncio.Event()

            def _on_disconnect(_client):
                print("✗ Desconectado del dispositivo (evento)")
                try:
                    disconnected_event.set()
                except Exception:
                    pass

            print("🔗 Intentando conectar...")
            async with BleakClient(known_address, disconnected_callback=_on_disconnect) as client:
                # Confirmación de conexión
                if not client.is_connected:
                    raise RuntimeError("No se pudo establecer la conexión")

                print(f"✓ Conectado a {TARGET_NAME} @ {client.address}")

                # Suscribirse a notificaciones del buffer
                await client.start_notify(BUFFER_CHAR_UUID, notification_handler)
                print("✓ Suscrito a notificaciones del buffer. Esperando datos...\n")

                # Resetear backoff tras conexión exitosa
                backoff = 2

                # Esperar hasta que se dispare el evento de desconexión
                await disconnected_event.wait()

            # Al salir del contexto, el cliente ya está cerrado. Volver a intentar.
            print("↻ Intentando reconectar...")
            await asyncio.sleep(1)

        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:
            print("\n✓ Programa terminado por el usuario")
            return
        except Exception as e:
            print(f"✗ Error de conexión/recepción: {e}")
            print(f"⏳ Reintentando en {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(max_backoff, max(2, backoff * 2))

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
