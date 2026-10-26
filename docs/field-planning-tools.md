# Offline field planning tools

The Tools workspace includes four additional calculators. Search by **MTU**, **BDP**,
**fiber**, or **PoE**, then open the matching card. Results can be copied or saved as a
text or JSON calculation snapshot. They use operator-entered specifications and are
marked **calculated estimate**; no diagnostic capture or survey measurement is created.

| Tool | Inputs | Result and use |
| --- | --- | --- |
| MTU / TCP MSS | Link MTU, IP and TCP header bytes, outer encapsulation bytes | Effective IP MTU and TCP payload limit. Enter 20 bytes for a basic IPv4 header or 40 for a basic IPv6 header; account for options and tunnel overhead explicitly. This does not discover path MTU. |
| TCP bandwidth-delay product | Target rate in Mbit/s and round-trip time in ms | In-flight bytes and MiB needed to fill the path at those assumptions. This is not a throughput prediction. |
| Fiber optical power budget | Minimum TX power, receiver sensitivity, length, attenuation, connector and splice losses, reserve | Estimated path loss, receiver power and margin after reserve. Negative margin flags a planning shortfall. Confirm actual components, wavelength and installed link separately. |
| PoE source power budget | Total PSE supply, existing commitments, planned device demand, unallocated reserve | Source headroom after the planned device and count of further equal-demand devices that fit. This does not establish per-port class or delivered PD power through cable. |

Fiber and PoE results include labeled native schematic flows highlighting the main
power and margin values. The text snapshot contains the complete inputs, outputs and
assumptions. Both diagrams are explicitly labeled as entered specifications, not
measured equipment.
