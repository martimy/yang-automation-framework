#!/usr/bin/env python3
from ncclient import manager
import xml.etree.ElementTree as ET

# ── Connection parameters ───────────────────────────────────────
HOST = "srl-01"  # ← change to your SR Linux mgmt IP
PORT = 830
USER = "admin"
PASS = "NokiaSrl1!"

# ── NETCONF configuration payload (SR Linux native YANG) ────────
config_xml = """
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>
      <name>ethernet-1/1</name>
      <config>
        <name>ethernet-1/1</name>
        <type xmlns:iana="urn:ietf:params:xml:ns:yang:iana-if-type">iana:ethernetCsmacd</type>
        <enabled>true</enabled>
      </config>
      <subinterfaces>
        <subinterface>
          <index>0</index>
          <config>
            <index>0</index>
            <enabled>true</enabled>
          </config>
          <ipv4 xmlns="http://openconfig.net/yang/interfaces/ip">
            <addresses>
              <address>
                <ip>192.168.1.1</ip>
                <config>
                  <ip>192.168.1.1</ip>
                  <prefix-length>24</prefix-length>
                </config>
              </address>
            </addresses>
            <config>
              <enabled>true</enabled>
            </config>
          </ipv4>
        </subinterface>
      </subinterfaces>
    </interface>
  </interfaces>
</config>
"""


def main():
    with manager.connect(
        host=HOST,
        port=PORT,
        username=USER,
        password=PASS,
        hostkey_verify=False,  # ← only for lab; use proper certs in production
        allow_agent=False,
        look_for_keys=False,
    ) as m:

        print("Connected to SR Linux NETCONF server")

        # Optional: lock the candidate datastore first (good practice)
        # m.lock("candidate")

        try:
            # Edit candidate configuration
            rpc_reply = m.edit_config(
                target="candidate",
                config=config_xml,
                default_operation="merge",  # merge = add/update without deleting other config
            )
            print("edit-config reply:", rpc_reply.xml)

            # Validate the candidate (optional but recommended)
            validate_reply = m.validate(source="candidate")
            print("validate reply:", validate_reply.xml)

            # Commit the changes
            commit_reply = m.commit()
            print("commit reply:", commit_reply.xml)

            print("Configuration applied successfully!")

        except Exception as e:
            print("Error during NETCONF operation:", str(e))
            if hasattr(e, "xml") and e.xml is not None:
                print("Full RPC error from device:\n", e.xml)
            # Optional: print server capabilities too
            # print("\nServer capabilities:")
            # for cap in m.server_capabilities:
            #     print(cap)
            raise  # or continue to discard_changes()

        finally:
            # Always unlock
            try:
                m.unlock("candidate")
            except:
                pass


if __name__ == "__main__":
    main()
