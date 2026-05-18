# Mini Docker Manager

Mini Docker Manager este o aplicatie desktop Python cu Tkinter pentru administrarea containerelor Docker din Linux/WSL. Proiectul foloseste direct Docker CLI prin `subprocess`, fara Docker SDK, si ofera o interfata simpla pentru listare, control si monitorizare de containere si imagini.

## Ce face

- listeaza toate containerele Docker, inclusiv cele oprite
- afiseaza `ID`, `IMAGE`, `COMMAND`, `PORTS`, `STATUS` si `STATE`
- porneste, opreste, restarteaza si sterge containere cu confirmare unde este cazul
- afiseaza loguri si `docker inspect` pentru containerul selectat
- afiseaza statistici de resurse cu `docker stats --no-stream`
- listeaza imaginile locale Docker intr-o fereastra separata
- permite `pull`, `run` si `remove` pentru imagini
- permite configurarea intervalului de auto-refresh din interfata

## Tehnologii

- Python 3
- Tkinter / ttk
- Docker CLI
- Linux shell commands prin `subprocess.run`
- WSL 2

## Cerinte

Ai nevoie de:

1. Windows 10/11 cu WSL 2 activat
2. O distributie Linux in WSL, de exemplu Ubuntu
3. Docker Desktop cu integrare WSL sau Docker Engine instalat direct in Linux
4. Python 3 si `tkinter`

Exemplu de instalare in Ubuntu WSL:

```bash
sudo apt update
sudo apt install python3 python3-tk
docker --version
python3 --version
```

Daca utilizatorul curent nu are permisiuni pentru Docker:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## Rulare

Din folderul proiectului:

```bash
python3 main.py
```

Sau prin scriptul inclus:

```bash
chmod +x run.sh
./run.sh
```

## Structura

- [main.py](main.py): interfata Tkinter si logica de UI
- [docker_cli.py](docker_cli.py): apelurile catre Docker CLI
- [parsers.py](parsers.py): parsare si conversie pentru output-ul Docker
- [run.sh](run.sh): rulare rapida din Linux/WSL
- [DOCUMENTATIE.md](DOCUMENTATIE.md): documentatie tehnica extinsa

## Comenzi Docker folosite

```bash
docker ps -a --format '{{json .}}'
docker stats --no-stream --format '{{json .}}'
docker images --format '{{json .}}'
docker start <container_id>
docker stop <container_id>
docker restart <container_id>
docker rm -f <container_id>
docker logs --tail 30 <container_id>
docker inspect <container_id>
docker pull <image>
docker run -d [--name name] [-p host:container] <image>
docker run -d [--name name] [-p host:container] <image> /bin/bash -c "command"
docker rmi <image_id>
```

## Note despre `docker run`

Din interfata poti seta optional:

- numele containerului
- maparea de porturi
- programul rulat in container, de exemplu `/bin/bash`
- comanda trimisa cu `-c`

Daca introduci o comanda pentru `-c` si lasi programul gol, aplicatia foloseste implicit `/bin/bash`.

## Limitari

- monitorizarea resurselor este pe baza de refresh, nu streaming continuu
- `docker run` foloseste un formular simplu, fara validare avansata pentru toate optiunile Docker
- proiectul este gandit pentru Linux/WSL, nu pentru executie directa din PowerShell
