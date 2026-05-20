#include <esp_now.h>
#include <WiFi.h>
#include "ConexaoBLE.h"

ThunkableBLE conexao;
int pin = 2; 

int contPisque = 0;
int quantInfoPisque = 3;

unsigned long ultimoTempoRecebido = 0; 
const unsigned long TIMEOUT_ESP_NOW = 2000;
bool conexaoPerdida = false;

typedef struct struct_mensagem {
    int valores[5];
} struct_mensagem;

struct_mensagem dadosRecebidos;

// Função executada automaticamente quando o ESP-NOW recebe dados
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {

  if(contPisque >= quantInfoPisque){
    digitalWrite(pin,1);
    contPisque = 0;
  }else if(contPisque == 1){
    digitalWrite(pin,0);
  }
  contPisque++;

  ultimoTempoRecebido = millis(); 
  conexaoPerdida = false;

  // Copia os bytes brutos para a estrutura de dados
  memcpy(&dadosRecebidos, incomingData, sizeof(dadosRecebidos));
  
  // Monta a String separada por vírgulas
  String payload = String(dadosRecebidos.valores[0]) + "," +
                   String(dadosRecebidos.valores[1]) + "," +
                   String(dadosRecebidos.valores[2]) + "," +
                   String(dadosRecebidos.valores[3]) + "," +
                   String(dadosRecebidos.valores[4]);
                   
  // >>> FORMATAÇÃO DO SENSOR: Envia para o terminal Python ler <<<
  Serial.print("Recebido via ESP-NOW: ");
  Serial.println(payload);

  // Se o Thunkable estiver conectado, envia para o celular também
  if (deviceConnected) {
     conexao.enviarMss(payload);
  }
}

void setup() {
    Serial.begin(115200);
    pinMode(pin, OUTPUT);
    
    esp_wifi_set_max_tx_power(75);

    // Inicializa o Wi-Fi em modo Station para o ESP-NOW
    WiFi.mode(WIFI_STA);

    // Inicializa o ESP-NOW para alimentar o Python na hora
    if (esp_now_init() != ESP_OK) {
      Serial.println("Erro ao inicializar ESP-NOW");
      return;
    }
    esp_now_register_recv_cb(esp_now_recv_cb_t(OnDataRecv));
    Serial.println("-> ESP-NOW ativo e transmitindo para o Python...");

    // Inicializa o BLE para o Thunkable
    conexao.iniciarBLE("Receptor");
    
    ultimoTempoRecebido = millis(); 
}

void loop() {
    // Alerta de perda de sinal com os sensores
    if (millis() - ultimoTempoRecebido > TIMEOUT_ESP_NOW && !conexaoPerdida) {
        Serial.println("\n[ALERTA] Conexao perdida com o ESP dos Sensores!");
        conexaoPerdida = true;
    }

    // Processa comandos enviados do celular (ex: Ligar/Desligar LED)
    String mss = conexao.getMssRecebida();
    if (deviceConnected && mss.length() > 0) {
        if (mss.equals("L") || mss.equals("l")) digitalWrite(pin, HIGH);
        else if (mss.equals("D") || mss.equals("d")) digitalWrite(pin, LOW);
        conexao.limparMss(); 
    }
    
    delay(20); 
}