#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h> // Biblioteca necessária para desligar o rádio nativamente

#define led 2 
int sensores[5] = {13, 14, 26, 33, 35};
int bombas[2] = {15, 19};
int infoPorPisque = 5;
int enviados = 0;

uint8_t broadcastAddress[] = {0x84, 0x1F, 0xE8, 0x39, 0xDB, 0x40};

typedef struct struct_mensagem {
    int valores[5];
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
  for(int i = 0; i < 2; i++) pinMode(bombas[i], OUTPUT);
  for(int i = 0; i < 5; i++) pinMode(sensores[i], INPUT);

  esp_wifi_set_max_tx_power(78);

  iniciarEspNow();
}

void loop() {
  esp_wifi_stop();//desliga para usar os sensores
  delay(10); // Pequena pausa para o rádio desligar totalmente

  int valoresUmidade[5];

  // ---- 2. FAZ A LEITURA DOS SENSORES (Agora vai ler os valores reais) ----
  for(int i = 0; i < 5; i++){
    int valorAnalog = analogRead(sensores[i]);
    int umidade = map(valorAnalog, 0, 4095, 100, 0);
    if(umidade > 100) umidade = 100;
    if(umidade < 0)   umidade = 0; 

    valoresUmidade[i] = umidade;
    meusDados.valores[i] = umidade; 
  }  
  
  esp_wifi_start();//religa a transmissao espnow
  iniciarEspNow();
  delay(10);

  // Mantém o envio serial para o seu Python
  for(int i = 0; i < 5; i++){
    Serial.print("S_"+String(i+1)+" Umidade: ");
    Serial.print(valoresUmidade[i]);
    Serial.print("% | ");
  }
  Serial.println();

  // Envia via ESP-NOW
  esp_now_send(broadcastAddress, (uint8_t *) &meusDados, sizeof(meusDados));

  if(enviados > infoPorPisque){
    digitalWrite(led, HIGH);
    enviados = 0;
  } else if(enviados == 1){  
    digitalWrite(led, LOW);
  }
  
  delay(100);
  enviados++;
}