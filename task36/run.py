from ncclient import manager
import requests

# ---------- CONFIGUREER HIER JE PARAMETERS ----------
GITHUB_RAW_URL = "https://raw.githubusercontent.com/MichelMichauxPXL/EntNetDavyMichel_lab8.1/refs/heads/main/task36/router01.xml"
DEVICE = {
    "host": "172.17.1.1",          # IP van je IOS-XE toestel
    "port": 830,
    "username": "admin",
    "password": "cisco123",
    "hostkey_verify": False,
    "device_params": {"name": "iosxe"},  # belangrijk voor IOS-XE
    "allow_agent": False,
    "look_for_keys": False,
    "timeout": 30,
}


def fetch_xml(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.text


def detect_datastore(m):
    """Detecteert automatisch of de router writable-running ondersteunt."""
    caps = list(m.server_capabilities)
    if any("writable-running" in c for c in caps):
        print("[+] Router ondersteunt :writable-running → target = running")
        return "running", False
    if any("candidate" in c for c in caps):
        print("[+] Router ondersteunt GEEN writable-running → target = candidate + commit")
        return "candidate", True
    raise Exception("Geen geschikte datastore gevonden (running/candidate).")


def wrap_config(xml_config):
    """
    Zorgt ervoor dat de XML altijd in een <config> root-element zit,
    zoals ncclient vereist voor edit_config.
    """
    stripped = xml_config.strip()
    if not stripped.startswith("<config"):
        return f"<config>{stripped}</config>"
    return stripped


def main():
    xml_config = fetch_xml(GITHUB_RAW_URL)
    xml_config = wrap_config(xml_config)

    print("[+] Verbinden met NETCONF device...")

    # FIX 1: gebruik 'with' statement — sluit de sessie automatisch af,
    #         ook bij exceptions. Vervangt de try/finally + m.close() constructie.
    # FIX 2: manager.connect() gooit een exception bij falen, returnt nooit None.
    #         De None-check was dode code en is verwijderd.
    with manager.connect(**DEVICE) as m:
        print(f"[+] Verbonden. Session ID: {m.session_id}")

        # Detecteer datastore
        target, needs_commit = detect_datastore(m)

        print(f"[+] Deploy config naar {target}...")
        # FIX 3: config is nu gegarandeerd gewikkeld in <config>...</config>
        reply = m.edit_config(target=target, config=xml_config)
        print(reply)

        if needs_commit:
            print("[+] Commit uitvoeren...")
            m.commit()

        print("[+] Config succesvol toegepast.")

    # FIX 4: m.close() → m.close_session() is niet meer nodig;
    #         het 'with' blok roept close_session() automatisch aan.


if __name__ == "__main__":
    main()