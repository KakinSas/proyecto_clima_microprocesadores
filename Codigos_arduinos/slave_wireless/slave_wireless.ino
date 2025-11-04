#include <Arduino.h>
#include <ArduinoBLE.h>
#include <Arduino_HTS221.h>
#include <Arduino_LPS22HB.h>

// Configuración de tiempo - 10 minutos
const unsigned long INTERVALO_LECTURA = 600000; // 10 minutos en milisegundos (600,000 ms)
unsigned long ultimaLectura = 0;

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
  Serial.println("Intervalo de lectura: 10 minutos");
  
  ultimaLectura = millis(); // Inicializar el tiempo
}

void loop() {
  BLE.poll();

  if (BLE.connected()) {
    unsigned long tiempoActual = millis();
    
    // Verificar si han pasado 10 minutos
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
      dataChar.writeValue(datos.c_str());
      
      // También por Serial para debug
      Serial.println(datos);
      
      // Actualizar el tiempo de la última lectura
      ultimaLectura = tiempoActual;
      
      // Parpadear LED para indicar lectura
      digitalWrite(LED_BUILTIN, HIGH);
      delay(100);
      digitalWrite(LED_BUILTIN, LOW);
    }
  } else {
    // Si no hay conexión, reanudar advertising
    BLE.advertise();
  }
  
  // Pequeño delay para no saturar el loop
  delay(100);
}