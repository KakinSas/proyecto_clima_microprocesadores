import asyncio
import threading
import sys
import os
import time
import importlib.util

def import_module_from_path(module_name, file_path):
    """
    Importa un módulo desde una ruta específica
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Rutas a los módulos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
wired_path = os.path.join(SCRIPT_DIR, 'wired', 'wired.py')
wireless_path = os.path.join(SCRIPT_DIR, 'wireless', 'wireless.py')

# Importar módulos
wired = import_module_from_path('wired', wired_path)
wireless = import_module_from_path('wireless', wireless_path)

# Variables de control
wired_running = True
wireless_running = True

def run_wired():
    """
    Ejecuta el lector serial en un thread separado con reintentos automáticos
    """
    retry_count = 0
    while wired_running:
        try:
            if retry_count > 0:
                print(f"🔄 WIRED: Reintentando conexión (intento #{retry_count})...")
            else:
                print("🔌 Iniciando módulo WIRED (Serial)...")
            
            wired.main()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            retry_count += 1
            print(f"✗ Error en módulo WIRED: {e}")
            print(f"⏳ WIRED: Esperando 5 segundos antes de reintentar...")
            time.sleep(5)

async def run_wireless():
    """
    Ejecuta el lector Bluetooth de forma asíncrona con reintentos automáticos
    """
    retry_count = 0
    while wireless_running:
        try:
            if retry_count > 0:
                print(f"🔄 WIRELESS: Reintentando conexión (intento #{retry_count})...")
            else:
                print("📡 Iniciando módulo WIRELESS (Bluetooth)...")
            
            await wireless.main()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            retry_count += 1
            print(f"✗ Error en módulo WIRELESS: {e}")
            print(f"⏳ WIRELESS: Esperando 5 segundos antes de reintentar...")
            await asyncio.sleep(5)

async def main():
    """
    Función principal que ejecuta ambos módulos en paralelo
    """
    print("="*70)
    print("    Sistema de Adquisición de Datos - Dual Mode")
    print("="*70)
    print("📊 Ejecutando lecturas simultáneas con auto-reconexión:")
    print("   🔌 WIRED: Puerto Serial COM5")
    print("   📡 WIRELESS: Bluetooth (ArduinoEsclavo)")
    print("   💾 Guardando en: data/sensor_data.csv")
    print("   🔄 Auto-reintento: Activado")
    print("="*70)
    print()
    
    # Crear thread para el módulo wired (serial)
    wired_thread = threading.Thread(target=run_wired, daemon=True)
    wired_thread.start()
    
    # Pequeña pausa para que wired inicie primero
    await asyncio.sleep(2)
    
    # Ejecutar el módulo wireless (bluetooth) en el loop asyncio principal
    try:
        await run_wireless()
    except KeyboardInterrupt:
        print("\n✓ Programa terminado por el usuario")
        global wired_running, wireless_running
        wired_running = False
        wireless_running = False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Programa terminado por el usuario")
        wired_running = False
        wireless_running = False

