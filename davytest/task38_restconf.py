"""
Task 38 – RESTCONF (Python)
============================
Haalt een YANG-compliant JSON configuratiebestand op uit GitHub en
deployt het via RESTCONF op een Cisco IOS-XE toestel.

Vereisten (uit projectopdracht):
  - RESTCONF (geen NETCONF, geen CLI)
  - JSON configuratie opgeslagen in GitHub (single source of truth)
  - PUT of PATCH met HTTP statuscode controle
  - Fout- en succeslogging
  - Idempotent en herhaalbaar
  - Responses parsen naar Python datastructuren
"""

import sys
import json
import requests
import urllib3

# Schakel SSL-waarschuwingen uit (self-signed cert op lab router)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Instellingen ────────────────────────────────────────────────────────────
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/MichelMichauxPXL/EntNetDavyMichel_lab8.1/main/davytest/router-config.json"
)

ROUTER_IP   = "172.17.1.1"    # Management IP (VLAN 11)
ROUTER_PORT = 443
USERNAME    = "admin"
PASSWORD    = "cisco123"

BASE_URL = f"https://{ROUTER_IP}:{ROUTER_PORT}/restconf/data"

HEADERS = {
    "Content-Type": "application/yang-data+json",
    "Accept":       "application/yang-data+json",
}

# HTTP statuscodes die als succes worden beschouwd
SUCCESS_CODES = {200, 201, 204}


# ─── Hulpfuncties ────────────────────────────────────────────────────────────
def log(level: str, bericht: str):
    prefix = {"INFO": "[*]", "OK": "[+]", "FOUT": "[-]", "WARN": "[!]"}.get(level, "[?]")
    print(f"{prefix} {bericht}")


def pretty_json(data) -> str:
    """Geeft JSON terug als leesbaar geïndenteerd formaat."""
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2, ensure_ascii=False)
    try:
        return json.dumps(json.loads(data), indent=2, ensure_ascii=False)
    except Exception:
        return str(data)


def restconf_put(pad: str, payload: dict, omschrijving: str) -> bool:
    """
    Voert een RESTCONF PUT uit op het opgegeven pad.
    Logt HTTP statuscode en response body.
    Retourneert True bij succes, False bij fout.
    """
    url = f"{BASE_URL}/{pad}"
    log("INFO", f"{omschrijving}")
    log("INFO", f"PUT → {url}")
    log("INFO", f"Payload:\n{pretty_json(payload)}")

    try:
        resp = requests.put(
            url,
            auth=(USERNAME, PASSWORD),
            headers=HEADERS,
            json=payload,
            verify=False,
            timeout=15,
        )

        # ── Statuscode controleren ────────────────────────────────────────
        if resp.status_code in SUCCESS_CODES:
            log("OK", f"HTTP {resp.status_code} — {omschrijving} geslaagd.")
        else:
            log("FOUT", f"HTTP {resp.status_code} — {omschrijving} mislukt.")
            # Response body parsen voor details
            try:
                fout_detail = resp.json()
                log("FOUT", f"Response body:\n{pretty_json(fout_detail)}")
            except Exception:
                log("FOUT", f"Response body (raw): {resp.text[:500]}")
            return False

        # ── Response body parsen als aanwezig ─────────────────────────────
        if resp.text:
            try:
                response_data = resp.json()
                log("INFO", f"Response:\n{pretty_json(response_data)}")
            except Exception:
                pass  # 204 No Content heeft geen body, dat is OK

        return True

    except requests.exceptions.ConnectionError:
        log("FOUT", f"Kan geen verbinding maken met {ROUTER_IP}:{ROUTER_PORT}. "
                    "Controleer of de router bereikbaar is en RESTCONF actief is.")
        return False
    except requests.exceptions.Timeout:
        log("FOUT", "Timeout — router reageert niet binnen 15 seconden.")
        return False
    except Exception as e:
        log("FOUT", f"Onverwachte fout: {e}")
        return False


def restconf_get(pad: str, omschrijving: str) -> dict | None:
    """
    Voert een RESTCONF GET uit en retourneert de geparseerde response als dict.
    """
    url = f"{BASE_URL}/{pad}"
    log("INFO", f"GET → {url} ({omschrijving})")
    try:
        resp = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            headers=HEADERS,
            verify=False,
            timeout=15,
        )
        if resp.status_code == 200:
            log("OK", f"HTTP {resp.status_code} — {omschrijving}")
            data = resp.json()
            log("INFO", f"Response:\n{pretty_json(data)}")
            return data
        else:
            log("FOUT", f"HTTP {resp.status_code} bij GET {pad}")
            return None
    except Exception as e:
        log("FOUT", f"GET mislukt: {e}")
        return None


