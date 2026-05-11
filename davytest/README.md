# Network as Code – LAB 8.2

## Overzicht

| Bestand | Task | Protocol |
|---|---|---|
| `task36_netconf.py` | Task 36 | NETCONF + Python |
| `task38_restconf.py` | Task 38 | RESTCONF + Python |
| `router-config.xml` | Config bron Task 36 | YANG-XML |
| `router-config.json` | Config bron Task 38 | YANG-JSON |

GitHub fungeert als **single source of truth**.  
De scripts halen de configuratie automatisch op via de raw GitHub URL.

---

## Vereisten

```bash
pip install ncclient requests
```

Router vereisten (reeds geconfigureerd via CLI):
```
netconf-yang
restconf
ip http secure-server
```

---

## Task 36 – NETCONF

### Wat het script doet
1. Config ophalen van GitHub (`router-config.xml`)
2. Verbinding maken via NETCONF (poort 830)
3. Candidate datastore **locken**
4. `edit-config` uitvoeren naar candidate
5. **Commit** naar running — of **discard-changes** bij fout
6. Candidate datastore **unlocken**
7. Verificatie via `get-config` op running

### Uitvoeren
```bash
python task36_netconf.py
```

### Verwachte output
```
[*] Config ophalen van GitHub...
[+] Config succesvol opgehaald (2048 bytes, HTTP 200)
[*] Verbinding maken met router 172.17.1.2:830 via NETCONF...
[+] Verbonden. Session-ID: 12345
[*] Candidate datastore locken...
[+] Statusfeedback: <ok/> — operatie geslaagd.
[*] edit-config uitvoeren naar candidate datastore...
[+] Statusfeedback: <ok/> — operatie geslaagd.
[*] Commit uitvoeren naar running datastore...
[+] Statusfeedback: <ok/> — operatie geslaagd.
[+] Configuratie succesvol gecommit naar running.
```

---

## Task 38 – RESTCONF

### Wat het script doet
1. Config ophalen van GitHub (`router-config.json`)
2. Per configuratieblok een **RESTCONF PUT** uitvoeren
3. HTTP statuscode controleren en loggen (200/201/204 = OK)
4. Response body parsen en pretty-printen
5. Verificatie via RESTCONF GET

### Uitvoeren
```bash
python task38_restconf.py
```

### Verwachte output
```
[*] Hostname configureren
[*] PUT → https://172.17.1.2:443/restconf/data/Cisco-IOS-XE-native:native/hostname
[+] HTTP 204 — Hostname configureren geslaagd.
[*] GigabitEthernet interfaces configureren
[*] PUT → https://172.17.1.2:443/restconf/data/...
[+] HTTP 204 — GigabitEthernet interfaces configureren geslaagd.
...
[+] Deployment volledig geslaagd — alle onderdelen geconfigureerd.
```

---

## GitHub repository structuur

```
yangtaken/
├── router-config.xml      ← NETCONF config (Task 36)
├── router-config.json     ← RESTCONF config (Task 38)
├── task36_netconf.py      ← NETCONF deployment script
├── task38_restconf.py     ← RESTCONF deployment script
└── README.md
```

---

## Troubleshooting

| Probleem | Oorzaak | Oplossing |
|---|---|---|
| `Connection refused` op poort 830 | NETCONF niet actief | `netconf-yang` op router uitvoeren |
| `HTTP 401` | Verkeerde credentials | Username/password controleren |
| `HTTP 400` | Ongeldige JSON/XML payload | Config bestand valideren |
| `HTTP 404` | RESTCONF pad bestaat niet | YANG Suite gebruiken om pad te verifiëren |
| Candidate lock mislukt | Andere sessie heeft lock | Wachten of router herstarten |
| SSH tunnel nodig | Geen direct netwerk | `ssh -L 8444:172.17.7.86:8443 yanguser@172.17.1.1` |
