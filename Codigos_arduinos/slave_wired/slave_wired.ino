#include <Arduino.h>
#include <Arduino_HTS221.h>
#include <Arduino_LPS22HB.h>

// Configuración de tiempo - 10 minutos
const unsigned long INTERVALO_LECTURA = 600000; // 10 minutos en milisegundos (600,000 ms)
unsigned long ultimaLectura = 0;

// LED de identificación - Parpadeo rápido (1 segundo)
const unsigned long INTERVALO_LED = 1000; // 1 segundo
unsigned long ultimoParpadeoLED = 0;
bool estadoLED = false;

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

  Serial.println("Arduino Wired - Iniciado");
  Serial.println("Intervalo de lectura: 10 minutos");
  
  // Enviar primer dato inmediatamente
  delay(2000); // Esperar 2 segundos para que se estabilicen los sensores
  
  float temperatura = HTS.readTemperature();
  float humedad = HTS.readHumidity();
  float presion = BARO.readPressure();
  
  Serial.print("T:");
  Serial.print(temperatura, 2);
  Serial.print(",H:");
  Serial.print(humedad, 2);
  Serial.print(",P:");
  Serial.println(presion, 2);
  
  Serial.println("Primer dato enviado - Siguiente en 10 minutos");
  
  // Parpadear LED para indicar lectura
  digitalWrite(LED_BUILTIN, HIGH);
  delay(100);
  digitalWrite(LED_BUILTIN, LOW);
  
  ultimaLectura = millis(); // Inicializar el tiempo después del primer envío
}

void loop() {
  unsigned long tiempoActual = millis();
  
  // LED de identificación - Parpadeo cada 1 segundo
  if (tiempoActual - ultimoParpadeoLED >= INTERVALO_LED) {
    estadoLED = !estadoLED;
    digitalWrite(LED_BUILTIN, estadoLED);
    ultimoParpadeoLED = tiempoActual;
  }
  
  // Verificar si han pasado 10 minutos
  if (tiempoActual - ultimaLectura >= INTERVALO_LECTURA) {
    // Leer sensores
    float temperatura = HTS.readTemperature();
    float humedad = HTS.readHumidity();
    float presion = BARO.readPressure();
    
    // Enviar datos en formato CSV
    Serial.print("T:");
    Serial.print(temperatura, 2);
    Serial.print(",H:");
    Serial.print(humedad, 2);
    Serial.print(",P:");
    Serial.println(presion, 2);
    
    // Actualizar el tiempo de la última lectura
    ultimaLectura = tiempoActual;
    
    // Triple parpadeo rápido para indicar envío de datos
    for (int i = 0; i < 3; i++) {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(100);
      digitalWrite(LED_BUILTIN, LOW);
      delay(100);
    }
  }
  
  // Pequeño delay para no saturar el loop
  delay(50);
}
