from ncclient import manager
import xmltodict

# import pprint
import xml.etree.ElementTree as ET
import xml.dom.minidom
import sys


def pretty_print_xml(xml_string):
    # Parse the XML string
    dom = xml.dom.minidom.parseString(xml_string)

    # Pretty print the XML
    pretty_xml = dom.toprettyxml(indent="  ")

    # Remove empty lines
    pretty_xml = "\n".join(line for line in pretty_xml.split("\n") if line.strip())

    print(pretty_xml)


# Parse from a file
# tree = ET.parse('your_file.xml')
# Write back to a file
# tree.write('pretty_file.xml', encoding='utf-8', xml_declaration=True)
# or get as a string
# pretty_xml_string = ET.tostring(root, encoding='utf-8').decode()
# Note: tostring does not automatically pretty-print before Python 3.9 without a custom indent function


# Filter: Get ALL interfaces
CEOS_INTERFACES = """
<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
"""

SRL_INTERFACES = """
<interfaces xmlns="http://openconfig.net/yang/interfaces"/>
"""

# Filter: Get one specific interface by name
ONE_SRL_INTERFACE = """
<interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>
        <name>ethernet-1/1</name>
    </interface>
</interfaces>
"""

ONE_CEOS_INTERFACE = """
<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
        <name>Ethernet1</name>
    </interface>
</interfaces>
"""

SRL_NETINSTANCE = """
<network-instance xmlns="urn:nokia.com:srlinux:net-inst:network-instance"/>
"""

ARISTA_NATIVE_FILTER = """
<interfaces xmlns="http://arista.com/yang/openconfig/interfaces/augments">
    <interface>
        <name>Ethernet1</name>
    </interface>
</interfaces>
"""

TRY_FILTER = """
<interfaces "http://arista.com/yang/experimental/eos/arista-interfaces-rates"/>
"""

class NetconfTransport:
    def __init__(self, host, username, password, port=830):
        self.params = dict(
            host=host,
            port=port,
            username=username,
            password=password,
            hostkey_verify=False,
            device_params={"name": "default"},
        )

    def get_config(self, filter_xml: str) -> dict:
        with manager.connect(**self.params) as m:
            result = m.get_config(source="running", filter=("subtree", filter_xml))
            return result.data_xml  # xmltodict.parse(result.data_xml)

    #    def push_config(self, payload_xml: str, confirmed=True, timeout=120) -> bool:
    #        with manager.connect(**self.params) as m:
    #            m.edit_config(target="running", config=payload_xml)
    #            #m.validate(source="candidate")
    #            #if confirmed:
    #            #    m.commit(confirmed=True, timeout=str(timeout))
    #            #else:
    #            #    m.commit()
    #            return True

    def push_config(self, payload_xml: str) -> bool:
        with manager.connect(**self.params) as m:
            caps = " ".join(m.server_capabilities)

            has_candidate = ":candidate" in caps
            has_validate = ":validate" in caps

            if has_candidate:
                m.edit_config(target="candidate", config=payload_xml)

                # Only call validate if the server actually supports it
                if has_validate:
                    m.validate(source="candidate")

                # You might also want to gate confirmed commit:
                # has_confirmed_commit = "confirmed-commit" in caps
                # For now, just do a normal commit:
                m.commit()
                print("Configuration is committed")
            else:
                m.edit_config(
                    target="running",
                    config=payload_xml,
                    default_operation="merge",
                )
                print("Configuration is merged")
        return True

    def get_cap(self) -> bool:
        with manager.connect(**self.params) as m:
            for cap in m.server_capabilities:
                if any(x in cap for x in ["candidate", "writable", "startup"]):
                    print(cap)
        return True


if __name__ == "__main__":

    transport = NetconfTransport("ceos-01", "admin", "admin")
    transport.get_cap()

    print("#" * 10, "Before")
    result = transport.get_config(TRY_FILTER)
    pretty_print_xml(result)

    if len(sys.argv) < 2:
        exit(0)
    file_path = sys.argv[1]

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except e:
        print(e)
        exit(0)

    transport.push_config(content)

    print("#" * 10, "After")
    result = transport.get_config(SRL_NETINSTANCE)
    pretty_print_xml(result)
