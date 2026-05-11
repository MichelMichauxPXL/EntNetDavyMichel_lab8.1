"""
Task 36 – NETCONF (Python)
==========================
Haalt een YANG-XML configuratiebestand op uit GitHub en deployt het
via NETCONF op een Cisco IOS-XE toestel.

Vereisten (uit projectopdracht):
  - NETCONF + YANG
  - Candidate datastore
  - GitHub als single source of truth
  - Foutafhandeling met discard-changes
  - Statusinformatie expliciet zichtbaar (<ok/> of error)
  - Pretty-print van XML responses
"""

import sys
import requests
from xml.dom.minidom import parseString
from ncclient import manager
from ncclient.operations import RPCError

# ─── Instellingen ────────────────────────────────────────────────────────────
# GitHub: raw URL naar je XML configuratiebestand
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/MichelMichauxPXL/EntNetDavyMichel_lab8.1/main/davytest/router-config.xml"
)

# Router verbindingsinstellingen
ROUTER = {
    "host":            "172.17.1.1",   # Management IP (VLAN 11)
    "port":            830,            # NETCONF standaard poort
    "username":        "admin",
    "password":        "cisco123",
    "hostkey_verify":  False,
    "device_params":   {"name": "iosxe"},
}


# ─── Hulpfuncties ────────────────────────────────────────────────────────────
def pretty_xml(xml_str: str) -> str:
    """Geeft XML terug als leesbaar geïndenteerd formaat."""
    try:
        return parseString(xml_str).toprettyxml(indent="  ")
    except Exception:
        return xml_str  # fallback als XML niet parseable is


def log(level: str, bericht: str):
    """Eenvoudige logger met niveau-aanduiding."""
    prefix = {"INFO": "[*]", "OK": "[+]", "FOUT": "[-]", "WARN": "[!]"}.get(level, "[?]")
    print(f"{prefix} {bericht}")


def check_rpc_ok(reply):
    """
    Controleert of een NETCONF RPC-reply <ok/> bevat.
    Gooit een RuntimeError als de reply een fout bevat.
    Retourneert True bij succes.
    """
    reply_xml = str(reply)
    log("INFO", "RPC-reply ontvangen:")
    print(pretty_xml(reply_xml))

    if "<ok/>" in reply_xml or "<ok />" in reply_xml:
        log("OK", "Statusfeedback: <ok/> — operatie geslaagd.")
        return True
    elif "rpc-error" in reply_xml:
        # Haal error-tag en error-message op voor duidelijke foutmelding
        dom = parseString(reply_xml)
        error_tag  = dom.getElementsByTagNameNS("*", "error-tag")
        error_msg  = dom.getElementsByTagNameNS("*", "error-message")
        tag = error_tag[0].firstChild.nodeValue  if error_tag  else "onbekend"
        msg = error_msg[0].firstChild.nodeValue  if error_msg  else "geen details"
        raise RuntimeError(f"NETCONF fout — error-tag: {tag} | error-message: {msg}")
    else:
        log("WARN", "Reply bevat geen <ok/> maar ook geen rpc-error. Controleer handmatig.")
        return False


# ─── Stap 1: Configuratie ophalen van GitHub ─────────────────────────────────
def haal_config_op_van_github(url: str) -> str:
    log("INFO", f"Configuratie ophalen van GitHub: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        log("OK", f"Config succesvol opgehaald ({len(resp.content)} bytes, HTTP {resp.status_code})")
        return resp.text
    except requests.exceptions.RequestException as e:
        log("FOUT", f"Fout bij ophalen GitHub config: {e}")
        sys.exit(1)


# ─── Stap 2: NETCONF deployment ──────────────────────────────────────────────
def deploy_via_netconf(config_xml: str):
    log("INFO", f"Verbinding maken met router {ROUTER['host']}:{ROUTER['port']} via NETCONF...")

    try:
        with manager.connect(**ROUTER) as conn:
            log("OK", f"Verbonden. Session-ID: {conn.session_id}")

            # ── Capabilities controleren ──────────────────────────────────
            log("INFO", "Ondersteunde NETCONF capabilities:")
            for cap in sorted(conn.server_capabilities):
                print(f"    {cap}")

            # ── Candidate datastore locken ────────────────────────────────
            log("INFO", "Candidate datastore locken...")
            try:
                lock_reply = conn.lock(target="candidate")
                check_rpc_ok(lock_reply)
            except RPCError as e:
                log("FOUT", f"Lock mislukt: {e}")
                sys.exit(1)

            # ── edit-config naar candidate ────────────────────────────────
            log("INFO", "edit-config uitvoeren naar candidate datastore...")
            try:
                edit_reply = conn.edit_config(
                    target="candidate",
                    config=config_xml,
                )
                check_rpc_ok(edit_reply)
            except (RPCError, RuntimeError) as e:
                log("FOUT", f"edit-config mislukt: {e}")
                log("INFO", "discard-changes uitvoeren om candidate terug te zetten...")
                discard_reply = conn.discard_changes()
                check_rpc_ok(discard_reply)
                log("INFO", "Candidate datastore unlocken...")
                conn.unlock(target="candidate")
                sys.exit(1)

            # ── Commit naar running ───────────────────────────────────────
            log("INFO", "Commit uitvoeren naar running datastore...")
            try:
                commit_reply = conn.commit()
                check_rpc_ok(commit_reply)
                log("OK", "Configuratie succesvol gecommit naar running.")
            except (RPCError, RuntimeError) as e:
                log("FOUT", f"Commit mislukt: {e}")
                log("INFO", "discard-changes uitvoeren...")
                conn.discard_changes()
                conn.unlock(target="candidate")
                sys.exit(1)

            # ── Candidate datastore unlocken ──────────────────────────────
            log("INFO", "Candidate datastore unlocken...")
            unlock_reply = conn.unlock(target="candidate")
            check_rpc_ok(unlock_reply)

            # ── Verificatie: running config ophalen ───────────────────────
            log("INFO", "Verificatie: running-config ophalen via NETCONF get-config...")
            running = conn.get_config(source="running")
            log("OK", "Running-config ontvangen (eerste 2000 tekens):")
            print(pretty_xml(str(running))[:2000])

    except Exception as e:
        log("FOUT", f"Onverwachte fout: {e}")
        sys.exit(1)


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Task 36 – NETCONF Deployment via GitHub (Python)")
    print("=" * 60)

    config_xml = haal_config_op_van_github(GITHUB_RAW_URL)

    print("\n--- GitHub XML payload (preview) ---")
    print(pretty_xml(config_xml)[:1000])
    print("---\n")

    deploy_via_netconf(config_xml)

    print("\n" + "=" * 60)
    print("  Deployment voltooid.")
    print("=" * 60)
