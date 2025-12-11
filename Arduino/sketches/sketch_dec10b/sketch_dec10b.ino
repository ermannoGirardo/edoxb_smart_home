#include <WiFiS3.h>

// WiFi
char ssid[] = "CasaLavagnola1";
char pass[] = "Marcello1963*";

// SERVER LOCALE (Arduino)
WiFiServer server(80);

// CLIENT (verso tuo backend)
const char* backendHost = "192.168.178.81";
const int backendPort = 8000;

// Sensori
const int sensorPin = 7;

// Attuatore (LUCE)
const int lucePin = 6;

// Timer invio periodico
unsigned long lastSend = 0;
unsigned long sendInterval = 5000;

// WiFi status
int status = WL_IDLE_STATUS;

void setup() {
  Serial.begin(115200);
  delay(1500);

  pinMode(sensorPin, INPUT_PULLUP);

  pinMode(lucePin, OUTPUT);     // <<< AGGIUNTO
  digitalWrite(lucePin, LOW);   // luce inizialmente spenta

  // Connessione WiFi
  Serial.println("Connessione alla rete...");
  while (status != WL_CONNECTED) {
    status = WiFi.begin(ssid, pass);
    delay(2000);
  }

  Serial.println("WiFi connesso!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  server.begin();
  Serial.println("Server HTTP avviato sulla porta 80");
}

void server_handleRequests() {
  WiFiClient client = server.available();
  if (!client) return;

  Serial.println("Cliente connesso al server locale");

  String req = "";
  while (client.connected() && client.available()) {
    char c = client.read();
    req += c;
    if (c == '\n') break;
  }

  Serial.println("Richiesta ricevuta:");
  Serial.println(req);

  // Estrazione endpoint
  String path = "";
  int start = req.indexOf(' ') + 1;
  int end   = req.indexOf(' ', start);
  if (start > 0 && end > 0) {
    path = req.substring(start, end);
  }

  Serial.print("Endpoint richiesto: ");
  Serial.println(path);

  // SWITCH su endpoint
  String response;

  if (path == "/accendi") {
    digitalWrite(lucePin, HIGH);   // <<< ACCENDE LUCE su PIN 6
    response = "{\"stato\": \"luce accesa\"}";
  }
  else if (path == "/spegni") {
    digitalWrite(lucePin, LOW);    // <<< SPEGNE LUCE su PIN 6
    response = "{\"stato\": \"luce spenta\"}";
  }
  else if (path == "/stato") {
    int s = digitalRead(sensorPin);
    response = "{\"sensore\": " + String(s) + "}";
  }
  else {
    response = "{\"errore\": \"endpoint sconosciuto\"}";
  }

  // Risposta
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: application/json");
  client.println("Connection: close");
  client.println();
  client.print(response);

  client.stop();
  Serial.println("Cliente disconnesso\n");
}

void client_sendSensorStatus() {
  if (millis() - lastSend < sendInterval) return;
  lastSend = millis();

  int valore = digitalRead(sensorPin);

  WiFiClient cli;

  if (!cli.connect(backendHost, backendPort)) {
    Serial.println("Errore di connessione al backend");
    return;
  }

  String url = "/sensori/update";
  String json = "{\"pin7\": " + String(valore) + "}";

  cli.print("POST " + url + " HTTP/1.1\r\n");
  cli.print("Host: " + String(backendHost) + "\r\n");
  cli.print("Content-Type: application/json\r\n");
  cli.print("Content-Length: " + String(json.length()) + "\r\n");
  cli.print("Connection: close\r\n\r\n");
  cli.print(json);

  Serial.println("Dati inviati al backend:");
  Serial.println(json);

  while (cli.connected() || cli.available()) {
    if (cli.available()) {
      Serial.print((char)cli.read());
    }
  }

  cli.stop();
  Serial.println("\nInvio completato.\n");
}

void loop() {
  server_handleRequests();
  client_sendSensorStatus();
}
