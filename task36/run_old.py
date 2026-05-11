from ncclient import manager
import requests
import sys

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


def main():
    xml_config = fetch_xml(GITHUB_RAW_URL)

    print("[+] Verbinden met NETCONF device...")
    with manager.connect(**DEVICE) as m:
        print(f"[+] Verbonden. Session ID: {m.session_id}")

        # Detecteer datastore
        target, needs_commit = detect_datastore(m)

        print(f"[+] Deploy config naar {target}...")
        reply = m.edit_config(target=target, config=xml_config)
        print(reply)

        if needs_commit:
            print("[+] Commit uitvoeren...")
            m.commit()

        print("[+] Config succesvol toegepast.")


if __name__ == "__main__":
    main()