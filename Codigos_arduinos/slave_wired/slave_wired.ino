#include <Arduino.h>
#include <Arduino_HTS221.h>
#include <Arduino_LPS22HB.h>

unsigned long lastUpdate = 0;
const int interval = 1000; // 1 segundo por lectura
int cycle = 0;

// Buffer de datos
const int BUFFER_SIZE = 244; // Para ser lo mismo que el wireless
byte dataBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// Estructura para cada registro de sensor (12 bytes: 3 floats)
struct SensorData {
  float temperature;
  float humidity;
  float pressure;
};

void setup() {
  Serial.begin(9600);
  while (!Serial);

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

  Serial.println("Esclavo cableado listo...");
}

void loop() {
  unsigned long now = millis();
  if (now - lastUpdate >= interval) {
    lastUpdate = now;

    // Leer sensores y agregar al buffer
    addSensorDataToBuffer();

    cycle++;
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }
}

void addSensorDataToBuffer() {
  // Leer sensores
  SensorData data;
  data.temperature = HTS.readTemperature();
  data.humidity = HTS.readHumidity();
  data.pressure = BARO.readPressure();

  // Calcular espacio necesario
  int dataSize = sizeof(SensorData); // 12 bytes

  // Verificar si hay espacio en el buffer
  if (bufferIndex + dataSize <= BUFFER_SIZE) {
    // Copiar datos al buffer
    memcpy(&dataBuffer[bufferIndex], &data, dataSize);
    bufferIndex += dataSize;
  } else {
    // Buffer lleno o a punto de llenarse, enviar
    sendBuffer();
    
    // Reiniciar buffer - NO agregar el dato actual
    bufferIndex = 0;
    memset(dataBuffer, 0, BUFFER_SIZE);
  }
}

void sendBuffer() {
  Serial.println("Buffer lleno, enviando informacion por serial");
  
  // Calcular número de registros
  int recordSize = sizeof(SensorData); // 12 bytes
  int numRecords = bufferIndex / recordSize;
  
  // Enviar cada registro por serial
  for (int i = 0; i < numRecords; i++) {
    int offset = i * recordSize;
    
    SensorData data;
    memcpy(&data, &dataBuffer[offset], recordSize);
    
    // Formato: Registro N - Temp: X.XX °C, Hum: X.XX %, Pres: X.XX kPa
    Serial.print("Registro ");
    Serial.print(i + 1);
    Serial.print(" - Temp: ");
    Serial.print(data.temperature, 2);
    Serial.print(" °C, Hum: ");
    Serial.print(data.humidity, 2);
    Serial.print(" %, Pres: ");
    Serial.print(data.pressure, 2);
    Serial.println(" kPa");
  }
  
  Serial.println("---FIN_BUFFER---");
}
