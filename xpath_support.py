from ncclient import manager

# Define your XPath filter
XPATH_OSPF = """
<filter type="xpath" select="/network-instances/network-instance"/>
"""

# Connect to device
with manager.connect(
    host="srl-01",
    port=830,
    username="admin",
    password="NokiaSrl1!",
    hostkey_verify=False
) as m:

    # Check device supports xpath capability (optional but good practice)
    if ":xpath" in m.server_capabilities:
        response = m.get_config(
            source="running",
            filter=XPATH_OSPF
        )
        print(response.xml)

    else:
        print("Device does not support XPath filtering")

