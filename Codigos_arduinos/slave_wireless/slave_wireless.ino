#include <Arduino.h>
#include <ArduinoBLE.h>
#include <Arduino_HTS221.h>
#include <Arduino_LPS22HB.h>

unsigned long lastUpdate = 0;
const int interval = 1000; // Cambiar a 1 segundo
int cycle = 0;

// Tiempo máximo de inactividad (ms)
const unsigned long centralTimeout = 10000; // 10 segundos
unsigned long lastActivity = 0;

// Buffer de datos
const int BUFFER_SIZE = 244; // Limite BLE
byte dataBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// Estructura para cada registro de sensor (12 bytes: 3 floats)
struct SensorData {
  float temperature;
  float humidity;
  float pressure;
};

// Servicio BLE personalizado
BLEService bufferService("19B10000-E8F2-537E-4F6C-D104768A1214");

// Característica del buffer (UUID personalizado)
BLECharacteristic bufferChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, BUFFER_SIZE);

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

  // Inicialización BLE
  if (!BLE.begin()) {
    Serial.println("Fallo BLE init");
    while (1);
  }

  BLE.setLocalName("ArduinoEsclavo");
  BLE.setAdvertisedService(bufferService);

  // Agregar característica al servicio
  bufferService.addCharacteristic(bufferChar);

  BLE.addService(bufferService);

  // Inicializar buffer vacío
  memset(dataBuffer, 0, BUFFER_SIZE);
  bufferChar.writeValue(dataBuffer, BUFFER_SIZE);

  BLE.advertise();
  Serial.println("Esclavo listo y anunciando...");

  lastActivity = millis();
}

void loop() {
  BLE.poll();

  if (BLE.connected()) {
    unsigned long now = millis();
    if (now - lastUpdate >= interval) {
      lastUpdate = now;

      // Leer sensores y agregar al buffer
      addSensorDataToBuffer();

      cycle++;
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));

      lastActivity = millis(); // registrar actividad local (envío de datos)
    }

    // Verificar inactividad
    if (millis() - lastActivity > centralTimeout) {
      Serial.println("Central inactivo, reiniciando...");
      restartBLE();
    }

  } else {
    // Si no hay central, reanudar advertising
    BLE.advertise();
    // Reiniciar buffer si se desconecta
    bufferIndex = 0;
    memset(dataBuffer, 0, BUFFER_SIZE);
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
  // Enviar buffer completo
  Serial.println("Buffer lleno, subiendo informacion a BLE");
  bufferChar.writeValue(dataBuffer, bufferIndex);
}

// Reinicio controlado del stack BLE
void restartBLE() {
  Serial.println("Reiniciando Esclavo...");
  BLE.end();              // detener BLE
  delay(1000);
  McuArmTools_SoftwareReset();     // reinicio completo del microcontrolador (ARM Cortex-M)
}

void McuArmTools_SoftwareReset(void)
{
  /* Generic way to request a reset from software for ARM Cortex */
  /* See https://community.freescale.com/thread/99740
     To write to this register, you must write 0x5FA to the VECTKEY field, otherwise the processor ignores the write.
     SYSRESETREQ will cause a system reset asynchronously, so need to wait afterwards.
   */
#if McuLib_CONFIG_CPU_IS_ARM_CORTEX_M
#if McuLib_CONFIG_PEX_SDK_USED
  SCB_AIRCR = SCB_AIRCR_VECTKEY(0x5FA) | SCB_AIRCR_SYSRESETREQ_MASK;
#elif McuLib_CONFIG_SDK_VERSION_USED==McuLib_CONFIG_SDK_S32K
  S32_SCB->AIRCR = S32_SCB_AIRCR_VECTKEY(0x5FA) | S32_SCB_AIRCR_SYSRESETREQ_MASK;
#elif McuLib_CONFIG_SDK_VERSION_USED==McuLib_CONFIG_SDK_RPI_PICO
  #define SCB_AIRCR                          (*((uint32_t*)(0xe0000000+0xed0c)))
  #define SCB_AIRCR_VECTKEY_Pos              16U                                            /*!< SCB AIRCR: VECTKEY Position */
  #define SCB_AIRCR_SYSRESETREQ_Pos           2U                                            /*!< SCB AIRCR: SYSRESETREQ Position */
  #define SCB_AIRCR_SYSRESETREQ_Msk          (1UL << SCB_AIRCR_SYSRESETREQ_Pos)             /*!< SCB AIRCR: SYSRESETREQ Mask */
 
  SCB_AIRCR = (0x5FA<<SCB_AIRCR_VECTKEY_Pos)|SCB_AIRCR_SYSRESETREQ_Msk;
#else
  SCB->AIRCR = (0x5FA<<SCB_AIRCR_VECTKEY_Pos)|SCB_AIRCR_SYSRESETREQ_Msk;
#endif
#endif
  for(;;) {
    /* wait until reset */
  }
}