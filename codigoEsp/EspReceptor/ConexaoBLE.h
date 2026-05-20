#ifndef CONEXAOBLE_H
#define CONEXAOBLE_H

#include <Arduino.h>
#include <NimBLEDevice.h> 

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "10000000-0000-0000-0000-000000000000"

NimBLECharacteristic *pCharacteristic;
NimBLEServer *pServer = NULL;
bool deviceConnected = false;
static String mssRecebida = "";

// Gerenciador de conexão do celular
class MyServerCallbacks: public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer, ble_gap_conn_desc* desc) {
      deviceConnected = true;
      Serial.println("\n[BLE] Celular Conectado!");
    }
    void onDisconnect(NimBLEServer* pServer, ble_gap_conn_desc* desc) {
      deviceConnected = false;
      Serial.println("\n[BLE] Celular Desconectado. Reiniciando anúncios...");
      NimBLEDevice::startAdvertising();
    }
};

// Gerenciador de comandos vindos do Thunkable para o ESP32
class BLE_Adapter_Callback : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic *pChar, ble_gap_conn_desc* desc) {
        String dadoRecebido = pChar->getValue().c_str(); 
        mssRecebida = dadoRecebido;
    }
};

class ThunkableBLE {
  public:
    void iniciarBLE(String nomeBT) {
      NimBLEDevice::init(nomeBT.c_str()); 
      NimBLEDevice::setSecurityAuth(false, false, false); // Modo "Just Works" (Sem PIN)

      pServer = NimBLEDevice::createServer();
      pServer->setCallbacks(new MyServerCallbacks());
      
      NimBLEService *pService = pServer->createService(SERVICE_UUID);
      
      pCharacteristic = pService->createCharacteristic(
          CHARACTERISTIC_UUID,
          NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::NOTIFY
      );
      
      pCharacteristic->setCallbacks(new BLE_Adapter_Callback());
      pService->start(); 

      // Configuração de anúncios visíveis para o Thunkable
      NimBLEAdvertising *pAdvertising = NimBLEDevice::getAdvertising();
      NimBLEAdvertisementData advData;
      NimBLEAdvertisementData scanData;
      
      advData.setName(nomeBT.c_str());
      advData.setFlags(BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP);
      scanData.addServiceUUID(SERVICE_UUID);
      
      pAdvertising->setAdvertisementData(advData);
      pAdvertising->setScanResponseData(scanData);
      
      // Intervalos espaçados para não sufocar o rádio do ESP-NOW
      pAdvertising->setMinInterval(0x80); // ~100ms
      pAdvertising->setMaxInterval(0x100); // ~200ms
      
      NimBLEDevice::startAdvertising(); 
      Serial.println("[BLE] Servidor Bluetooth Low Energy Ativo!");
    }

    void enviarMss(String mensagem) {
      pCharacteristic->setValue(mensagem.c_str()); 
      pCharacteristic->notify(); 
    }

    String getMssRecebida() { return mssRecebida; }
    void limparMss() { mssRecebida = ""; }
};

#endif