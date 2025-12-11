#include <WiFiS3.h>

// Credenziali WiFi
char ssid[] = "";
char pass[] = "*";

// Parametri server
const char* host = "192.168.178.81";
const int port = 8000;

// Stato WiFi
int status = WL_IDLE_STATUS;

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("Inizializzazione WiFi...");

  // Connessione WiFi
  while (status != WL_CONNECTED) {
    Serial.print("Connessione a: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    delay(3000);
  }

  Serial.println("WiFi connesso!");
  Serial.print("IP assegnato: ");
  Serial.println(WiFi.localIP());
  Serial.println("Pronto. Scrivi 'accendi' o 'spegni' nel monitor seriale.");
}

void inviaPOST(String comando) {
  WiFiClient client;

  Serial.println("------------------------------");
  Serial.print("Connessione a ");
  Serial.print(host);
  Serial.print(":");
  Serial.println(port);

  if (!client.connect(host, port)) {
    Serial.println("ERRORE: impossibile connettersi al server");
    return;
  }

  String url = "/luce/" + comando;
  String body = "{}";  // Corpo JSON (vuoto se non richiesto)

  Serial.print("Invio POST a ");
  Serial.println(url);

  // Header HTTP
  client.print("POST " + url + " HTTP/1.1\r\n");
  client.print("Host: " + String(host) + "\r\n");
  client.print("Content-Type: application/json\r\n");
  client.print("Content-Length: " + String(body.length()) + "\r\n");
  client.print("Connection: close\r\n\r\n");

  // Corpo della richiesta
  client.print(body);

  Serial.println("Richiesta inviata. In attesa della risposta...\n");

  // Lettura risposta server
  while (client.connected() || client.available()) {
    if (client.available()) {
      String line = client.readStringUntil('\n');
      Serial.println(line);
    }
  }

  client.stop();
  Serial.println("Richiesta completata!");
  Serial.println("------------------------------\n");
}

void loop() {
  // Se arriva un comando dal monitor seriale...
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "accendi") {
      inviaPOST("accendi");
    } 
    else if (cmd == "spegni") {
      inviaPOST("spegni");
    } 
    else {
      Serial.println("Comando non valido. Usa: accendi | spegni");
    }
  }
}
