#include <ArduinoBLE.h>

BLEDevice peripheral;

// Buffer para recibir datos
const int BUFFER_SIZE = 1024;
byte dataBuffer[BUFFER_SIZE];

bool dataReceived = false;

void setup() {
  Serial.begin(9600);
  while (!Serial); // Espera monitor serie

  if (!BLE.begin()){
    // error al iniciar BLE
    while (1);
  }

  BLE.scanForName("ArduinoEsclavo");
}

void loop() {
  BLE.poll(); // gestiona eventos BLE

  // si se cierra el monitor serie, desconectar esclavo
  if (!Serial && BLE.connected()) {
    peripheral.disconnect(); // forzar desconexión
    return;                  // saltar el resto del loop
  }

  if (!BLE.connected()) {
    if (Serial) BLE.scanForName("ArduinoEsclavo");
    peripheral = BLE.available();

    if (peripheral) {
      BLE.stopScan();
      if (peripheral.connect()) {  
        Serial.println("Conectando al esclavo...");
        peripheral.discoverAttributes();
        
        // Suscribirse a notificaciones del buffer
        BLECharacteristic bufferChar = peripheral.characteristic("19B10001-E8F2-537E-4F6C-D104768A1214");
        if (bufferChar && bufferChar.canSubscribe()) {
          bufferChar.subscribe();
          Serial.println("Suscrito a notificaciones del buffer");
        }
      }
    }
  } else {
    // Verificar si hay nuevos datos disponibles
    BLECharacteristic bufferChar = peripheral.characteristic("19B10001-E8F2-537E-4F6C-D104768A1214");
    if (bufferChar && bufferChar.valueUpdated()) {
      Serial.println("====================================");
      readBuffer();
    }
  }
}

void readBuffer(){
  // UUID personalizado para el buffer de datos
  BLECharacteristic bufferChar = peripheral.characteristic("19B10001-E8F2-537E-4F6C-D104768A1214");
  
  if (bufferChar && bufferChar.canRead()) {
    int bytesRead = bufferChar.readValue(dataBuffer, BUFFER_SIZE);
    
    if (bytesRead > 0) {
      Serial.print("Buffer recibido: ");
      Serial.print(bytesRead);
      Serial.println(" bytes");
      
      // Mostrar el contenido del buffer en hexadecimal
      Serial.print("Datos (HEX): ");
      for (int i = 0; i < bytesRead; i++) {
        if (dataBuffer[i] < 0x10) Serial.print("0");
        Serial.print(dataBuffer[i], HEX);
        Serial.print(" ");
        if ((i + 1) % 16 == 0) {
          Serial.println();
          Serial.print("             ");
        }
      }
      Serial.println();
      
      processBufferData(dataBuffer, bytesRead);
    } else {
      Serial.println("No se pudieron leer datos del buffer");
    }
  } else {
    Serial.println("Característica de buffer no disponible o no se puede leer");
  }
}

void processBufferData(byte* buffer, int size) {
  // Esta función procesa los datos del buffer
  
  Serial.println("Procesando datos del buffer...");
  
  // Ejemplo de procesamiento 
  // Si cada registro tiene: 4 bytes temp + 4 bytes hum + 4 bytes pres = 12 bytes por registro
  int recordSize = 12; // float temp + float hum + float pres
  int numRecords = size / recordSize;
  
  for (int i = 0; i < numRecords; i++) {
    int offset = i * recordSize;
    
    float temp, hum, pres;
    memcpy(&temp, &buffer[offset], sizeof(float));
    memcpy(&hum, &buffer[offset + 4], sizeof(float));
    memcpy(&pres, &buffer[offset + 8], sizeof(float));
    
    Serial.print("Registro ");
    Serial.print(i + 1);
    Serial.print(" - Temp: ");
    Serial.print(temp);
    Serial.print(" °C, Hum: ");
    Serial.print(hum);
    Serial.print(" %, Pres: ");
    Serial.print(pres);
    Serial.println(" kPa");
  }
}