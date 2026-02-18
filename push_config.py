import sys
from ncclient import manager

devices = {
    "srl": {
        "host": "srl-01",
        "port": 830,
        "username": "admin",
        "password": "NokiaSrl1!",
        "hostkey_verify": False,
    },
    "ceos": {
        "host": "ceos-01",
        "port": 830,
        "username": "admin",
        "password": "admin",
        "hostkey_verify": False,
    },
}


if len(sys.argv) < 3:
    print(f"Expecting: {sys.argv[0]} <device> <XML file>")
    sys.exit(0)

device, file_path = sys.argv[1], sys.argv[2]

if device in devices:

    with open(file_path, "r", encoding="utf-8") as file:
        payload_xml = file.read()

        with manager.connect(**devices[device]) as m:
            caps = " ".join(m.server_capabilities)

            has_candidate = ":candidate" in caps
            has_validate = ":validate" in caps
            has_confirmed_commit = ":has_confirmed_commit" in caps

            if has_candidate:
                m.edit_config(target="candidate", config=payload_xml)

                if has_validate:
                    m.validate(source="candidate")

                if has_confirmed_commit:
                    m.commit(confirmed=True, timeout=str(timeout))

                m.commit()
                print("Configuration is committed")
            else:
                m.edit_config(
                    target="running",
                    config=payload_xml,
                    default_operation="merge",
                )
                print("Configuration is merged")

else:
    print(f"Avaliable devices are: {', '.join(devices.keys())}.")
