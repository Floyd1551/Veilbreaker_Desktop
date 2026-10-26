"""Original offline field notes; links provide optional primary-source background."""

REFERENCES = (
    ('Cellular channel numbering', '''<h2>LTE EARFCN and NR ARFCN</h2>
<p>Channel numbers label radio-frequency positions; they do not identify an operator, serving cell, tower or antenna. A phone may report a band directly. Treat a band inferred from channel range as a candidate, especially where NR bands overlap.</p>
<table border="1" cellpadding="6"><tr><th>NR-ARFCN range</th><th>Global raster frequency (MHz)</th><th>Step</th></tr>
<tr><td>0–599999</td><td>N × 0.005</td><td>5 kHz</td></tr>
<tr><td>600000–2016666</td><td>3000 + (N − 600000) × 0.015</td><td>15 kHz</td></tr>
<tr><td>2016667–3279165</td><td>24250.08 + (N − 2016667) × 0.06</td><td>60 kHz</td></tr></table>
<p>This is the NR <b>global</b> frequency raster. A band-specific channel raster, permitted bandwidth, device capabilities and current regional rules still need checking. LTE EARFCN uses a separate band-specific downlink or uplink base frequency and offset; the same numerical channel alone is insufficient for this tool to establish frequency.</p>
<p>Bundled band-candidate table version: 2026-10-22, derived from the Android Open Source Project. See the Cellular channel inspector for the actual bundled version.</p>
<p>References: <a href="https://www.etsi.org/deliver/etsi_ts/138100_138199/138104/16.09.00_60/ts_138104v160900p.pdf">ETSI TS 138 104, global NR raster</a>; <a href="https://www.etsi.org/deliver/etsi_ts/136100_136199/136101/18.06.00_60/ts_136101v180600p.pdf">ETSI TS 136 101, LTE EARFCN</a>; <a href="https://android.googlesource.com/platform/frameworks/base/+/master/telephony/java/android/telephony/AccessNetworkUtils.java">AOSP channel ranges</a>. Standards and regulatory material should be rechecked before operational decisions.</p>'''),
    ('RF power and decibels', '''<h2>RF power and decibels</h2>
<p><b>dB</b> expresses a ratio. <b>dBm</b> is power relative to one milliwatt. <b>dBi</b> is antenna gain relative to an isotropic radiator. These are different quantities: do not substitute one for another.</p>
<table border="1" cellpadding="6"><tr><th>Power change</th><th>Ratio</th></tr><tr><td>+3.01 dB</td><td>2 ×</td></tr><tr><td>+10 dB</td><td>10 ×</td></tr><tr><td>−3.01 dB</td><td>0.5 ×</td></tr><tr><td>−10 dB</td><td>0.1 ×</td></tr></table>
<p>Add antenna gain and subtract cable losses when computing EIRP. Use gain in the relevant direction. More transmitter power does not automatically improve the return path.</p>
<p><b>Try:</b> compare both directions, keep antenna orientation fixed and record feed loss before attributing a change to propagation.</p>
<p>Reference: <a href="https://www.itu.int/rec/R-REC-P.525/en">ITU-R P.525: free-space propagation</a>.</p>'''),
    ('Wireless measurements: RSSI, RSRP, RSRQ and SINR', '''<h2>What the measurements tell you</h2>
<table border="1" cellpadding="6"><tr><th>Measurement</th><th>Interpretation</th></tr>
<tr><td>RSSI</td><td>Received power indication; its bandwidth and content depend on the technology and receiver.</td></tr>
<tr><td>RSRP / SS-RSRP</td><td>Power of specified cellular reference signals. Keep LTE and NR measurement definitions distinct.</td></tr>
<tr><td>RSRQ / SS-RSRQ</td><td>Reference-signal quality relative to received power, under the relevant radio definition.</td></tr>
<tr><td>SINR</td><td>Signal relative to interference plus noise. A strong signal can still have poor SINR.</td></tr></table>
<p>No single universal threshold proves reliable service. Read signal quality together with loss, latency, throughput, bandwidth, radio technology and application requirements. Missing values mean not exposed, not zero.</p>
<p><b>Try:</b> repeat at the same position and orientation; compare signal power and quality before changing equipment.</p>
<p>Reference: <a href="https://developer.android.com/reference/android/telephony/CellSignalStrengthLte">Android LTE measurement API</a>, <a href="https://developer.android.com/reference/android/telephony/CellSignalStrengthNr">Android NR measurement API</a>.</p>'''),
    ('Propagation: Fresnel, obstacles and materials', '''<h2>Seeing the path around the signal</h2>
<p>Visual line of sight alone does not establish radio clearance. The first Fresnel zone occupies space around the direct path. The 60% radius is a planning guide, not a guarantee of service.</p>
<table border="1" cellpadding="6"><tr><th>Operator observation</th><th>Possible effect to investigate</th></tr>
<tr><td>Concrete or reinforced pillar</td><td>Attenuation, reflection and edge diffraction; composition and geometry matter.</td></tr>
<tr><td>Metal panels or coated glazing</td><td>Reflection and attenuation; the effect depends on frequency and angle.</td></tr>
<tr><td>Foliage, moisture or people</td><td>Variable absorption, scattering and obstruction.</td></tr>
<tr><td>Different antenna orientations</td><td>Polarization and antenna-pattern differences.</td></tr></table>
<p>A power measurement cannot identify which mechanism caused a change. Avoid assigning a fixed loss to all concrete walls. Record material, position, orientation and uncertainty; compare repeat measurements on both sides or along a route.</p>
<p>References: <a href="https://www.itu.int/rec/R-REC-P.526/en">ITU-R P.526</a>, <a href="https://www.itu.int/rec/R-REC-P.2040/en">ITU-R P.2040</a>.</p>'''),
    ('Survey coverage, AP identity and DAS', '''<h2>What a coverage map can claim</h2>
<p>A measurement map can show signal strength without knowing an AP identity. It then describes the connection observed at each point, which may change transmitter while you walk.</p>
<p>For transmitter-specific coverage, retain a stable Wi-Fi BSSID or full cellular identity. An SSID is a network name, and a PCI alone is not a globally unique cell identifier. A DAS can use a shared cell identity across multiple remote antennas; that does not reveal which remote served the phone.</p>
<p><b>Measured points</b> show actual observations. A smoothed heat map estimates between them. Keep floors, visits, metrics, bands and incompatible acquisition settings separate. A missing sample must not appear as weak signal.</p>
<p>Manually placed points are operator observations, not GPS fixes. Floor-plan coordinates have no geographic meaning without explicit registration.</p>
<p>Reference: <a href="https://developer.android.com/reference/android/net/wifi/WifiInfo">Android Wi-Fi connection information</a>.</p>'''),
    ('IPv4 CIDR and IPv6 address charts', '''<h2>Address planning</h2>
<table border="1" cellpadding="6"><tr><th>IPv4 prefix</th><th>Total addresses</th><th>Conventional host count</th></tr>
<tr><td>/24</td><td>256</td><td>254</td></tr><tr><td>/25</td><td>128</td><td>126</td></tr><tr><td>/26</td><td>64</td><td>62</td></tr><tr><td>/27</td><td>32</td><td>30</td></tr><tr><td>/28</td><td>16</td><td>14</td></tr><tr><td>/29</td><td>8</td><td>6</td></tr><tr><td>/30</td><td>4</td><td>2</td></tr><tr><td>/31</td><td>2</td><td>2 on point-to-point links</td></tr><tr><td>/32</td><td>1</td><td>Single-address route</td></tr></table>
<p>IPv6 addresses are 128 bits; a /64 contains 2^64 addresses. IPv6 has no broadcast address. An address count is not a claim that every address can be assigned under a particular deployment policy.</p>
<p>The subnet inspector accepts an interface address and normalizes its network. It does not discover hosts, validate leases or prove reachability.</p>
<p>References: <a href="https://www.rfc-editor.org/rfc/rfc4632">RFC 4632</a>, <a href="https://www.rfc-editor.org/rfc/rfc3021">RFC 3021</a>, <a href="https://www.rfc-editor.org/rfc/rfc4291">RFC 4291</a>.</p>'''),
    ('Networking: DHCP, DNS, MTU and test sequence', '''<h2>Separate radio quality from network service</h2>
<table border="1" cellpadding="6"><tr><th>Stage</th><th>Useful check</th></tr>
<tr><td>Link</td><td>Association, interface state, radio quality and negotiation.</td></tr><tr><td>Addressing</td><td>Address, prefix, default route and lease; DHCP failure is not automatically an RF fault.</td></tr><tr><td>Local path</td><td>Gateway reachability and loss; a blocked ICMP response alone does not prove failure.</td></tr><tr><td>Names</td><td>DNS resolution compared with direct-IP access.</td></tr><tr><td>Application path</td><td>Relevant service, authentication, latency and throughput under representative load.</td></tr></table>
<p>MTU limits an IP packet on a link. Path MTU is constrained along the route. TCP MSS describes TCP payload and depends on IP/TCP headers; encapsulation and options change the budget. Do not assume every path has a 1500-byte MTU or every packet has minimum headers.</p>
<p>Record test target and direction: a nearby server and a remote internet server answer different questions.</p>
<p>References: <a href="https://www.rfc-editor.org/rfc/rfc2131">DHCP</a>, <a href="https://www.rfc-editor.org/rfc/rfc1034">DNS</a>, <a href="https://www.rfc-editor.org/rfc/rfc1191">Path MTU discovery</a>.</p>'''),
)
