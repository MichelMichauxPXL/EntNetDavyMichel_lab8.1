import xml.dom.minidom

from ncclient import manager
m = manager.connect(
    host="10.176.163.10",
    port=830,
    username="cisco",
    password="cisco123!",
    hostkey_verify=False
)

'''GET
print("#Supported Capabilities (YANG models):")
for capability in m.server_capabilities:
    print(capability)
'''

'''FILTER
netconf_filter = """
<filter>
<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native" />
</filter>
"""

netconf_reply = m.get_config(source="running", filter=netconf_filter)
print(xml.dom.minidom.parseString(netconf_reply.xml).toprettyxml())
'''

'''EDIT
netconf_hostname = """
<config>
<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
<hostname>NEWHOSTNAME</hostname>
</native>
</config>
"""

netconf_reply = m.edit_config(target="running", config=netconf_hostname)
print(xml.dom.minidom.parseString(netconf_reply.xml).toprettyxml())
'''

'''EDIT LOOPBACK
netconf_loopback = """
<config>
    <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
        <interface>
            <Loopback>
                <name>1</name>
                <description>My first NETCONF loopback</description>
                <ip>
                    <address>
                        <primary>
                            <address>10.1.1.1</address>
                            <mask>255.255.255.0</mask>
                        </primary>
                    </address>
                </ip>
            </Loopback>
        </interface>
    </native>
</config>
"""

netconf_reply = m.edit_config(target="running", config=netconf_loopback)
print(xml.dom.minidom.parseString(netconf_reply.xml).toprettyxml())
'''

netconf_newloop = """
<config>
<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
    <interface>
        <Loopback>
            <name>2</name>
            <description>My second NETCONF loopback</description>
            <ip>
                <address>
                    <primary>
                        <address>10.1.1.1</address>
                        <mask>255.255.255.0</mask>
                    </primary>
                </address>
            </ip>
        </Loopback>
        </interface>
    </native>
</config>
"""

netconf_reply = m.edit_config(target="running", config=netconf_newloop)