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
ALL_INTERFACES = """
<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
"""

# Filter: Get one specific interface by name
ONE_INTERFACE = """
<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
        <name>Ethernet1</name>
    </interface>
</interfaces>
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

    def push_config(self, payload_xml: str, confirmed=True, timeout=120) -> bool:
        # print(payload_xml)
        # return True
        with manager.connect(**self.params) as m:
            caps = " ".join(m.server_capabilities)

            has_candidate = ":candidate" in caps
            has_validate = ":validate" in caps
            # has_confirmed_commit = ":confirmed-commit" in caps

            try:
                if has_candidate:
                    # print(payload_xml)
                    m.edit_config(target="candidate", config=payload_xml)

                    # Only call validate if the server actually supports it
                    if has_validate:
                        # print("calling validate")
                        m.validate(source="candidate")

                    # if has_confirmed_commit and confirmed:
                    #     # print("calling confirm-commit")
                    #     m.commit(confirmed=True, timeout=str(timeout))
                    # else:
                    m.commit()
                    print("Configuration is committed")
                else:
                    m.edit_config(
                        target="running",
                        config=payload_xml,
                        # default_operation="merge"
                    )
                    # print("Configuration is merged")
            except Exception as e:
                print(str(e))
                return False
        return True

    def get_cap(self) -> bool:
        with manager.connect(**self.params) as m:
            for cap in m.server_capabilities:
                if any(x in cap for x in ["candidate", "writable", "startup"]):
                    print(cap)
        return True
