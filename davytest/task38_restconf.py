"""
Task 38 – RESTCONF (Python)
============================
Haalt een YANG-compliant JSON configuratiebestand op uit GitHub en
deployt het via RESTCONF op een Cisco IOS-XE toestel.

Fix: PUT op een lijst geeft HTTP 405. Oplossing: PATCH per item afzonderlijk.
"""

import sys
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Instellingen ─────────────────────────────────────────────────────────────
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/MichelMichauxPXL/EntNetDavyMichel_lab8.1/main/davytest/router-config.json"
)

ROUTER_IP   = "172.17.1.1"
ROUTER_PORT = 443
USERNAME    = "admin"
PASSWORD    = "cisco123"

BASE_URL = f"https://{ROUTER_IP}:{ROUTER_PORT}/restconf/data"

HEADERS = {
    "Content-Type": "application/yang-data+json",
    "Accept":       "application/yang-data+json",
}

SUCCESS_CODES = {200, 201, 204}


# ─── Hulpfuncties ─────────────────────────────────────────────────────────────
def log(level: str, bericht: str):
    prefix = {"INFO": "[*]", "OK": "[+]", "FOUT": "[-]", "WARN": "[!]"}.get(level, "[?]")
    print(f"{prefix} {bericht}")


def pretty_json(data) -> str:
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2, ensure_ascii=False)
    try:
        return json.dumps(json.loads(data), indent=2, ensure_ascii=False)
    except Exception:
        return str(data)


def restconf_patch(pad: str, payload: dict, omschrijving: str) -> bool:
    """PATCH op een specifiek pad — werkt voor zowel bestaande als nieuwe resources."""
    url = f"{BASE_URL}/{pad}"
    log("INFO", f"{omschrijving}")
    log("INFO", f"PATCH → {url}")
    log("INFO", f"Payload:\n{pretty_json(payload)}")

    try:
        resp = requests.patch(
            url,
            auth=(USERNAME, PASSWORD),
            headers=HEADERS,
            json=payload,
            verify=False,
            timeout=15,
        )

        if resp.status_code in SUCCESS_CODES:
            log("OK", f"HTTP {resp.status_code} — {omschrijving} geslaagd.")
        else:
            log("FOUT", f"HTTP {resp.status_code} — {omschrijving} mislukt.")
            try:
                log("FOUT", f"Response body:\n{pretty_json(resp.json())}")
            except Exception:
                log("FOUT", f"Response body (raw): {resp.text[:500]}")
            return False

        return True

    except requests.exceptions.ConnectionError:
        log("FOUT", f"Geen verbinding met {ROUTER_IP}:{ROUTER_PORT}.")
        return False
    except requests.exceptions.Timeout:
        log("FOUT", "Timeout — router reageert niet.")
        return False
    except Exception as e:
        log("FOUT", f"Onverwachte fout: {e}")
        return False


def restconf_get(pad: str, omschrijving: str) -> dict | None:
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


