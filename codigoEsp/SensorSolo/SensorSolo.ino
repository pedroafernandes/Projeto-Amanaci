#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h> // Biblioteca necessária para desligar o rádio nativamente

#define led 2 
int sensores[5] = {13, 14, 26, 33, 35};

// 4 pinos de bombas físicas (Bomba 1, 2, 3 e 4)
int pinosBombas[4] = {15, 19, 21, 22}; 

int infoPorPisque = 5;
int enviados = 0;

uint8_t broadcastAddress[] = {0x84, 0x1F, 0xE8, 0x39, 0xDB, 0x40};

// Estrutura para 9 posições (5 umidades + 4 estados de bombas)
typedef struct struct_mensagem {
    int valores[9];
} struct_mensagem;

struct_mensagem meusDados;
esp_now_peer_info_t peerInfo;

// Função isolada para ligar o Wi-Fi e configurar o ESP-NOW
void iniciarEspNow() {
  WiFi.mode(WIFI_STA);
  
  if (esp_now_init() != ESP_OK) {
    Serial.println("Erro ao inicializar ESP-NOW");
    return;
  }
  
  // Como o Wi-Fi reinicia, precisamos registrar o "peer" novamente
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0; 
  peerInfo.encrypt = false;
  
  esp_now_add_peer(&peerInfo);
}

void setup() {
  Serial.begin(115200);
  pinMode(led, OUTPUT);
  
  // Configura os 4 pinos das bombas como saídas
  for(int i = 0; i < 4; i++) pinMode(pinosBombas[i], OUTPUT);
  for(int i = 0; i < 5; i++) pinMode(sensores[i], INPUT);

  // Força a potência máxima de transmissão de hardware
  esp_wifi_set_max_tx_power(78);

  iniciarEspNow();
}

void loop() {
  
  if(enviados > infoPorPisque){
    digitalWrite(led, HIGH);
    enviados = 0;
  } else if(enviados == 1){  
    digitalWrite(led, LOW);
  }
  enviados++;

  esp_wifi_stop(); // Desliga o rádio para evitar ruídos nas leituras analógicas dos sensores
  delay(10);       // Pequena pausa para o rádio desligar totalmente

  int valoresUmidade[5];

  // ---- LEITURA DOS SENSORES ----
  for(int i = 0; i < 5; i++){
    int valorAnalog = analogRead(sensores[i]);
    int umidade = map(valorAnalog, 0, 4095, 100, 0);
    if(umidade > 100) umidade = 100;
    if(umidade < 0)   umidade = 0; 

    valoresUmidade[i] = umidade;
    meusDados.valores[i] = umidade; // Salva as umidades nos índices 0 a 4 da estrutura
  }  

  // ---- NOVA LÓGICA DE IRRIGAÇÃO AUTOMÁTICA COOPERATIVA ----
  // Agora calcula a média entre o Sensor da Ponta (i) e o Sensor Central (valoresUmidade[4])
  for(int i = 0; i < 4; i++) {
    int mediaSetor = (valoresUmidade[i] + valoresUmidade[4]) / 2;

    if(mediaSetor < 30) {
      digitalWrite(pinosBombas[i], HIGH); // Liga a bomba física se a média ponderada for < 30%
      meusDados.valores[5 + i] = 1;       // Sinaliza no array que a bomba está Ligada (1)
    } else {
      digitalWrite(pinosBombas[i], LOW);  // Desliga a bomba física se a média ponderada for >= 30%
      meusDados.valores[5 + i] = 0;       // Sinaliza no array que a bomba está Desligada (0)
    }
  }
  
  esp_wifi_start(); // Religa a transmissão ESP-NOW
  iniciarEspNow();
  delay(10);

  // Mantém o envio serial original para debug local
  for(int i = 0; i < 5; i++){
    Serial.print("S_"+String(i+1)+" Umidade: ");
    Serial.print(valoresUmidade[i]);
    Serial.print("% | ");
  }
  
  Serial.print("Bombas Ativas: ");
  for(int i = 0; i < 4; i++) {
    Serial.print("B" + String(i+1) + ":" + String(meusDados.valores[5+i]) + " ");
  }
  Serial.println();

  // Envia a estrutura completa (9 valores) via ESP-NOW para o receptor
  esp_now_send(broadcastAddress, (uint8_t *) &meusDados, sizeof(meusDados));

  delay(100);
}