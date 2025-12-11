#include <WiFiS3.h>
#include <WebSocketsClient.h>

WebSocketsClient ws;

// Credentials WiFi
const char ssid[] = "CasaLavagnola1";
const char pass[] = "Marcello1963*";

// Server WebSocket REMOTO
const char* ws_host = "192.168.178.97";   // <--- METTI QUI IP SERVER
const uint16_t ws_port = 8005;             // <--- METTI QUI PORTA SERVER
const char* ws_path = "/ws";               // <--- per la maggior parte dei server

unsigned long lastSend = 0;

void setup() {
  Serial.begin(9600);

  // Connect WiFi
  Serial.println("Connessione WiFi...");
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(2000);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connesso. IP Arduino: ");
  Serial.println(WiFi.localIP());

  // Setup WebSocket client
  ws.begin(ws_host, ws_port, ws_path);

  ws.onEvent(webSocketEvent);

  // Impostazioni raccomandate
  ws.setReconnectInterval(5000);   // tenta retry ogni 5s
  ws.enableHeartbeat(15000, 3000, 2);
}

void loop() {
  ws.loop();

  // invia "ciao" ogni 5 secondi
  if (millis() - lastSend > 5000) {
    lastSend = millis();

    Serial.println("Invio: ciao");
    ws.sendTXT("ciao");
  }
}

void webSocketEvent(WStype_t type, uint8_t *payload, size_t length) {

  switch (type) {

    case WStype_CONNECTED:
      Serial.println("WebSocket connesso al server");
      ws.sendTXT("ciao");   // primo messaggio
      break;

    case WStype_DISCONNECTED:
      Serial.println("WebSocket disconnesso");
      break;

    case WStype_TEXT:
      Serial.print("Ricevuto: ");
      Serial.println((char*)payload);
      break;

    default:
      break;
  }
}