# ─── Config ophalen van GitHub ────────────────────────────────────────────────
def haal_config_op_van_github(url: str) -> dict:
    log("INFO", f"JSON configuratie ophalen van GitHub: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        config = resp.json()
        log("OK", f"Config succesvol opgehaald (HTTP {resp.status_code}, {len(resp.content)} bytes)")
        return config
    except requests.exceptions.RequestException as e:
        log("FOUT", f"Fout bij ophalen GitHub config: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log("FOUT", f"GitHub config is geen geldige JSON: {e}")
        sys.exit(1)


# ─── Deployment ───────────────────────────────────────────────────────────────
def deploy_via_restconf(config: dict):
    fouten = []
    native = config.get("Cisco-IOS-XE-native:native", {})

    # ── 1. Hostname ───────────────────────────────────────────────────────────
    if "hostname" in native:
        payload = {"Cisco-IOS-XE-native:hostname": native["hostname"]}
        ok = restconf_patch(
            "Cisco-IOS-XE-native:native/hostname",
            payload,
            "Hostname configureren"
        )
        if not ok:
            fouten.append("hostname")

    # ── 2. GigabitEthernet interfaces — één voor één ──────────────────────────
    if "interface" in native and "GigabitEthernet" in native["interface"]:
        for iface in native["interface"]["GigabitEthernet"]:
            naam = iface["name"]
            # Slashes URL-encoden: 0/0/1 → 0%2F0%2F1
            naam_encoded = naam.replace("/", "%2F")
            payload = {"Cisco-IOS-XE-native:GigabitEthernet": iface}
            ok = restconf_patch(
                f"Cisco-IOS-XE-native:native/interface/GigabitEthernet={naam_encoded}",
                payload,
                f"GigabitEthernet{naam} configureren"
            )
            if not ok:
                fouten.append(f"GigabitEthernet{naam}")

    # ── 3. Loopback interfaces — één voor één ────────────────────────────────
    if "interface" in native and "Loopback" in native["interface"]:
        for lb in native["interface"]["Loopback"]:
            naam = lb["name"]
            payload = {"Cisco-IOS-XE-native:Loopback": lb}
            ok = restconf_patch(
                f"Cisco-IOS-XE-native:native/interface/Loopback={naam}",
                payload,
                f"Loopback{naam} configureren"
            )
            if not ok:
                fouten.append(f"Loopback{naam}")

    # ── 4. Static routes ──────────────────────────────────────────────────────
    if "ip" in native and "route" in native["ip"]:
        payload = {"Cisco-IOS-XE-native:route": native["ip"]["route"]}
        ok = restconf_patch(
            "Cisco-IOS-XE-native:native/ip/route",
            payload,
            "Static routes configureren"
        )
        if not ok:
            fouten.append("static routes")

    # ── 5. OSPF — per process-ID ──────────────────────────────────────────────
    if "router" in native and "ospf" in native.get("router", {}):
        for ospf_proc in native["router"]["ospf"]:
            proc_id = ospf_proc["id"]
            payload = {
                "Cisco-IOS-XE-ospf:ospf": ospf_proc
            }
            ok = restconf_patch(
                f"Cisco-IOS-XE-native:native/router/ospf={proc_id}",
                payload,
                f"OSPF process {proc_id} configureren"
            )
            if not ok:
                fouten.append(f"OSPF {proc_id}")

    return fouten


# ─── Verificatie ─────────────────────────────────────────────────────────────
def verificeer(config: dict):
    native = config.get("Cisco-IOS-XE-native:native", {})
    log("INFO", "Verificatie via RESTCONF GET...")

    if "hostname" in native:
        restconf_get("Cisco-IOS-XE-native:native/hostname", "Hostname")

    if "interface" in native and "GigabitEthernet" in native["interface"]:
        for iface in native["interface"]["GigabitEthernet"]:
            naam = iface["name"]
            naam_encoded = naam.replace("/", "%2F")
            restconf_get(
                f"Cisco-IOS-XE-native:native/interface/GigabitEthernet={naam_encoded}",
                f"GigabitEthernet{naam}"
            )

    if "interface" in native and "Loopback" in native["interface"]:
        for lb in native["interface"]["Loopback"]:
            restconf_get(
                f"Cisco-IOS-XE-native:native/interface/Loopback={lb['name']}",
                f"Loopback{lb['name']}"
            )


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Task 38 – RESTCONF Deployment via GitHub (Python)")
    print("=" * 60)

    config = haal_config_op_van_github(GITHUB_RAW_URL)

    print()
    fouten = deploy_via_restconf(config)

    print()
    verificeer(config)

    print()
    print("=" * 60)
    if fouten:
        log("WARN", f"Deployment voltooid MET fouten in: {', '.join(fouten)}")
        sys.exit(1)
    else:
        log("OK", "Deployment volledig geslaagd — alle onderdelen geconfigureerd.")
    print("=" * 60)