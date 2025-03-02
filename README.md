# floratech_hub

floratech_hub/
│── floratech_hub/              Directory principale del pacchetto
│   │── __init__.py             Rende floratech_hub un pacchetto Python
│   │── lora/                   Modulo per la gestione LoRa
│   │   │── __init__.py         Rende lora un sotto-pacchetto
│   │   │── lora.py             Classe per la gestione della comunicazione LoRa
│   │   │── constants.py        Costanti di configurazione per LoRa
│   │── database/               Modulo per la gestione del database TinyDB
│   │   │── __init__.py         Rende database un sotto-pacchetto
│   │   │── tinydb_manager.py   Gestione del database TinyDB
│   │── server/                 Modulo per la comunicazione con il server
│   │   │── __init__.py         Rende server un sotto-pacchetto
│   │   │── server_api.py       Comunicazione con server esterno
│   │── config.py               Configurazioni globali
│   │── main.py                 Punto di ingresso del programma
│── tests/                      Test per il codice
│── setup.py                    Script di installazione del pacchetto
│── requirements.txt            Dipendenze del progetto
│── README.md                   Descrizione del progetto
