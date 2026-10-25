# WLAN Pros capability inventory and Veilbreaker gap ledger

Research snapshot: October 25, 2026. Source: [official v1.12.0 field manual](https://toolbox.wlanpros.com/instructions.pdf), 473 PDF pages. This is a documentation inventory, not an audit of the user's installed app or a claim of feature parity.

The publisher advertises 264 tools. The manual contains **270 entry-level headings**: Test Network 8, Networking 25, Calculators 41, Quick Reference 104, Educational Resources 1, Classroom 91. Retain all 270 for review. The differences include a throughput-method explanation, a nested fiber-connector section, extra Test Network entries and extra tone-generator entries; do not equate heading count with independently executable tools.

Only factual feature titles, categories and page locations are catalogued. Implement capabilities independently with original UI, explanations, examples and diagrams. Publisher handouts, artwork and branded checklists are reference subjects, not assets to bundle. Broad classroom and trade topics remain in this ledger; their release scheduling is not yet approved.

**Status legend:** Related implementation means a Veilbreaker component addresses part of the subject, not that the entire tool exists. Not mapped means no implementation was established in this bounded review, not proof of absence. Reference/lesson candidates need original content, authoritative sources and review. This inventory does not assess every input, algorithm or platform restriction in the manual.

Related source filenames are under `src/veilbreaker/`; consult the roadmap and field guides for qualification. Start implementation with the proposed [1.0 scope and delivery sequence](V1_FIELD_PLATFORM.md), then verify individual requirements against the relevant manual pages and primary standards.



## Test Network (5 tools) / General

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-001 | Test My Connection | [3](https://toolbox.wlanpros.com/instructions.pdf#page=3) | Related implementation; parity unverified | core.py; acquisition.py |
| WP-002 | Analyze Results | [5](https://toolbox.wlanpros.com/instructions.pdf#page=5) | Related implementation; parity unverified | core.py; followup.py |
| WP-003 | Network Quality | [6](https://toolbox.wlanpros.com/instructions.pdf#page=6) | Related implementation; parity unverified | core.py |
| WP-004 | Wi-Fi Information | [8](https://toolbox.wlanpros.com/instructions.pdf#page=8) | Related implementation; parity unverified | core.py |
| WP-005 | BSS Load | [9](https://toolbox.wlanpros.com/instructions.pdf#page=9) | Not mapped; review required | — |
| WP-006 | Cellular Information | [10](https://toolbox.wlanpros.com/instructions.pdf#page=10) | Related implementation; parity unverified | cellular_report.py; cell_visibility.py |
| WP-007 | Roaming Log | [11](https://toolbox.wlanpros.com/instructions.pdf#page=11) | Not mapped; review required | — |
| WP-008 | How the Toolbox Measures Throughput | [12](https://toolbox.wlanpros.com/instructions.pdf#page=12) | Not mapped; review required | — |

## Networking Tools (25 tools) / This Device (5)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-009 | Current Location | [15](https://toolbox.wlanpros.com/instructions.pdf#page=15) | Related implementation; parity unverified | location_report.py; map_data.py |
| WP-010 | Device Info | [16](https://toolbox.wlanpros.com/instructions.pdf#page=16) | Related implementation; parity unverified | core.py |
| WP-011 | Interface Information | [17](https://toolbox.wlanpros.com/instructions.pdf#page=17) | Related implementation; parity unverified | core.py |
| WP-012 | Join a Network | [18](https://toolbox.wlanpros.com/instructions.pdf#page=18) | Not mapped; review required | — |
| WP-013 | Link Info | [19](https://toolbox.wlanpros.com/instructions.pdf#page=19) | Related implementation; parity unverified | core.py |

## Networking Tools (25 tools) / Reachability & Path (5)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-014 | Ping (ICMP) | [21](https://toolbox.wlanpros.com/instructions.pdf#page=21) | Related implementation; parity unverified | core.py |
| WP-015 | Ping (TCP) | [21](https://toolbox.wlanpros.com/instructions.pdf#page=21) | Not mapped; review required | — |
| WP-016 | Ping Plotter | [22](https://toolbox.wlanpros.com/instructions.pdf#page=22) | Not mapped; review required | — |
| WP-017 | Traceroute (Mobile) | [23](https://toolbox.wlanpros.com/instructions.pdf#page=23) | Not mapped; review required | — |
| WP-018 | Traceroute (System) | [24](https://toolbox.wlanpros.com/instructions.pdf#page=24) | Related implementation; parity unverified | core.py |

## Networking Tools (25 tools) / Discovery & Scanning (5)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-019 | Lookup (ARP/NDP) | [25](https://toolbox.wlanpros.com/instructions.pdf#page=25) | Not mapped; review required | — |
| WP-020 | Nearby AP Scan | [26](https://toolbox.wlanpros.com/instructions.pdf#page=26) | Not mapped; review required | — |
| WP-021 | Network Discovery | [27](https://toolbox.wlanpros.com/instructions.pdf#page=27) | Not mapped; review required | — |
| WP-022 | Ping Sweep | [28](https://toolbox.wlanpros.com/instructions.pdf#page=28) | Not mapped; review required | — |
| WP-023 | Port Scan | [29](https://toolbox.wlanpros.com/instructions.pdf#page=29) | Not mapped; review required | — |

## Networking Tools (25 tools) / Names & Ownership (5)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-024 | IP Geolocation | [30](https://toolbox.wlanpros.com/instructions.pdf#page=30) | Not mapped; review required | — |
| WP-025 | Lookup (BGP/ASN) | [31](https://toolbox.wlanpros.com/instructions.pdf#page=31) | Not mapped; review required | — |
| WP-026 | Lookup (DNS) | [31](https://toolbox.wlanpros.com/instructions.pdf#page=31) | Related implementation; parity unverified | core.py |
| WP-027 | MAC Vendor OUI Lookup | [32](https://toolbox.wlanpros.com/instructions.pdf#page=32) | Not mapped; review required | — |
| WP-028 | WHOIS | [33](https://toolbox.wlanpros.com/instructions.pdf#page=33) | Not mapped; review required | — |

## Networking Tools (25 tools) / Services & Protocols (5)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-029 | Inspector (HTTP Header) | [34](https://toolbox.wlanpros.com/instructions.pdf#page=34) | Not mapped; review required | — |
| WP-030 | Inspector (SSL/TLS) | [35](https://toolbox.wlanpros.com/instructions.pdf#page=35) | Not mapped; review required | — |
| WP-031 | Packet Sender | [36](https://toolbox.wlanpros.com/instructions.pdf#page=36) | Not mapped; review required | — |
| WP-032 | Time Server (NTP) | [36](https://toolbox.wlanpros.com/instructions.pdf#page=36) | Not mapped; review required | — |
| WP-033 | Wake-on-LAN | [37](https://toolbox.wlanpros.com/instructions.pdf#page=37) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / RF & Propagation (9)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-034 | Cable Loss | [38](https://toolbox.wlanpros.com/instructions.pdf#page=38) | Not mapped; review required | — |
| WP-035 | Earth Curvature | [40](https://toolbox.wlanpros.com/instructions.pdf#page=40) | Related implementation; parity unverified | terrain_profile.py |
| WP-036 | Free Space Path Loss | [41](https://toolbox.wlanpros.com/instructions.pdf#page=41) | Not mapped; review required | — |
| WP-037 | Fresnel Zone | [41](https://toolbox.wlanpros.com/instructions.pdf#page=41) | Related implementation; parity unverified | terrain_profile.py |
| WP-038 | ITU Rain Fade | [43](https://toolbox.wlanpros.com/instructions.pdf#page=43) | Not mapped; review required | — |
| WP-039 | Link Budget | [44](https://toolbox.wlanpros.com/instructions.pdf#page=44) | Not mapped; review required | — |
| WP-040 | Noise Floor | [45](https://toolbox.wlanpros.com/instructions.pdf#page=45) | Not mapped; review required | — |
| WP-041 | PtP Link Check | [46](https://toolbox.wlanpros.com/instructions.pdf#page=46) | Related implementation; parity unverified | terrain_profile.py; path_assessment_ui.py |
| WP-042 | RF Attenuation | [48](https://toolbox.wlanpros.com/instructions.pdf#page=48) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / Antenna & Coverage (4)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-043 | Antenna Downtilt | [49](https://toolbox.wlanpros.com/instructions.pdf#page=49) | Not mapped; review required | — |
| WP-044 | Downtilt Coverage | [50](https://toolbox.wlanpros.com/instructions.pdf#page=50) | Not mapped; review required | — |
| WP-045 | EIRP Calculator | [51](https://toolbox.wlanpros.com/instructions.pdf#page=51) | Not mapped; review required | — |
| WP-046 | Wavelength | [52](https://toolbox.wlanpros.com/instructions.pdf#page=52) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / Capacity & Power (5)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-047 | Capacity Planner | [53](https://toolbox.wlanpros.com/instructions.pdf#page=53) | Not mapped; review required | — |
| WP-048 | PoE Budget | [54](https://toolbox.wlanpros.com/instructions.pdf#page=54) | Not mapped; review required | — |
| WP-049 | Shannon Capacity | [55](https://toolbox.wlanpros.com/instructions.pdf#page=55) | Not mapped; review required | — |
| WP-050 | SSID Airtime | [56](https://toolbox.wlanpros.com/instructions.pdf#page=56) | Not mapped; review required | — |
| WP-051 | Throughput Calculator | [58](https://toolbox.wlanpros.com/instructions.pdf#page=58) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / IP & Addressing (4)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-052 | IP Subnet Calculator (IPv4) | [60](https://toolbox.wlanpros.com/instructions.pdf#page=60) | Not mapped; review required | — |
| WP-053 | IP Subnet Calculator (IPv6) | [62](https://toolbox.wlanpros.com/instructions.pdf#page=62) | Not mapped; review required | — |
| WP-054 | MTU & MSS Calculator | [64](https://toolbox.wlanpros.com/instructions.pdf#page=64) | Not mapped; review required | — |
| WP-055 | Subnet Planner (VLSM) | [66](https://toolbox.wlanpros.com/instructions.pdf#page=66) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / Coordinates & GPS (4)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-056 | Distance and Bearing | [68](https://toolbox.wlanpros.com/instructions.pdf#page=68) | Related implementation; parity unverified | cell_context.py |
| WP-057 | Final Point | [69](https://toolbox.wlanpros.com/instructions.pdf#page=69) | Not mapped; review required | — |
| WP-058 | Lat / Long Conversion | [70](https://toolbox.wlanpros.com/instructions.pdf#page=70) | Not mapped; review required | — |
| WP-059 | Midpoint | [71](https://toolbox.wlanpros.com/instructions.pdf#page=71) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / Conversions (7)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-060 | Architectural Scale | [72](https://toolbox.wlanpros.com/instructions.pdf#page=72) | Not mapped; review required | — |
| WP-061 | Channel / Frequency | [73](https://toolbox.wlanpros.com/instructions.pdf#page=73) | Related implementation; parity unverified | cell_visibility.py |
| WP-062 | dBm / Watt Converter | [74](https://toolbox.wlanpros.com/instructions.pdf#page=74) | Not mapped; review required | — |
| WP-063 | Hex / ASCII | [75](https://toolbox.wlanpros.com/instructions.pdf#page=75) | Not mapped; review required | — |
| WP-064 | Metric Conversion | [77](https://toolbox.wlanpros.com/instructions.pdf#page=77) | Not mapped; review required | — |
| WP-065 | Transfer Time | [77](https://toolbox.wlanpros.com/instructions.pdf#page=77) | Not mapped; review required | — |
| WP-066 | Unit Converter | [79](https://toolbox.wlanpros.com/instructions.pdf#page=79) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / Ham Radio (2)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-067 | Antenna Length | [80](https://toolbox.wlanpros.com/instructions.pdf#page=80) | Not mapped; review required | — |
| WP-068 | Maidenhead Grid Square | [81](https://toolbox.wlanpros.com/instructions.pdf#page=81) | Not mapped; review required | — |

## Calculators & Tools (39 tools) / Utilities & Generators (4)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-069 | DTMF Generator | [82](https://toolbox.wlanpros.com/instructions.pdf#page=82) | Not mapped; review required | — |
| WP-070 | Blue Box (MF) | [83](https://toolbox.wlanpros.com/instructions.pdf#page=83) | Not mapped; review required | — |
| WP-071 | Red Box (US coin tones) | [84](https://toolbox.wlanpros.com/instructions.pdf#page=84) | Not mapped; review required | — |
| WP-072 | Hear the Frequency | [85](https://toolbox.wlanpros.com/instructions.pdf#page=85) | Not mapped; review required | — |
| WP-073 | Morse Code | [86](https://toolbox.wlanpros.com/instructions.pdf#page=86) | Not mapped; review required | — |
| WP-074 | QR Code Generator | [87](https://toolbox.wlanpros.com/instructions.pdf#page=87) | Not mapped; review required | — |

## Quick Reference (103 tools) / Radio & Spectrum (10)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-075 | Adjacent Radio Systems | [89](https://toolbox.wlanpros.com/instructions.pdf#page=89) | New original reference/lesson candidate | — |
| WP-076 | Channel Map | [90](https://toolbox.wlanpros.com/instructions.pdf#page=90) | New original reference/lesson candidate | — |
| WP-077 | dB Reference | [91](https://toolbox.wlanpros.com/instructions.pdf#page=91) | New original reference/lesson candidate | — |
| WP-078 | How Strong Is Wi-Fi, Really? | [92](https://toolbox.wlanpros.com/instructions.pdf#page=92) | New original reference/lesson candidate | — |
| WP-079 | Non-Wi-Fi Wireless Channels | [93](https://toolbox.wlanpros.com/instructions.pdf#page=93) | New original reference/lesson candidate | — |
| WP-080 | Regulatory Domains | [94](https://toolbox.wlanpros.com/instructions.pdf#page=94) | New original reference/lesson candidate | — |
| WP-081 | RF Bands | [95](https://toolbox.wlanpros.com/instructions.pdf#page=95) | Related implementation; parity unverified | bandplan.py |
| WP-082 | Signal Thresholds | [96](https://toolbox.wlanpros.com/instructions.pdf#page=96) | New original reference/lesson candidate | — |
| WP-083 | Spectrum Reference | [97](https://toolbox.wlanpros.com/instructions.pdf#page=97) | Related implementation; parity unverified | bandplan.py |
| WP-084 | Wi-Fi HaLow | [98](https://toolbox.wlanpros.com/instructions.pdf#page=98) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Wi-Fi Standards & Terminology (6)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-085 | 802.11 Feature Matrix | [99](https://toolbox.wlanpros.com/instructions.pdf#page=99) | New original reference/lesson candidate | — |
| WP-086 | 802.11 Standards | [100](https://toolbox.wlanpros.com/instructions.pdf#page=100) | New original reference/lesson candidate | — |
| WP-087 | MCS Index | [100](https://toolbox.wlanpros.com/instructions.pdf#page=100) | New original reference/lesson candidate | — |
| WP-088 | Modulation | [101](https://toolbox.wlanpros.com/instructions.pdf#page=101) | New original reference/lesson candidate | — |
| WP-089 | Wireless Glossary | [102](https://toolbox.wlanpros.com/instructions.pdf#page=102) | New original reference/lesson candidate | — |
| WP-090 | Wi-Fi Standards Bodies | [103](https://toolbox.wlanpros.com/instructions.pdf#page=103) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Security & Auth (5)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-091 | 802.1X / EAP Types | [104](https://toolbox.wlanpros.com/instructions.pdf#page=104) | New original reference/lesson candidate | — |
| WP-092 | Diffie-Hellman | [104](https://toolbox.wlanpros.com/instructions.pdf#page=104) | New original reference/lesson candidate | — |
| WP-093 | FreeRADIUS on WLAN Pi | [105](https://toolbox.wlanpros.com/instructions.pdf#page=105) | New original reference/lesson candidate | — |
| WP-094 | Wi-Fi Authentication Glossary | [106](https://toolbox.wlanpros.com/instructions.pdf#page=106) | New original reference/lesson candidate | — |
| WP-095 | WPA Security | [107](https://toolbox.wlanpros.com/instructions.pdf#page=107) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Clients & Field Wi-Fi (6)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-096 | Apple Wi-Fi Support Tips | [108](https://toolbox.wlanpros.com/instructions.pdf#page=108) | New original reference/lesson candidate | — |
| WP-097 | How Your Devices Access the Internet | [108](https://toolbox.wlanpros.com/instructions.pdf#page=108) | New original reference/lesson candidate | — |
| WP-098 | macOS Menu-Bar Wi-Fi | [110](https://toolbox.wlanpros.com/instructions.pdf#page=110) | New original reference/lesson candidate | — |
| WP-099 | Roaming Parameters | [111](https://toolbox.wlanpros.com/instructions.pdf#page=111) | New original reference/lesson candidate | — |
| WP-100 | Throughput Testing: Where You Test | [111](https://toolbox.wlanpros.com/instructions.pdf#page=111) | New original reference/lesson candidate | — |
| WP-101 | Wi-Fi Tools Comparison | [113](https://toolbox.wlanpros.com/instructions.pdf#page=113) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Capture & Troubleshooting (9)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-102 | 802.11 Reason Codes | [114](https://toolbox.wlanpros.com/instructions.pdf#page=114) | New original reference/lesson candidate | — |
| WP-103 | Association Sequence | [115](https://toolbox.wlanpros.com/instructions.pdf#page=115) | New original reference/lesson candidate | — |
| WP-104 | Find the Switch and Port (LLDP/CDP) | [116](https://toolbox.wlanpros.com/instructions.pdf#page=116) | New original reference/lesson candidate | — |
| WP-105 | How to NOT Have a Wireless Problem | [118](https://toolbox.wlanpros.com/instructions.pdf#page=118) | New original reference/lesson candidate | — |
| WP-106 | Linux / WLAN Commands | [118](https://toolbox.wlanpros.com/instructions.pdf#page=118) | New original reference/lesson candidate | — |
| WP-107 | Network CLI Commands | [119](https://toolbox.wlanpros.com/instructions.pdf#page=119) | New original reference/lesson candidate | — |
| WP-108 | VoIP over Wi-Fi Filters | [121](https://toolbox.wlanpros.com/instructions.pdf#page=121) | New original reference/lesson candidate | — |
| WP-109 | Wi-Fi Client Testing Checklist | [123](https://toolbox.wlanpros.com/instructions.pdf#page=123) | New original reference/lesson candidate | — |
| WP-110 | Wireshark 802.11 Filters | [124](https://toolbox.wlanpros.com/instructions.pdf#page=124) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Networking & Protocols (14)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-111 | DHCP Options | [126](https://toolbox.wlanpros.com/instructions.pdf#page=126) | New original reference/lesson candidate | — |
| WP-112 | DNS Record Types | [126](https://toolbox.wlanpros.com/instructions.pdf#page=126) | New original reference/lesson candidate | — |
| WP-113 | DSCP / QoS Markings | [127](https://toolbox.wlanpros.com/instructions.pdf#page=127) | New original reference/lesson candidate | — |
| WP-114 | HTTP Methods & Headers | [128](https://toolbox.wlanpros.com/instructions.pdf#page=128) | New original reference/lesson candidate | — |
| WP-115 | HTTP Status Codes | [128](https://toolbox.wlanpros.com/instructions.pdf#page=128) | New original reference/lesson candidate | — |
| WP-116 | IP Address Reference | [129](https://toolbox.wlanpros.com/instructions.pdf#page=129) | New original reference/lesson candidate | — |
| WP-117 | Naming & Addressing Conventions | [130](https://toolbox.wlanpros.com/instructions.pdf#page=130) | New original reference/lesson candidate | — |
| WP-118 | OSI Model | [130](https://toolbox.wlanpros.com/instructions.pdf#page=130) | New original reference/lesson candidate | — |
| WP-119 | Packet Decode | [131](https://toolbox.wlanpros.com/instructions.pdf#page=131) | New original reference/lesson candidate | — |
| WP-120 | PLMN ID Reference | [133](https://toolbox.wlanpros.com/instructions.pdf#page=133) | Related implementation; parity unverified | cellular_report.py |
| WP-121 | Speed Test Services | [133](https://toolbox.wlanpros.com/instructions.pdf#page=133) | New original reference/lesson candidate | — |
| WP-122 | Subnetting / CIDR Table | [134](https://toolbox.wlanpros.com/instructions.pdf#page=134) | New original reference/lesson candidate | — |
| WP-123 | Top-Level Domains | [135](https://toolbox.wlanpros.com/instructions.pdf#page=135) | New original reference/lesson candidate | — |
| WP-124 | Well-Known Ports | [136](https://toolbox.wlanpros.com/instructions.pdf#page=136) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Cabling, Connectors & Hardware (12)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-125 | Antenna Connectors | [136](https://toolbox.wlanpros.com/instructions.pdf#page=136) | New original reference/lesson candidate | — |
| WP-126 | Bend Radius & Pull Tension | [138](https://toolbox.wlanpros.com/instructions.pdf#page=138) | New original reference/lesson candidate | — |
| WP-127 | Coax Cable | [138](https://toolbox.wlanpros.com/instructions.pdf#page=138) | New original reference/lesson candidate | — |
| WP-128 | Ethernet Cable & Connector | [139](https://toolbox.wlanpros.com/instructions.pdf#page=139) | New original reference/lesson candidate | — |
| WP-129 | Fiber Optic | [140](https://toolbox.wlanpros.com/instructions.pdf#page=140) | New original reference/lesson candidate | — |
| WP-130 | Fiber Connectors & Polish (a section within the Fiber Optic tool) | [141](https://toolbox.wlanpros.com/instructions.pdf#page=141) | New original reference/lesson candidate | — |
| WP-131 | LED Decoder | [143](https://toolbox.wlanpros.com/instructions.pdf#page=143) | New original reference/lesson candidate | — |
| WP-132 | Optical Transceivers | [144](https://toolbox.wlanpros.com/instructions.pdf#page=144) | New original reference/lesson candidate | — |
| WP-133 | Rack Units | [145](https://toolbox.wlanpros.com/instructions.pdf#page=145) | New original reference/lesson candidate | — |
| WP-134 | RJ Connectors | [146](https://toolbox.wlanpros.com/instructions.pdf#page=146) | New original reference/lesson candidate | — |
| WP-135 | Screw Drives | [147](https://toolbox.wlanpros.com/instructions.pdf#page=147) | New original reference/lesson candidate | — |
| WP-136 | SD & microSD Cards | [147](https://toolbox.wlanpros.com/instructions.pdf#page=147) | New original reference/lesson candidate | — |
| WP-137 | Vendor Model Decode | [149](https://toolbox.wlanpros.com/instructions.pdf#page=149) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Power & Cooling (7)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-138 | Batteries | [150](https://toolbox.wlanpros.com/instructions.pdf#page=150) | New original reference/lesson candidate | — |
| WP-139 | Cooling & Thermal | [150](https://toolbox.wlanpros.com/instructions.pdf#page=150) | New original reference/lesson candidate | — |
| WP-140 | IEC Power Connectors | [151](https://toolbox.wlanpros.com/instructions.pdf#page=151) | New original reference/lesson candidate | — |
| WP-141 | NEMA Connectors | [152](https://toolbox.wlanpros.com/instructions.pdf#page=152) | New original reference/lesson candidate | — |
| WP-142 | Ohm's Law & Power Wheel | [153](https://toolbox.wlanpros.com/instructions.pdf#page=153) | New original reference/lesson candidate | — |
| WP-143 | PoE Reference | [154](https://toolbox.wlanpros.com/instructions.pdf#page=154) | New original reference/lesson candidate | — |
| WP-144 | Power Phasing | [155](https://toolbox.wlanpros.com/instructions.pdf#page=155) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Codes, Safety & Compliance (8)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-145 | Cloud Tool Trust | [156](https://toolbox.wlanpros.com/instructions.pdf#page=156) | New original reference/lesson candidate | — |
| WP-146 | Credentials & Licenses | [157](https://toolbox.wlanpros.com/instructions.pdf#page=157) | New original reference/lesson candidate | — |
| WP-147 | Enclosure Ratings | [158](https://toolbox.wlanpros.com/instructions.pdf#page=158) | New original reference/lesson candidate | — |
| WP-148 | Hazardous Locations | [159](https://toolbox.wlanpros.com/instructions.pdf#page=159) | New original reference/lesson candidate | — |
| WP-149 | NEC Gotchas | [160](https://toolbox.wlanpros.com/instructions.pdf#page=160) | New original reference/lesson candidate | — |
| WP-150 | Network in Scope | [161](https://toolbox.wlanpros.com/instructions.pdf#page=161) | New original reference/lesson candidate | — |
| WP-151 | Safety Basics | [162](https://toolbox.wlanpros.com/instructions.pdf#page=162) | New original reference/lesson candidate | — |
| WP-152 | Site Access | [163](https://toolbox.wlanpros.com/instructions.pdf#page=163) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Buildings & Verticals (8)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-153 | AEC Process & Glossary | [163](https://toolbox.wlanpros.com/instructions.pdf#page=163) | New original reference/lesson candidate | — |
| WP-154 | CAD & BIM Formats | [164](https://toolbox.wlanpros.com/instructions.pdf#page=164) | New original reference/lesson candidate | — |
| WP-155 | Data Centers & Wi-Fi | [165](https://toolbox.wlanpros.com/instructions.pdf#page=165) | New original reference/lesson candidate | — |
| WP-156 | Healthcare Wi-Fi | [166](https://toolbox.wlanpros.com/instructions.pdf#page=166) | New original reference/lesson candidate | — |
| WP-157 | Plan-Set Literacy | [167](https://toolbox.wlanpros.com/instructions.pdf#page=167) | New original reference/lesson candidate | — |
| WP-158 | Structured Cabling | [168](https://toolbox.wlanpros.com/instructions.pdf#page=168) | New original reference/lesson candidate | — |
| WP-159 | Telecom Spaces | [169](https://toolbox.wlanpros.com/instructions.pdf#page=169) | New original reference/lesson candidate | — |
| WP-160 | Verticals Index | [170](https://toolbox.wlanpros.com/instructions.pdf#page=170) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Ham Radio (6)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-161 | Band Names & Wavelengths | [171](https://toolbox.wlanpros.com/instructions.pdf#page=171) | New original reference/lesson candidate | — |
| WP-162 | General License Frequency Chart | [172](https://toolbox.wlanpros.com/instructions.pdf#page=172) | New original reference/lesson candidate | — |
| WP-163 | Ham Radio General Exam Study Notes | [172](https://toolbox.wlanpros.com/instructions.pdf#page=172) | New original reference/lesson candidate | — |
| WP-164 | Part 15 vs Part 97 | [173](https://toolbox.wlanpros.com/instructions.pdf#page=173) | New original reference/lesson candidate | — |
| WP-165 | Spectrum Band Designations | [174](https://toolbox.wlanpros.com/instructions.pdf#page=174) | New original reference/lesson candidate | — |
| WP-166 | US Amateur Band Plan | [174](https://toolbox.wlanpros.com/instructions.pdf#page=174) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Encoding & Formats (8)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-167 | ASCII / Hex / Binary | [176](https://toolbox.wlanpros.com/instructions.pdf#page=176) | New original reference/lesson candidate | — |
| WP-168 | Data Units | [177](https://toolbox.wlanpros.com/instructions.pdf#page=177) | New original reference/lesson candidate | — |
| WP-169 | Hash Lengths | [177](https://toolbox.wlanpros.com/instructions.pdf#page=177) | New original reference/lesson candidate | — |
| WP-170 | Keyboard Shortcuts | [178](https://toolbox.wlanpros.com/instructions.pdf#page=178) | New original reference/lesson candidate | — |
| WP-171 | Markdown Cheatsheet | [178](https://toolbox.wlanpros.com/instructions.pdf#page=178) | New original reference/lesson candidate | — |
| WP-172 | Phonetic Alphabet | [179](https://toolbox.wlanpros.com/instructions.pdf#page=179) | New original reference/lesson candidate | — |
| WP-173 | Regex Cheatsheet | [180](https://toolbox.wlanpros.com/instructions.pdf#page=180) | New original reference/lesson candidate | — |
| WP-174 | Top 30 Emoji | [180](https://toolbox.wlanpros.com/instructions.pdf#page=180) | New original reference/lesson candidate | — |

## Quick Reference (103 tools) / Travel & International (4)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-175 | Date / Time Standards | [181](https://toolbox.wlanpros.com/instructions.pdf#page=181) | New original reference/lesson candidate | — |
| WP-176 | Emergency Phrases | [182](https://toolbox.wlanpros.com/instructions.pdf#page=182) | New original reference/lesson candidate | — |
| WP-177 | International Power Plugs | [183](https://toolbox.wlanpros.com/instructions.pdf#page=183) | New original reference/lesson candidate | — |
| WP-178 | Time Zones | [184](https://toolbox.wlanpros.com/instructions.pdf#page=184) | New original reference/lesson candidate | — |

## Educational Resources (1 tool) / General

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-179 | Ham Radio Study Resources | [185](https://toolbox.wlanpros.com/instructions.pdf#page=185) | New original reference/lesson candidate | — |

## Wireless Classroom (91 tools) / Guided Lessons (30)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-180 | Antenna Fundamentals | [186](https://toolbox.wlanpros.com/instructions.pdf#page=186) | New original reference/lesson candidate | — |
| WP-181 | Spectrum Analysis | [187](https://toolbox.wlanpros.com/instructions.pdf#page=187) | New original reference/lesson candidate | — |
| WP-182 | Find My, Explained | [188](https://toolbox.wlanpros.com/instructions.pdf#page=188) | New original reference/lesson candidate | — |
| WP-183 | Home Internet, Explained | [190](https://toolbox.wlanpros.com/instructions.pdf#page=190) | New original reference/lesson candidate | — |
| WP-184 | Wi-Fi Calling, Explained | [191](https://toolbox.wlanpros.com/instructions.pdf#page=191) | New original reference/lesson candidate | — |
| WP-185 | Starlink, Explained | [192](https://toolbox.wlanpros.com/instructions.pdf#page=192) | New original reference/lesson candidate | — |
| WP-186 | Tap, Touch and Near, Explained | [193](https://toolbox.wlanpros.com/instructions.pdf#page=193) | New original reference/lesson candidate | — |
| WP-187 | Satellite Texting, Explained | [194](https://toolbox.wlanpros.com/instructions.pdf#page=194) | New original reference/lesson candidate | — |
| WP-188 | Wi-Fi on Planes, Explained | [195](https://toolbox.wlanpros.com/instructions.pdf#page=195) | New original reference/lesson candidate | — |
| WP-189 | Wi-Fi and Your Health, Explained | [196](https://toolbox.wlanpros.com/instructions.pdf#page=196) | New original reference/lesson candidate | — |
| WP-190 | Travel Routers, Explained | [197](https://toolbox.wlanpros.com/instructions.pdf#page=197) | New original reference/lesson candidate | — |
| WP-191 | Mobile Hotspots, Explained | [198](https://toolbox.wlanpros.com/instructions.pdf#page=198) | New original reference/lesson candidate | — |
| WP-192 | Captive Portals, Explained | [199](https://toolbox.wlanpros.com/instructions.pdf#page=199) | New original reference/lesson candidate | — |
| WP-193 | Bluetooth, Explained | [200](https://toolbox.wlanpros.com/instructions.pdf#page=200) | New original reference/lesson candidate | — |
| WP-194 | Weak Cell Signal at Home, Explained | [201](https://toolbox.wlanpros.com/instructions.pdf#page=201) | New original reference/lesson candidate | — |
| WP-195 | How GPS Works, Explained | [202](https://toolbox.wlanpros.com/instructions.pdf#page=202) | New original reference/lesson candidate | — |
| WP-196 | How Your Phone Knows Where It Is, Explained | [203](https://toolbox.wlanpros.com/instructions.pdf#page=203) | New original reference/lesson candidate | — |
| WP-197 | Analog vs Digital, Explained | [205](https://toolbox.wlanpros.com/instructions.pdf#page=205) | New original reference/lesson candidate | — |
| WP-198 | Scales and Ratios, Explained | [206](https://toolbox.wlanpros.com/instructions.pdf#page=206) | New original reference/lesson candidate | — |
| WP-199 | Phone Data Abroad, Explained | [207](https://toolbox.wlanpros.com/instructions.pdf#page=207) | New original reference/lesson candidate | — |
| WP-200 | Smart Home Radios, Explained | [208](https://toolbox.wlanpros.com/instructions.pdf#page=208) | New original reference/lesson candidate | — |
| WP-201 | Cameras, Doorbells and Baby Monitors, Explained | [209](https://toolbox.wlanpros.com/instructions.pdf#page=209) | New original reference/lesson candidate | — |
| WP-202 | How Your Devices Access the Internet, Explained | [211](https://toolbox.wlanpros.com/instructions.pdf#page=211) | New original reference/lesson candidate | — |
| WP-203 | Mesh, Extenders and Wired Access Points, Explained | [212](https://toolbox.wlanpros.com/instructions.pdf#page=212) | New original reference/lesson candidate | — |
| WP-204 | Is Your Router Too Old? | [213](https://toolbox.wlanpros.com/instructions.pdf#page=213) | New original reference/lesson candidate | — |
| WP-205 | Why the TV and the Printer Vanish on Guest Wi-Fi | [214](https://toolbox.wlanpros.com/instructions.pdf#page=214) | New original reference/lesson candidate | — |
| WP-206 | One Talker per Channel | [215](https://toolbox.wlanpros.com/instructions.pdf#page=215) | New original reference/lesson candidate | — |
| WP-207 | Public Wi-Fi | [219](https://toolbox.wlanpros.com/instructions.pdf#page=219) | New original reference/lesson candidate | — |
| WP-208 | Wi-Fi Privacy Myths | [220](https://toolbox.wlanpros.com/instructions.pdf#page=220) | New original reference/lesson candidate | — |
| WP-209 | Connected, No Internet: Captive Portals | [221](https://toolbox.wlanpros.com/instructions.pdf#page=221) | New original reference/lesson candidate | — |

## Wireless Classroom (91 tools) / RF and Propagation (13)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-210 | Decibels in Your Head: the Rules of 3 and 10 | [222](https://toolbox.wlanpros.com/instructions.pdf#page=222) | New original reference/lesson candidate | — |
| WP-211 | FSPL Simulator | [225](https://toolbox.wlanpros.com/instructions.pdf#page=225) | New original reference/lesson candidate | — |
| WP-212 | Wi-Fi Through a Wall | [230](https://toolbox.wlanpros.com/instructions.pdf#page=230) | New original reference/lesson candidate | — |
| WP-213 | How to Measure Wall Attenuation | [234](https://toolbox.wlanpros.com/instructions.pdf#page=234) | New original reference/lesson candidate | — |
| WP-214 | Multipath Simulator | [240](https://toolbox.wlanpros.com/instructions.pdf#page=240) | New original reference/lesson candidate | — |
| WP-215 | Why Two Devices Disagree | [245](https://toolbox.wlanpros.com/instructions.pdf#page=245) | New original reference/lesson candidate | — |
| WP-216 | Room Propagation | [250](https://toolbox.wlanpros.com/instructions.pdf#page=250) | New original reference/lesson candidate | — |
| WP-217 | Antenna Pattern | [254](https://toolbox.wlanpros.com/instructions.pdf#page=254) | New original reference/lesson candidate | — |
| WP-218 | Polarization | [261](https://toolbox.wlanpros.com/instructions.pdf#page=261) | New original reference/lesson candidate | — |
| WP-219 | Rate vs Range | [265](https://toolbox.wlanpros.com/instructions.pdf#page=265) | New original reference/lesson candidate | — |
| WP-220 | 6 GHz Power and PSD | [271](https://toolbox.wlanpros.com/instructions.pdf#page=271) | New original reference/lesson candidate | — |
| WP-221 | Uplink vs Downlink | [275](https://toolbox.wlanpros.com/instructions.pdf#page=275) | New original reference/lesson candidate | — |
| WP-222 | Body Loss | [279](https://toolbox.wlanpros.com/instructions.pdf#page=279) | New original reference/lesson candidate | — |

## Wireless Classroom (91 tools) / Signals and PHY (7)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-223 | Modulation Simulator | [284](https://toolbox.wlanpros.com/instructions.pdf#page=284) | New original reference/lesson candidate | — |
| WP-224 | Fourier and FFT | [288](https://toolbox.wlanpros.com/instructions.pdf#page=288) | New original reference/lesson candidate | — |
| WP-225 | OFDMA Resource Units | [296](https://toolbox.wlanpros.com/instructions.pdf#page=296) | New original reference/lesson candidate | — |
| WP-226 | MIMO and Beamforming | [300](https://toolbox.wlanpros.com/instructions.pdf#page=300) | New original reference/lesson candidate | — |
| WP-227 | PHY Preamble Reference | [304](https://toolbox.wlanpros.com/instructions.pdf#page=304) | New original reference/lesson candidate | — |
| WP-228 | A Frame's Journey | [308](https://toolbox.wlanpros.com/instructions.pdf#page=308) | New original reference/lesson candidate | — |
| WP-229 | The Number on the Box vs the Number in Your Hand | [313](https://toolbox.wlanpros.com/instructions.pdf#page=313) | New original reference/lesson candidate | — |

## Wireless Classroom (91 tools) / Airtime and Access (13)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-230 | Medium Access Simulator | [317](https://toolbox.wlanpros.com/instructions.pdf#page=317) | New original reference/lesson candidate | — |
| WP-231 | Voice Priority, End to End | [321](https://toolbox.wlanpros.com/instructions.pdf#page=321) | New original reference/lesson candidate | — |
| WP-232 | Airtime Anatomy | [326](https://toolbox.wlanpros.com/instructions.pdf#page=326) | New original reference/lesson candidate | — |
| WP-233 | Airtime Fairness | [333](https://toolbox.wlanpros.com/instructions.pdf#page=333) | New original reference/lesson candidate | — |
| WP-234 | OFDMA vs MU-MIMO | [336](https://toolbox.wlanpros.com/instructions.pdf#page=336) | New original reference/lesson candidate | — |
| WP-235 | Rate Adaptation | [340](https://toolbox.wlanpros.com/instructions.pdf#page=340) | New original reference/lesson candidate | — |
| WP-236 | What an Interferer Costs (and how a NIC hears the air) | [344](https://toolbox.wlanpros.com/instructions.pdf#page=344) | New original reference/lesson candidate | — |
| WP-237 | Spatial Reuse | [349](https://toolbox.wlanpros.com/instructions.pdf#page=349) | New original reference/lesson candidate | — |
| WP-238 | Power Save | [353](https://toolbox.wlanpros.com/instructions.pdf#page=353) | New original reference/lesson candidate | — |
| WP-239 | Multicast at the Basic Rate | [358](https://toolbox.wlanpros.com/instructions.pdf#page=358) | New original reference/lesson candidate | — |
| WP-240 | Channel Utilization Meter | [362](https://toolbox.wlanpros.com/instructions.pdf#page=362) | New original reference/lesson candidate | — |
| WP-241 | Legacy Protection Cost | [369](https://toolbox.wlanpros.com/instructions.pdf#page=369) | New original reference/lesson candidate | — |
| WP-242 | Multi-Link Operation | [375](https://toolbox.wlanpros.com/instructions.pdf#page=375) | New original reference/lesson candidate | — |

## Wireless Classroom (91 tools) / Network Design and Security (17)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-243 | Channel Planner | [379](https://toolbox.wlanpros.com/instructions.pdf#page=379) | New original reference/lesson candidate | — |
| WP-244 | Adjacent Channels and AP Stacking | [385](https://toolbox.wlanpros.com/instructions.pdf#page=385) | New original reference/lesson candidate | — |
| WP-245 | Roaming Walk | [390](https://toolbox.wlanpros.com/instructions.pdf#page=390) | New original reference/lesson candidate | — |
| WP-246 | Band Steering | [395](https://toolbox.wlanpros.com/instructions.pdf#page=395) | New original reference/lesson candidate | — |
| WP-247 | Survey Walk | [401](https://toolbox.wlanpros.com/instructions.pdf#page=401) | New original reference/lesson candidate | — |
| WP-248 | Heat Map Builder | [407](https://toolbox.wlanpros.com/instructions.pdf#page=407) | New original reference/lesson candidate | — |
| WP-249 | Predict, Then Measure | [412](https://toolbox.wlanpros.com/instructions.pdf#page=412) | New original reference/lesson candidate | — |
| WP-250 | Where Am I? Signal Strength vs Round-Trip Timing | [416](https://toolbox.wlanpros.com/instructions.pdf#page=416) | New original reference/lesson candidate | — |
| WP-251 | Repeaters and Mesh Backhaul | [420](https://toolbox.wlanpros.com/instructions.pdf#page=420) | New original reference/lesson candidate | — |
| WP-252 | Why a Busy Line Lags | [424](https://toolbox.wlanpros.com/instructions.pdf#page=424) | New original reference/lesson candidate | — |
| WP-253 | DFS and Radar | [427](https://toolbox.wlanpros.com/instructions.pdf#page=427) | New original reference/lesson candidate | — |
| WP-254 | Down the Stack, Across the Air, Up the Other Side | [431](https://toolbox.wlanpros.com/instructions.pdf#page=431) | New original reference/lesson candidate | — |
| WP-255 | Conference Wi-Fi Runs Out of Addresses | [435](https://toolbox.wlanpros.com/instructions.pdf#page=435) | New original reference/lesson candidate | — |
| WP-256 | Association, Frame by Frame | [439](https://toolbox.wlanpros.com/instructions.pdf#page=439) | New original reference/lesson candidate | — |
| WP-257 | 802.1X and EAP Ladder | [450](https://toolbox.wlanpros.com/instructions.pdf#page=450) | New original reference/lesson candidate | — |
| WP-258 | PoE: Why the New AP Runs at Half Strength | [458](https://toolbox.wlanpros.com/instructions.pdf#page=458) | New original reference/lesson candidate | — |
| WP-259 | Why a Long Wi-Fi Password Matters More on WPA2 | [461](https://toolbox.wlanpros.com/instructions.pdf#page=461) | New original reference/lesson candidate | — |

## Wireless Classroom (91 tools) / Course Handouts (11)

| ID | Capability title | PDF page | Veilbreaker assessment | Related source |
| --- | --- | --- | --- | --- |
| WP-260 | 2.4 GHz Channel Allocations | [465](https://toolbox.wlanpros.com/instructions.pdf#page=465) | New original reference/lesson candidate | — |
| WP-261 | 5 GHz Channel Allocations | [466](https://toolbox.wlanpros.com/instructions.pdf#page=466) | New original reference/lesson candidate | — |
| WP-262 | 6 GHz Channel Allocations | [466](https://toolbox.wlanpros.com/instructions.pdf#page=466) | New original reference/lesson candidate | — |
| WP-263 | 6 GHz Channel Allocations with GVP | [467](https://toolbox.wlanpros.com/instructions.pdf#page=467) | New original reference/lesson candidate | — |
| WP-264 | Wireless LAN Troubleshooting Causes | [468](https://toolbox.wlanpros.com/instructions.pdf#page=468) | New original reference/lesson candidate | — |
| WP-265 | WLAN Pros Bubble Diagram | [469](https://toolbox.wlanpros.com/instructions.pdf#page=469) | New original reference/lesson candidate | — |
| WP-266 | Top 20 Wi-Fi Checklist | [470](https://toolbox.wlanpros.com/instructions.pdf#page=470) | New original reference/lesson candidate | — |
| WP-267 | Extended Wi-Fi Checklist | [470](https://toolbox.wlanpros.com/instructions.pdf#page=470) | New original reference/lesson candidate | — |
| WP-268 | Extended Checklist (Non-Advertised Items) | [471](https://toolbox.wlanpros.com/instructions.pdf#page=471) | New original reference/lesson candidate | — |
| WP-269 | Wi-Fi Connection Checklist | [472](https://toolbox.wlanpros.com/instructions.pdf#page=472) | New original reference/lesson candidate | — |
| WP-270 | Modulation and Coding Schemes (MCS Index) | [473](https://toolbox.wlanpros.com/instructions.pdf#page=473) | New original reference/lesson candidate | — |
