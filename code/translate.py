from jinja2 import Template
from intent import InterfaceIntent


class InterfaceTranslator:
    TEMPLATE = Template("""
<config>
  <interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>
      <name>{{ name }}</name>
      <config>
        <name>{{ name }}</name>
        <type xmlns:iana-if-type="urn:ietf:params:xml:ns:yang:iana-if-type">
          iana-if-type:ethernetCsmacd
        </type>
        <enabled>{{ enabled | lower }}</enabled>
      </config>
      <subinterfaces>
        <subinterface>
          <index>0</index>
          <config>
            <index>0</index>
            <enabled>{{ enabled | lower }}</enabled>
          </config>
          <ipv4 xmlns="http://openconfig.net/yang/interfaces/ip">
            <addresses>
              <address>
                <ip>{{ ip_address }}</ip>
                <config>
                  <ip>{{ ip_address }}</ip>
                  <prefix-length>{{ prefix_length }}</prefix-length>
                </config>
              </address>
            </addresses>
            <config>
              <enabled>{{ enabled | lower }}</enabled>
            </config>
          </ipv4>
        </subinterface>
      </subinterfaces>
    </interface>
  </interfaces>
</config>
""")

    def translate(self, intent: InterfaceIntent) -> str:
        return self.TEMPLATE.render(**intent.__dict__)


if __name__ == "__main__":

    intent = InterfaceIntent(
        name="ethernet-1/1",
        description="To cEOS",
        ip_address="192.168.1.1",
        prefix_length=24,
        enabled=True,
        mtu=1500,
    )

    translator = InterfaceTranslator()
    result = translator.translate(intent)
    print(result)
