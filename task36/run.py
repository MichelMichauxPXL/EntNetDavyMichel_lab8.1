from ncclient import manager
import requests
import sys

# ---------- CONFIGUREER HIER JE PARAMETERS ----------

GITHUB_RAW_URL = "https://raw.githubusercontent.com/MichelMichauxPXL/EntNetDavyMichel_lab8.1/d440adf7d40bea67f1594e939e3e13dee85bf847/task36/router01.xml"

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

TARGET_DATASTORE = "running"       # of "candidate" als je dat gebruikt

# ----------------------------------------------------


def fetch_xml_from_github(url: str) -> str:
    """Haalt een XML-configuratiebestand op uit GitHub (raw URL)."""
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def deploy_config_via_netconf(device_params: dict, xml_config: str, target: str = "running"):
    """Deployt de meegegeven XML-config via NETCONF op IOS-XE."""
    print(f"[+] Verbinden met {device_params['host']} via NETCONF...")
    with manager.connect(**device_params) as m:
        print(f"[+] Verbonden. Session ID: {m.session_id}")

        # Optioneel: capabilities tonen
        # for cap in m.server_capabilities:
        #     print(cap)

        print(f"[+] Deploy config naar datastore: {target}")
        reply = m.edit_config(target=target, config=xml_config, default_operation="merge")
        print("[+] NETCONF reply:")
        print(reply)


def main():
    try:
        print(f"[+] Haal XML-config op uit GitHub: {GITHUB_RAW_URL}")
        xml_config = fetch_xml_from_github(GITHUB_RAW_URL)

        # Kleine sanity check
        if "<config" not in xml_config:
            print("[!] Waarschuwing: XML bevat geen <config>-element. Controleer je YANG-based XML.")
        
        deploy_config_via_netconf(DEVICE, xml_config, TARGET_DATASTORE)
        print("[+] Config succesvol gepusht (tenzij NETCONF een error gaf).")

    except requests.HTTPError as e:
        print(f"[X] HTTP-fout bij ophalen van GitHub: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[X] Onverwachte fout: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()