# ─── Stap 1: Config ophalen van GitHub ───────────────────────────────────────
def haal_config_op_van_github(url: str) -> dict:
    log("INFO", f"JSON configuratie ophalen van GitHub: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        config = resp.json()
        log("OK", f"Config succesvol opgehaald (HTTP {resp.status_code}, {len(resp.content)} bytes)")
        log("INFO", f"Config preview:\n{pretty_json(config)[:800]}")
        return config
    except requests.exceptions.RequestException as e:
        log("FOUT", f"Fout bij ophalen GitHub config: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log("FOUT", f"GitHub config is geen geldige JSON: {e}")
        sys.exit(1)


# ─── Stap 2: RESTCONF deployment ─────────────────────────────────────────────
def deploy_via_restconf(config: dict):
    fouten = []
    native = config.get("Cisco-IOS-XE-native:native", {})

    # ── 1. Hostname ───────────────────────────────────────────────────────
    if "hostname" in native:
        payload = {"Cisco-IOS-XE-native:hostname": native["hostname"]}
        ok = restconf_put(
            "Cisco-IOS-XE-native:native/hostname",
            payload,
            "Hostname configureren"
        )
        if not ok:
            fouten.append("hostname")

    # ── 2. Interfaces ─────────────────────────────────────────────────────
    if "interface" in native:
        ifaces = native["interface"]

        # GigabitEthernet interfaces
        if "GigabitEthernet" in ifaces:
            payload = {
                "Cisco-IOS-XE-native:GigabitEthernet": ifaces["GigabitEthernet"]
            }
            ok = restconf_put(
                "Cisco-IOS-XE-native:native/interface/GigabitEthernet",
                payload,
                "GigabitEthernet interfaces configureren"
            )
            if not ok:
                fouten.append("GigabitEthernet interfaces")

        # Loopback interfaces (indien aanwezig)
        if "Loopback" in ifaces:
            payload = {
                "Cisco-IOS-XE-native:Loopback": ifaces["Loopback"]
            }
            ok = restconf_put(
                "Cisco-IOS-XE-native:native/interface/Loopback",
                payload,
                "Loopback interfaces configureren"
            )
            if not ok:
                fouten.append("Loopback interfaces")

    # ── 3. Static routes ──────────────────────────────────────────────────
    if "ip" in native and "route" in native["ip"]:
        payload = {"Cisco-IOS-XE-native:route": native["ip"]["route"]}
        ok = restconf_put(
            "Cisco-IOS-XE-native:native/ip/route",
            payload,
            "Static routes configureren"
        )
        if not ok:
            fouten.append("static routes")

    # ── 4. OSPF (indien aanwezig in config) ───────────────────────────────
    if "router" in native and "ospf" in native.get("router", {}):
        payload = {
            "Cisco-IOS-XE-native:router": {
                "Cisco-IOS-XE-ospf:ospf": native["router"]["ospf"]
            }
        }
        ok = restconf_put(
            "Cisco-IOS-XE-native:native/router/ospf",
            payload,
            "OSPF configureren"
        )
        if not ok:
            fouten.append("OSPF")

    return fouten


# ─── Stap 3: Verificatie ──────────────────────────────────────────────────────
def verificeer(config: dict):
    native = config.get("Cisco-IOS-XE-native:native", {})
    log("INFO", "Verificatie via RESTCONF GET...")

    if "hostname" in native:
        restconf_get(
            "Cisco-IOS-XE-native:native/hostname",
            "Hostname verificeren"
        )

    if "interface" in native and "GigabitEthernet" in native["interface"]:
        # Eerste interface ophalen als verificatie
        eerste = native["interface"]["GigabitEthernet"][0]
        naam = eerste.get("name", "0/0/1").replace("/", "%2F")
        restconf_get(
            f"Cisco-IOS-XE-native:native/interface/GigabitEthernet={naam}",
            f"Interface GigabitEthernet{eerste.get('name')} verificeren"
        )


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Task 38 – RESTCONF Deployment via GitHub (Python)")
    print("=" * 60)

    # 1. Config ophalen
    config = haal_config_op_van_github(GITHUB_RAW_URL)

    # 2. Deployen
    print()
    fouten = deploy_via_restconf(config)

    # 3. Verificatie
    print()
    verificeer(config)

    # 4. Samenvatting
    print()
    print("=" * 60)
    if fouten:
        log("WARN", f"Deployment voltooid MET fouten in: {', '.join(fouten)}")
        sys.exit(1)
    else:
        log("OK", "Deployment volledig geslaagd — alle onderdelen geconfigureerd.")
    print("=" * 60)
