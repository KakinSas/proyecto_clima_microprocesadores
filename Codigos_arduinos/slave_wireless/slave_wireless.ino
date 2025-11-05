#include <Arduino.h>
#include <ArduinoBLE.h>
#include <Arduino_HTS221.h>
#include <Arduino_LPS22HB.h>

// Configuración de tiempo - 1 minuto (para sincronización)
const unsigned long INTERVALO_LECTURA = 60000; // 1 minuto en milisegundos (60,000 ms)
unsigned long ultimaLectura = 0;

// LED de identificación - Parpadeo lento (2 segundos)
const unsigned long INTERVALO_LED = 2000; // 2 segundos
unsigned long ultimoParpadeoLED = 0;
bool estadoLED = false;

// Control de parpadeo de envío de datos (sin usar delay)
unsigned long inicioParpadeoEnvio = 0;
int contadorParpadeosEnvio = 0;
bool modoParpadeoEnvio = false;
bool estadoLEDEnvio = false;

// Control de advertising
bool advertisingActivo = false;


// Servicio BLE personalizado
BLEService sensorService("19B10000-E8F2-537E-4F6C-D104768A1214");

// Característica para enviar datos (UUID personalizado)
BLECharacteristic dataChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 100);

void setup() {
  Serial.begin(9600);

  pinMode(LED_BUILTIN, OUTPUT);

  // Inicialización de sensores
  if (!HTS.begin()) {
    Serial.println("Fallo HTS221");
    while (1);
  }
  if (!BARO.begin()) {
    Serial.println("Fallo LPS22HB");
    while (1);
  }

  // Inicialización BLE
  if (!BLE.begin()) {
    Serial.println("Fallo BLE init");
    while (1);
  }

  BLE.setLocalName("ArduinoEsclavo");
  BLE.setAdvertisedService(sensorService);

  // Agregar característica al servicio
  sensorService.addCharacteristic(dataChar);

  BLE.addService(sensorService);

  BLE.advertise();
  Serial.println("Arduino Wireless - Iniciado");
  Serial.println("Intervalo de lectura: 1 minuto (sincronizado cada 10 min)");
  Serial.println("Esperando conexion BLE para enviar datos...");
  
  ultimaLectura = millis();
}

void loop() {
  BLE.poll();
  unsigned long tiempoActual = millis();
  
  // Manejo de parpadeo de envío (sin bloquear con delay)
  if (modoParpadeoEnvio) {
    if (tiempoActual - inicioParpadeoEnvio >= 100) {
      inicioParpadeoEnvio = tiempoActual;
      estadoLEDEnvio = !estadoLEDEnvio;
      digitalWrite(LED_BUILTIN, estadoLEDEnvio);
      
      if (!estadoLEDEnvio) {
        contadorParpadeosEnvio++;
        if (contadorParpadeosEnvio >= 2) {
          modoParpadeoEnvio = false;
          contadorParpadeosEnvio = 0;
        }
      }
    }
  } else {
    // LED de identificación - Parpadeo cada 2 segundos
    if (tiempoActual - ultimoParpadeoLED >= INTERVALO_LED) {
      estadoLED = !estadoLED;
      digitalWrite(LED_BUILTIN, estadoLED);
      ultimoParpadeoLED = tiempoActual;
    }
  }

  if (BLE.connected()) {
    // Resetear flag de advertising al conectar
    advertisingActivo = false;
    
    // Verificar si ha pasado 1 minuto
    if (tiempoActual - ultimaLectura >= INTERVALO_LECTURA) {
      // Leer sensores
      float temperatura = HTS.readTemperature();
      float humedad = HTS.readHumidity();
      float presion = BARO.readPressure();
      
      // Crear string con los datos en formato CSV
      String datos = "T:" + String(temperatura, 2) + 
                     ",H:" + String(humedad, 2) + 
                     ",P:" + String(presion, 2);
      
      // Enviar por BLE (convertir a bytes)
      bool envioExitoso = dataChar.writeValue(datos.c_str());
      
      if (envioExitoso) {
        // También por Serial para debug
        Serial.println(datos);
        
        // Actualizar el tiempo de la última lectura solo si envío exitoso
        ultimaLectura = tiempoActual;
        
        // Iniciar parpadeo sin bloquear
        modoParpadeoEnvio = true;
        inicioParpadeoEnvio = tiempoActual;
        contadorParpadeosEnvio = 0;
        digitalWrite(LED_BUILTIN, HIGH);
      } else {
        Serial.println("✗ Error enviando datos BLE");
      }
    }
  } else {
    // Si no hay conexión, reanudar advertising solo una vez
    if (!advertisingActivo) {
      BLE.advertise();
      advertisingActivo = true;
    }
  }
  
  // Pequeño delay para no saturar el loop
  delay(10); // Reducido de 50ms a 10ms para mejor respuesta
}