# Documentatie proiect

## 1. Ce face aplicatia

Aplicatia este un mini-manager grafic pentru containere Docker, inspirat de ideea de Docker Desktop, dar implementat intr-o forma simpla, pentru Linux in WSL. Interfata este facuta in Python cu Tkinter, iar partea de administrare Docker este facuta prin comenzi Linux executate cu `subprocess`.

## 2. Tehnologii folosite

- Python 3
- Tkinter si ttk pentru interfata grafica
- subprocess pentru apelarea comenzilor Linux
- Docker CLI pentru administrarea containerelor
- Bash prin fisierul `run.sh`

## 3. Arhitectura aplicatiei

Fluxul aplicatiei este urmatorul:

1. Utilizatorul apasa un buton in interfata.
2. `main.py` apeleaza o functie din `docker_cli.py`.
3. `docker_cli.py` executa o comanda Linux cu `subprocess.run(...)`.
4. Rezultatul din `stdout` este trimis in `parsers.py`.
5. Datele procesate sunt afisate in tabelele Tkinter.

Diagrama simpla:

```text
Tkinter GUI -> Python callbacks -> subprocess.run -> Docker CLI -> stdout/stderr -> parsare -> GUI
```

## 4. Explicatia fisierelor

### `main.py`

Acesta este fisierul principal. El:

- creeaza fereastra principala
- creeaza cele doua tabele cu `ttk.Treeview`
- defineste butoanele Refresh, Start, Stop, Restart, Remove, Logs, Inspect si Images
- gestioneaza selectia containerului doar in tabelul principal
- afiseaza un rezumat cu total/running/stopped
- porneste auto-refresh cu `root.after(...)`, folosind numarul de secunde ales in interfata
- deschide o fereastra separata pentru managementul imaginilor Docker
- foloseste un thread separat pentru refresh, ca interfata sa ramana fluida
- cere prin dialog si optiunile pentru `docker run`: nume, porturi, program si comanda de tip `-c`

### `docker_cli.py`

Acest fisier contine partea care interactioneaza direct cu Linux si Docker. Functia `_run_docker_command` este cea mai importanta deoarece:

- construieste comanda, de exemplu `docker ps -a --format {{json .}}`
- ruleaza comanda cu `subprocess.run`
- citeste `stdout` si `stderr`
- verifica `returncode`
- ridica exceptii clare daca apare eroare

Pentru a face fisierul mai usor de prezentat, datele pentru containere, stats si imagini sunt transformate in dictionare prin helper-e mici separate.

Acest fisier arata explicit componenta Linux a proiectului, fiindca foloseste comenzi reale din shell si interpreteaza rezultatul lor in Python.

### `parsers.py`

Acest fisier transforma output-ul text primit de la Docker in date usor de folosit in GUI.

- `parse_json_lines` citeste fiecare linie JSON intoarsa de Docker
- `parse_size_mb` converteste valori precum `824KiB`, `45.2MiB` sau `1.3GiB` in MB
- `_split_number_and_unit` separa explicit numarul de unitatea de masura
- `extract_memory_usage` extrage doar memoria folosita din formatul `used / limit`

## 5. Comenzi Linux folosite in proiect

Aplicatia foloseste direct urmatoarele comenzi:

```bash
docker ps -a --format '{{json .}}'
docker stats --no-stream --format '{{json .}}'
docker images --format '{{json .}}'
docker start <container_id>
docker stop <container_id>
docker restart <container_id>
docker rm -f <container_id>
docker pull <image>
docker run -d [--name nume] [-p host:container] <image>
docker run -d [--name nume] [-p host:container] <image> /bin/bash -c "comanda"
docker rmi <image_id>
docker logs --tail 30 <container_id>
docker inspect <container_id>
```

Aceste comenzi au fost alese pentru ca:

- sunt native Linux / Docker CLI
- pot fi apelate usor din Python
- permit parsare mai stabila decat output-ul tabelar clasic

## 6. De ce am ales aceasta solutie

In loc sa folosesc Docker SDK pentru Python, am preferat Docker CLI prin `subprocess`, deoarece cerinta cere explicit integrare cu Linux, shell sau scripturi bash.

Astfel, proiectul demonstreaza clar combinatia dintre:

- Python pentru logica si GUI
- Linux pentru comenzi si automatizare
- Docker pentru administrarea containerelor

## 7. FAQ

### De ce am folosit `ttk.Treeview`?

Pentru ca este cea mai simpla componenta standard Tkinter pentru a afisa date tabelare.

### De ce folosesc `subprocess.run` si nu `os.system`?

`subprocess.run` este mai sigur si mai flexibil. El permite capturarea output-ului, verificarea codului de iesire si setarea unui timeout.

### Ce face `root.after(5000, ...)`?

Planifica executia unei functii dupa 5000 ms, fara a bloca fereastra grafica.

### De ce refresh-ul ruleaza intr-un thread separat?

Pentru ca apelurile `docker ps`, `docker stats` si `docker images` pot dura, iar daca ar rula direct in thread-ul Tkinter, interfata ar avea lag.

### De ce parsez JSON pe linii?

Docker poate produce cate un obiect JSON pe fiecare linie, iar aceasta varianta este mai robusta decat taierea unui tabel text dupa spatii.

## 8. Prerequisites & run

Pasii minimi pentru rulare:

```bash
sudo apt update
sudo apt install python3 python3-tk
python3 --version
docker --version
python3 main.py
```

Alternativ:

```bash
chmod +x run.sh
./run.sh
```

## 9. Referinte bibliografice

- https://docs.docker.com/reference/cli/docker/ps/
- https://docs.docker.com/reference/cli/docker/images/
- https://docs.docker.com/reference/cli/docker/run/
- https://docs.docker.com/reference/cli/docker/pull/
- https://docs.docker.com/reference/cli/docker/stats/
- https://docs.python.org/3/library/subprocess.html
- https://docs.python.org/3/library/tkinter.ttk.html
- https://learn.microsoft.com/windows/wsl/
- https://www.geeksforgeeks.org/python/python-gui-tkinter/

## 10. Ce m-a ajutat in rezolvare

- documentatia oficiala Python pentru `subprocess` si Tkinter
- documentatia Docker CLI pentru format JSON si stats
- materialele de curs despre procese, apeluri de sistem si integrarea Python cu shell-ul Linux
- copilot VS Code (pentru actiunea de refresh care ruleaza acum in background si nu pe thread-ul UI, pentru a nu avea lag, si nu numai - nu am gasit link de partajare direct din aplicatie)

- url GitHub: https://github.com/lookasdev/mini-docker-manager