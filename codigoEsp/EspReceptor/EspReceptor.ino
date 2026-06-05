#include <esp_now.h>
#include <WiFi.h>
#include "ConexaoBLE.h"

ThunkableBLE conexao;
int pin = 2; 

unsigned long ultimoTempoRecebido = 0; 
const unsigned long TIMEOUT_ESP_NOW = 2000;
bool conexaoPerdida = false;

// Estrutura atualizada para receber 5 umidades + 4 estados de bombas
typedef struct struct_mensagem {
    int valores[9]; 
} struct_mensagem;

struct_mensagem dadosRecebidos;

void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  ultimoTempoRecebido = millis(); 
  conexaoPerdida = false;

  memcpy(&dadosRecebidos, incomingData, sizeof(dadosRecebidos));
  
  // Monta a String com todos os 9 valores separados por vírgula
  String payload = String(dadosRecebidos.valores[0]) + "," +
                   String(dadosRecebidos.valores[1]) + "," +
                   String(dadosRecebidos.valores[2]) + "," +
                   String(dadosRecebidos.valores[3]) + "," +
                   String(dadosRecebidos.valores[4]) + "," +
                   String(dadosRecebidos.valores[5]) + "," + // Estado Bomba 1 (0 ou 1)
                   String(dadosRecebidos.valores[6]) + "," + // Estado Bomba 2 (0 ou 1)
                   String(dadosRecebidos.valores[7]) + "," + // Estado Bomba 3 (0 ou 1)
                   String(dadosRecebidos.valores[8]);        // Estado Bomba 4 (0 ou 1)
                   
  Serial.print("Recebido via ESP-NOW -> ");
  Serial.println(payload);

  if (deviceConnected) {
     conexao.enviarMss(payload);
  }
}

void setup() {
    Serial.begin(115200);
    pinMode(pin, OUTPUT);
    
    WiFi.mode(WIFI_STA);

    if (esp_now_init() != ESP_OK) {
      Serial.println("Erro ao inicializar ESP-NOW");
      return;
    }
    esp_now_register_recv_cb(esp_now_recv_cb_t(OnDataRecv));
    Serial.println("-> ESP-NOW ativo e transmitindo para o Python...");

    conexao.iniciarBLE("Receptor");
    
    ultimoTempoRecebido = millis(); 
}

void loop() {
    // CORRIGIDO: Agora usa a variável correta 'ultimoTempoRecebido'
    if (millis() - ultimoTempoRecebido > TIMEOUT_ESP_NOW && !conexaoPerdida) {
        Serial.println("\n[ALERTA] Conexao perdida com o ESP dos Sensores!");
        conexaoPerdida = true;
    }

    String mss = conexao.getMssRecebida();
    if (deviceConnected && mss.length() > 0) {
        if (mss.equals("L") || mss.equals("l")) digitalWrite(pin, HIGH);
        else if (mss.equals("D") || mss.equals("d")) digitalWrite(pin, LOW);
        conexao.limparMss(); 
    }
    
    delay(20); 
}