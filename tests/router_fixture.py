"""IGD giả nói SOAP qua HTTP thật trên loopback, không mở cổng router ngoài."""

import asyncio
import xml.etree.ElementTree as ET

from nostalgia.net.router_discovery import RouterService


class FakeRouter:
    def __init__(self) -> None:
        self.address = "8.8.8.8"
        self.mappings: dict[int, dict[str, str]] = {}
        self.actions: list[str] = []
        self.added = asyncio.Event()
        self.delay_add = False

    async def serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            head = (await reader.readuntil(b"\r\n\r\n")).decode()
            fields = {
                name.lower(): value.strip()
                for line in head.split("\r\n")
                if ":" in line
                for name, value in [line.split(":", 1)]
            }
            payload = await reader.readexactly(int(fields["content-length"]))
            document = ET.fromstring(payload)
            arguments = {
                child.tag.rsplit("}", 1)[-1]: child.text or "" for child in document.iter()
            }
            action = fields["soapaction"].strip('"').split("#")[1]
            self.actions.append(action)
            port = int(arguments.get("NewExternalPort", "0"))
            status = 200
            if action == "GetExternalIPAddress":
                body = f"<NewExternalIPAddress>{self.address}</NewExternalIPAddress>"
            elif action == "GetSpecificPortMappingEntry":
                if port in self.mappings:
                    body = "".join(
                        f"<{key}>{value}</{key}>" for key, value in self.mappings[port].items()
                    )
                else:
                    status, body = 500, "<errorCode>714</errorCode>"
            elif action == "AddPortMapping":
                self.mappings[port] = {
                    key: arguments[key]
                    for key in ("NewInternalClient", "NewInternalPort", "NewPortMappingDescription")
                }
                self.added.set()
                if self.delay_add:
                    await asyncio.sleep(0.1)
                body = ""
            elif action == "DeletePortMapping":
                self.mappings.pop(port, None)
                body = ""
            else:
                raise AssertionError(action)
            response = ("<Envelope><Body>" + body + "</Body></Envelope>").encode()
            writer.write(
                f"HTTP/1.1 {status} Result\r\nContent-Length: {len(response)}\r\n\r\n".encode()
                + response
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    def service(self, port: int) -> RouterService:
        return RouterService(
            "127.0.0.1",
            f"http://127.0.0.1:{port}/control",
            "urn:schemas-upnp-org:service:WANIPConnection:1",
            "192.168.1.10",
        )
