import sys
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Instellingen ─────────────────────────────────────────────────────────────
GITHUB_URL = "https://raw.githubusercontent.com/MichelMichauxPXL/EntNetDavyMichel_lab8.1/main/davytest/router-config.json"
ROUTER_IP  = "172.17.1.1"
USERNAME   = "admin"
PASSWORD   = "cisco123"

BASE_URL = f"https://{ROUTER_IP}/restconf/data"
HEADERS  = {
    "Content-Type": "application/yang-data+json",
    "Accept":       "application/yang-data+json",
}


def log(ok, tekst):
    print(f"{'[+]' if ok else '[-]'} {tekst}")


def restconf_request(methode, pad, payload, naam):
    """Voert een PATCH of PUT uit. Geeft True terug bij succes."""
    url  = f"{BASE_URL}/{pad}"
    print(f"\n[*] {methode} {naam}")
    print(f"    URL: {url}")
    print(f"    Payload:\n{json.dumps(payload, indent=2)}")

    try:
        resp = requests.request(
            methode, url,
            auth=(USERNAME, PASSWORD),
            headers=HEADERS,
            json=payload,
            verify=False,
            timeout=15,
        )
        print(f"    HTTP {resp.status_code}")
        if resp.status_code in (200, 201, 204):
            log(True, f"{naam} geslaagd (HTTP {resp.status_code})")
            return True
        else:
            log(False, f"{naam} mislukt (HTTP {resp.status_code})")
            try:
                print(f"    Foutdetail: {json.dumps(resp.json(), indent=2)}")
            except Exception:
                print(f"    Foutdetail: {resp.text[:300]}")
            return False
    except requests.exceptions.ConnectionError:
        log(False, f"Geen verbinding met {ROUTER_IP}")
        return False
    except Exception as e:
        log(False, f"Fout: {e}")
        return False


def patch(pad, payload, naam):
    return restconf_request("PATCH", pad, payload, naam)


def put(pad, payload, naam):
    return restconf_request("PUT", pad, payload, naam)


def get(pad, naam):
    url  = f"{BASE_URL}/{pad}"
    resp = requests.get(url, auth=(USERNAME, PASSWORD), headers=HEADERS,
                        verify=False, timeout=15)
    print(f"\n[*] GET {naam} — HTTP {resp.status_code}")
    if resp.status_code == 200:
        print(json.dumps(resp.json(), indent=2))
        return True
    log(False, f"GET {naam} mislukt (HTTP {resp.status_code})")
    return False


# ─── Stap 1: Config ophalen van GitHub ───────────────────────────────────────
print("=" * 55)
print("  Task 38 – RESTCONF deployment via GitHub")
print("=" * 55)

print(f"\n[*] Config ophalen van: {GITHUB_URL}")
resp = requests.get(GITHUB_URL, timeout=15)
if resp.status_code != 200:
    print(f"[-] GitHub ophalen mislukt (HTTP {resp.status_code})")
    sys.exit(1)

config = resp.json()
native = config["Cisco-IOS-XE-native:native"]
log(True, f"Config opgehaald (HTTP {resp.status_code})")

# ─── Stap 2: Deployment ───────────────────────────────────────────────────────
fouten = []

# 1. Hostname
if not patch("Cisco-IOS-XE-native:native/hostname",
             {"Cisco-IOS-XE-native:hostname": native["hostname"]},
             "Hostname"):
    fouten.append("hostname")

# 2. GigabitEthernet interfaces (bestaan al → PATCH)
for iface in native.get("interface", {}).get("GigabitEthernet", []):
    naam = iface["name"]
    pad  = f"Cisco-IOS-XE-native:native/interface/GigabitEthernet={naam.replace('/', '%2F')}"
    if not patch(pad, {"Cisco-IOS-XE-native:GigabitEthernet": iface}, f"Gi{naam}"):
        fouten.append(f"Gi{naam}")

# 3. Loopback interfaces (bestaan nog NIET → PUT om aan te maken)
for lb in native.get("interface", {}).get("Loopback", []):
    naam = lb["name"]
    pad  = f"Cisco-IOS-XE-native:native/interface/Loopback={naam}"
    if not put(pad, {"Cisco-IOS-XE-native:Loopback": lb}, f"Loopback{naam}"):
        fouten.append(f"Loopback{naam}")

# 4. Static route (bestaat al → PATCH)
if "ip" in native and "route" in native["ip"]:
    if not patch("Cisco-IOS-XE-native:native/ip/route",
                 {"Cisco-IOS-XE-native:route": native["ip"]["route"]},
                 "Static route"):
        fouten.append("static route")

# ─── Stap 3: Verificatie ──────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("  Verificatie via RESTCONF GET")
print("=" * 55)
get("Cisco-IOS-XE-native:native/hostname", "Hostname")
get("Cisco-IOS-XE-native:native/interface/GigabitEthernet=0%2F0%2F0.11", "Gi0/0/0.11")
get("Cisco-IOS-XE-native:native/interface/Loopback=0", "Loopback0")

# ─── Resultaat ────────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
if fouten:
    log(False, f"Fouten in: {', '.join(fouten)}")
else:
    log(True, "Alle onderdelen succesvol geconfigureerd!")
print("=" * 55)