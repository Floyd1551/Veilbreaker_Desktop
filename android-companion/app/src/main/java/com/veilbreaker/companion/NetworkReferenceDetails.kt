package com.veilbreaker.companion

/** Offline field context. Examples are illustrative, not captured evidence. */
internal object NetworkReferenceDetails {
    fun details(id: String): String? = when (id) {
        "expanded-ipv4-private" -> """
            VALUE REFERENCE
            RFC 1918 private blocks: 10.0.0.0–10.255.255.255 (/8), 172.16.0.0–172.31.255.255 (/12), and 192.168.0.0–192.168.255.255 (/16). 172.32.0.0 is outside the RFC 1918 172.16/12 block. Other special-purpose blocks have different rules.

            FIELD METHOD
            Record each network's address AND prefix. Calculate both network ranges before joining sites; two disjoint prefixes may be reached normally, whereas overlapping ranges can make route selection ambiguous. Identify NAT and VPN boundaries before assuming identical addresses identify the same host. A private address is not evidence of a firewall or Internet access.

            Source: IETF RFC 1918 (1996), https://www.rfc-editor.org/rfc/rfc1918.html; special-purpose registry, https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml
        """.trimIndent()
        "expanded-cidr" -> """
            VALUE REFERENCE
            For IPv4 a /24 has 256 total addresses; a /26 has 64; a /30 has 4. These totals include all addresses, not necessarily usable hosts. A /31 can use both addresses on a point-to-point link under RFC 3021; do not apply the usual two-address subtraction blindly.

            FIELD METHOD
            Apply the prefix mask to identify the network, then compare the destination against that range. A match normally uses the on-link path; a nonmatch needs a route or default gateway. For example, 192.0.2.65/26 belongs to 192.0.2.64/26; 192.0.2.130 is outside that prefix. Check actual routing and local policy as exceptions can exist.

            Sources: IETF RFC 4632 (2006), https://www.rfc-editor.org/rfc/rfc4632.html; RFC 3021 (2000), https://www.rfc-editor.org/rfc/rfc3021.html
        """.trimIndent()
        "expanded-cidr-table" -> """
            VALUE REFERENCE
            Total addresses are 2^(32 − prefix length): /24 = 256, /25 = 128, /26 = 64, /27 = 32, /28 = 16, /29 = 8 and /30 = 4. A /31 has two addresses and a /32 has one. The adjacent table lists total addresses, not a promise of assignable hosts.

            FIELD METHOD
            Identify the prefix first; compare the network range with adjacent allocations and the actual gateway. Traditional broadcast-subnet host counts often subtract network and broadcast addresses, but /31 point-to-point links and operator policy need separate handling. Keep planned address assignments separate from an observed DHCP lease.

            Sources: IETF RFC 4632 (2006), https://www.rfc-editor.org/rfc/rfc4632.html; RFC 3021 (2000), https://www.rfc-editor.org/rfc/rfc3021.html
        """.trimIndent()
        "expanded-ipv6" -> """
            VALUE REFERENCE
            fe80::/10 identifies link-local unicast; fc00::/7 is the unique-local block, with locally assigned addresses using fd00::/8. Global unicast addresses are routable only where routing and policy permit. An interface or zone identifier can be needed when using a link-local address.

            FIELD METHOD
            Record full address, prefix length, interface, source address and selected route. Test a known destination on the same interface before comparing with a global target. A link-local address proves neither a default route nor Internet service; a unique-local address is not inherently a security boundary.

            Sources: IETF RFC 4291 (2006), https://www.rfc-editor.org/rfc/rfc4291.html; RFC 4193 (2005), https://www.rfc-editor.org/rfc/rfc4193.html
        """.trimIndent()
        "expanded-mtu" -> """
            VALUE REFERENCE
            An illustrative 1500-byte IPv4 MTU with a 20-byte IPv4 header and 20-byte TCP header leaves a nominal 1460-byte MSS. IPv6's base header is 40 bytes, giving 1440 bytes with a 20-byte TCP header. Options, extension headers and encapsulation change actual packet overhead; do not assume a fixed path MTU.

            FIELD METHOD
            If a session connects but larger transfers stall, record interface MTU, IP version, tunnel and target; use approved size-controlled probes and inspect packet-too-big or fragmentation-needed messages. Compare both directions and another path. Filtering of ICMP can disrupt path-MTU discovery, but does not prove that every timeout is an MTU issue.

            Sources: IETF RFC 9293 (2022), https://www.rfc-editor.org/rfc/rfc9293.html; IPv6 path MTU, RFC 8201 (2017), https://www.rfc-editor.org/rfc/rfc8201.html
        """.trimIndent()
        "expanded-bdp" -> """
            VALUE REFERENCE
            BDP in bytes = path rate in bits/s × round-trip time in seconds ÷ 8. An illustrative 100 Mb/s path with 40 ms RTT has a BDP of 500,000 bytes, approximately 488 KiB. Use the RTT and target rate for the same path and time window.

            FIELD METHOD
            Compare the estimated in-flight requirement with the available send/receive windows before blaming a high-latency link for limited throughput. Record test direction, target, duration, load and transport. A sufficiently large window is necessary for this simple model but cannot overcome loss, congestion, application limits or a slow endpoint.

            Source: IETF RFC 6349 (2011), https://www.rfc-editor.org/rfc/rfc6349.html
        """.trimIndent()
        "expanded-dns" -> """
            VALUE REFERENCE
            A and AAAA records carry IPv4 and IPv6 addresses; CNAME provides an alias; MX identifies mail exchangers; TXT carries text. Recursive resolvers may answer from a cache, and record TTL governs caching behavior rather than application availability.

            FIELD METHOD
            Record the exact name, resolver, response, query type and time. Compare the configured resolver with an authorized alternative and test the returned address independently. A cached answer can succeed during an upstream DNS fault; successful resolution alone does not prove routing, TLS or the application is working.

            Sources: IETF RFC 1034 (1987), https://www.rfc-editor.org/rfc/rfc1034.html; RFC 1035 (1987), https://www.rfc-editor.org/rfc/rfc1035.html; IPv6 AAAA, RFC 3596 (2003), https://www.rfc-editor.org/rfc/rfc3596.html
        """.trimIndent()
        "expanded-dhcp" -> """
            VALUE REFERENCE
            A typical IPv4 lease exchange uses Discover, Offer, Request and Acknowledgment. Configuration can include address, subnet mask, router and DNS server; lease timers and renewal behavior are separate from physical link state.

            FIELD METHOD
            Record the lease address, prefix, gateway, resolver, server and remaining lease time when exposed. Compare a working and affected client on the same VLAN. An address alone does not verify that the gateway or DNS works; a missing or incorrect option can produce apparently partial connectivity. Avoid releasing a production lease merely to test it without operational coordination.

            Sources: IETF RFC 2131 (1997), https://www.rfc-editor.org/rfc/rfc2131.html; DHCP options, RFC 2132 (1997), https://www.rfc-editor.org/rfc/rfc2132.html
        """.trimIndent()
        "expanded-latency" -> """
            VALUE REFERENCE
            RTT measures a round trip to the chosen target, not a one-way delay. A 20 ms RTT does not establish symmetric 10 ms one-way paths. Delay variation depends on the chosen measurement method and interval; report that method with the value. Loss is observed missing responses over a stated count and interval.

            FIELD METHOD
            Collect repeated probes to a local gateway and a known remote target at comparable intervals; record duration, sample count, interface and load. A missing ICMP reply can reflect filtering or rate limiting. Compare with application-level results and other clients before concluding a link is dropping user traffic.

            Sources: IETF RFC 2681 (1999), https://www.rfc-editor.org/rfc/rfc2681.html; IP packet delay variation, RFC 3393 (2002), https://www.rfc-editor.org/rfc/rfc3393.html
        """.trimIndent()
        "expanded-fiber-budget" -> """
            VALUE REFERENCE
            Example: 2 km at 0.4 dB/km plus four mated pairs at 0.3 dB each gives an illustrative 2.0 dB path loss before splices, splitters and margin. Replace every example value with the actual fiber, wavelength and component specifications. Link budget compares transmitter power and total loss against receiver sensitivity AND maximum allowed input.

            FIELD METHOD
            Record transmit range, receive sensitivity, overload limit, wavelength, fiber length, all mated connections, splices, splitters and margin. Measure using the approved reference method and calibrated equipment; compare observed insertion loss with the planned cable-plant budget. Excess optical power may require an approved attenuator.

            Source: Fiber Optic Association, loss budget guidance, https://www.thefoa.org/tech/lossbudg.htm; expected loss, https://www.thefoa.org/tech/loss-est.htm
        """.trimIndent()
        "expanded-fiber-connector" -> """
            VALUE REFERENCE
            Connector loss is associated with a mated connection and depends on geometry, condition and reference method. A loss allowance in a design is not a measurement. UPC and APC interfaces require compatible mating hardware; use manufacturer identification and specifications rather than relying only on color.

            FIELD METHOD
            Follow site laser-safety rules; never look into an end face. Inspect both sides with approved equipment, clean only as required, and inspect again before mating. Record connector type, reference method, wavelength and inspection outcome. If excessive loss remains after cleaning, investigate patch leads, polarity and damaged components with appropriate test equipment.

            Source: Fiber Optic Association, inspection and cleaning guidance, https://www.thefoa.org/tech/ref/testing/test/scope.html
        """.trimIndent()
        "expanded-poe" -> """
            VALUE REFERENCE
            IEEE 802.3af, 802.3at and 802.3bt describe different powered-device and source capabilities. Do not assume that a port's marketing label or total switch budget guarantees the needed power at the device. Cable resistance, allocation, number of pairs and negotiated operating mode affect delivery.

            FIELD METHOD
            Record source model, port standard/class, switch-wide available budget, powered-device steady and startup demand, and cable length and termination. Compare switch allocation and fault logs with the device's rated requirements. Substitute known-good rated components only within site procedures. Electrical work and testing must follow equipment instructions.

            Source: IEEE 802.3 Ethernet working group, https://www.ieee802.org/3/; verify the applicable standard edition and manufacturer ratings for the deployed equipment.
        """.trimIndent()
        "expanded-ups" -> """
            VALUE REFERENCE
            Ideal runtime in hours = usable watt-hours ÷ load watts. For an illustrative 240 Wh usable battery and 40 W constant load, the ideal result is 6 hours before conversion losses or reserve. Amp-hours alone cannot be converted to watt-hours without a relevant voltage; actual usable energy varies with load and equipment.

            FIELD METHOD
            Inventory steady and startup loads, measure actual input power where safe, and review the manufacturer's runtime curves. Include inverter/converter losses, battery age, temperature and reserve. Validate with an authorized controlled test; do not present the ideal estimate as a guaranteed runtime or assume all nameplate battery energy is usable.

            Source: U.S. Department of Energy, energy units and electrical basics, https://www.eia.gov/energyexplained/electricity/measuring-electricity.php; use the specific UPS manufacturer's runtime and safety documentation.
        """.trimIndent()
        else -> null
    }
}
