import sys
import requests
from xml.dom.minidom import parseString
from ncclient import manager
from ncclient.operations import RPCError

# ==============================================================
#  INSTELLINGEN
# ==============================================================
GITHUB_URL = "https://raw.githubusercontent.com/MichelMichauxPXL/EntNetDavyMichel_lab8.1/main/davytest/router-config.xml"

ROUTER = {
    "host":           "172.17.1.1",   # Management IP van de router (VLAN 11)
    "port":           830,            # NETCONF standaard poort
    "username":       "admin",
    "password":       "cisco123",
    "hostkey_verify": False,          # Self-signed certificaat negeren
    "device_params":  {"name": "iosxe"},
}

# ==============================================================
#  HULPFUNCTIES
# ==============================================================

def log(ok, tekst):
    """Toont [+] bij succes of [-] bij fout."""
    print(f"{'[+]' if ok else '[-]'} {tekst}")


def pretty_xml(xml_str):
    """Zet XML om naar leesbaar geïndenteerd formaat (toprettyxml)."""
    try:
        return parseString(xml_str).toprettyxml(indent="  ")
    except Exception:
        return xml_str  # fallback als XML niet parseerbaar is


def check_ok(reply):
    """
    Controleert of de NETCONF RPC-reply een <ok/> bevat.
    Dit is de standaard NETCONF statusfeedback bij een geslaagde operatie.
    Gooit een fout als de reply een rpc-error bevat.
    """
    xml = str(reply)
    print(pretty_xml(xml))  # Altijd tonen voor transparantie

    if "<ok/>" in xml or "<ok />" in xml:
        log(True, "Statusfeedback: <ok/> — operatie geslaagd.")
        return True
    elif "rpc-error" in xml:
        # Haal de foutdetails op uit de XML
        dom = parseString(xml)
        tag = dom.getElementsByTagNameNS("*", "error-tag")
        msg = dom.getElementsByTagNameNS("*", "error-message")
        tag_val = tag[0].firstChild.nodeValue if tag else "onbekend"
        msg_val = msg[0].firstChild.nodeValue if msg else "geen details"
        raise RuntimeError(f"NETCONF fout — error-tag: {tag_val} | bericht: {msg_val}")
    else:
        log(False, "Geen <ok/> en geen rpc-error — controleer handmatig.")
        return False


# ==============================================================
#  STAP 1 – CONFIG OPHALEN VAN GITHUB
#  GitHub fungeert als single source of truth voor de YANG-XML config
# ==============================================================
print("=" * 55)
print("  Task 36 – NETCONF deployment via GitHub")
print("=" * 55)

print(f"\n[*] Config ophalen van GitHub...")
resp = requests.get(GITHUB_URL, timeout=15)
if resp.status_code != 200:
    log(False, f"GitHub ophalen mislukt (HTTP {resp.status_code})")
    sys.exit(1)

config_xml = resp.text
log(True, f"Config opgehaald ({len(resp.content)} bytes, HTTP {resp.status_code})")

# Korte preview van de XML payload
print("\n[*] XML payload preview (eerste 500 tekens):")
print(pretty_xml(config_xml)[:500])

# ==============================================================
#  STAP 2 – DEPLOYMENT VIA NETCONF
# ==============================================================
print(f"\n[*] Verbinding maken met {ROUTER['host']}:{ROUTER['port']} via NETCONF...")

try:
    with manager.connect(**ROUTER) as conn:
        log(True, f"Verbonden — Session-ID: {conn.session_id}")

        # --- Candidate datastore locken ---
        # Voorkomt dat andere sessies tegelijk wijzigingen maken
        print("\n[*] Candidate datastore locken...")
        try:
            check_ok(conn.lock(target="candidate"))
        except RPCError as e:
            log(False, f"Lock mislukt: {e}")
            sys.exit(1)

        # --- edit-config naar candidate ---
        # Stuurt de volledige YANG-XML config naar de candidate datastore
        # Bij fout: discard-changes zodat candidate schoon blijft
        print("\n[*] edit-config uitvoeren naar candidate...")
        try:
            check_ok(conn.edit_config(target="candidate", config=config_xml))
        except (RPCError, RuntimeError) as e:
            log(False, f"edit-config mislukt: {e}")
            print("[*] discard-changes uitvoeren (candidate terugzetten)...")
            check_ok(conn.discard_changes())
            conn.unlock(target="candidate")
            sys.exit(1)

        # --- Commit naar running ---
        # Maakt de wijzigingen actief op het toestel
        # Bij fout: discard-changes om alles terug te draaien
        print("\n[*] Commit uitvoeren naar running...")
        try:
            check_ok(conn.commit())
            log(True, "Configuratie succesvol gecommit naar running.")
        except (RPCError, RuntimeError) as e:
            log(False, f"Commit mislukt: {e}")
            print("[*] discard-changes uitvoeren...")
            check_ok(conn.discard_changes())
            conn.unlock(target="candidate")
            sys.exit(1)

        # --- Candidate datastore unlocken ---
        # Altijd unlocken, ook na succes
        print("\n[*] Candidate datastore unlocken...")
        check_ok(conn.unlock(target="candidate"))

        # ==============================================================
        #  STAP 3 – VERIFICATIE
        #  Haalt de volledige running-config op via NETCONF get-config
        # ==============================================================
        print("\n[*] Verificatie: running-config ophalen via get-config...")
        running = conn.get_config(source="running")
        log(True, "Running-config ontvangen (preview eerste 1500 tekens):")
        print(pretty_xml(str(running))[:1500])

except Exception as e:
    log(False, f"Onverwachte fout: {e}")
    sys.exit(1)

# ==============================================================
#  RESULTAAT
# ==============================================================
print("\n" + "=" * 55)
log(True, "Deployment volledig geslaagd!")
print("=" * 55)