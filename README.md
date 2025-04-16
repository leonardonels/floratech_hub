<div align="center">
    <h1>Floratech HUB</h1>
</div>

## :open_file_folder: What's in this repo
```commandline
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
```

## :gear: How to ssh
> In order to access the server from your local machine, you need to install Cloudflared on your local machine.
> You can follow the installation by running the following command:
```commandline
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb &&
sudo dpkg -i cloudflared.deb &&
rm cloudflared.deb
```
> Next, you need to add remote server to your SSH config. You can do this by adding the following configuration to your ~/.ssh/config:
```commandline
Host django
  Hostname ssh-django.leonardonels.com
  User django
  ProxyCommand /usr/local/bin/cloudflared access ssh --hostname %h
```
> Now you can access the server by running the following command:
```commandline
ssh django
```
