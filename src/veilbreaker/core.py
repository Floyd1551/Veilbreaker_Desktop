#!/usr/bin/env python3
"""
Veilbreaker Diagnostic Reasoning Engine
NetworkHub / Outpost Relay

An explainable, evidence-weighted diagnostic engine for field networking,
cellular/FWA, WAN, Wi-Fi, DNS, MTU and device-health troubleshooting.

Design goals:
  * Never equate a single threshold with root cause.
  * Correlate independent observations across layers.
  * Track supporting AND contradictory evidence.
  * Rank competing hypotheses with confidence-like scores.
  * Admit uncertainty when evidence is incomplete.
  * Recommend the next test with the highest diagnostic value.
  * Keep every conclusion explainable to a field technician/engineer.

No third-party Python packages are mandatory. Native AT-modem collection uses
pyserial when available (recommended on Windows); Linux also has a minimal
stdlib POSIX serial fallback. External JSON adapters remain supported.

Primary host support:
  * Linux: NetworkHub / OR-Base native host.
  * Windows 10/11: native collectors use PowerShell/NetTCPIP, netsh, route.exe,
    and Windows ping semantics; no WSL dependency is required.
  * Starlink: read-only local terminal telemetry through the dish gRPC service.
    Veilbreaker supports the community starlink_grpc module or grpcurl reflection.
  * Cellular: native read-only AT support for Sierra Wireless EM9 (EM9190/
    EM9191/EM7690/EM92-family) and Quectel RM5xx/RG5xx modules, plus a generic
    3GPP AT fallback for standards-compliant modems. Driver registry is extensible.

Windows examples:
  py Veilbreaker_v0.9.3_multimodem.py doctor
  py Veilbreaker_v0.9.3_multimodem.py platform-info
  py Veilbreaker_v0.9.3_multimodem.py run --active --guided
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence
import json
import math


# =============================================================================
# DATA MODEL
# =============================================================================

class Severity(str, Enum):
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    CRITICAL = "critical"


class Domain(str, Enum):
    DATA_QUALITY = "data_quality"
    CELLULAR_RF = "cellular_rf"
    RAN = "ran"
    CARRIER_CORE = "carrier_core"
    WAN = "wan"
    LOCAL_LAN = "local_lan"
    WIFI = "wifi"
    DNS = "dns"
    MTU = "mtu"
    DEVICE = "device"
    GPS = "gps"
    SPECTRUM = "spectrum"
    SATELLITE = "satellite"
    SDR = "sdr"
    POWER = "power"
    UNKNOWN = "unknown"


class Direction(str, Enum):
    SUPPORT = "support"
    CONTRADICT = "contradict"


class Quality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Evidence:
    hypothesis_id: str
    direction: Direction
    weight: float
    statement: str
    keys: List[str] = field(default_factory=list)
    quality: Quality = Quality.HIGH


@dataclass
class Finding:
    finding_id: str
    severity: Severity
    domain: Domain
    title: str
    observation: str
    interpretation: str
    recommendation: str
    confidence: float
    evidence_keys: List[str] = field(default_factory=list)


@dataclass
class Hypothesis:
    hypothesis_id: str
    title: str
    domain: Domain
    prior: float
    support: float = 0.0
    contradiction: float = 0.0
    confidence: float = 0.0
    status: str = "unassessed"
    evidence: List[Evidence] = field(default_factory=list)

    def add(self, ev: Evidence) -> None:
        self.evidence.append(ev)
        q = {Quality.LOW: 0.65, Quality.MEDIUM: 0.85, Quality.HIGH: 1.0}[ev.quality]
        w = max(0.0, ev.weight) * q
        if ev.direction == Direction.SUPPORT:
            self.support += w
        else:
            self.contradiction += w


@dataclass
class NextTest:
    test_id: str
    title: str
    purpose: str
    action: str
    expected_signal: str
    priority: int
    diagnostic_value: float
    domains: List[Domain] = field(default_factory=list)


@dataclass
class DiagnosticReport:
    status: str
    health_score: int
    data_quality_score: int
    findings: List[Finding]
    hypotheses: List[Hypothesis]
    next_tests: List[NextTest]
    summary: List[str]
    normalized_metrics: Dict[str, Any]
    engine_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class DiagnosticProfile:
    name: str = "field_validation"

    # Broad engineering guidance, not vendor/carrier guarantees.
    rsrp_good: float = -90.0
    rsrp_fair: float = -100.0
    rsrp_poor: float = -110.0
    rsrq_fair: float = -15.0
    rsrq_poor: float = -20.0
    sinr_good: float = 13.0
    sinr_fair: float = 5.0
    sinr_poor: float = 0.0

    latency_warn_ms: float = 100.0
    latency_critical_ms: float = 250.0
    jitter_warn_ms: float = 30.0
    loss_warn_pct: float = 1.0
    loss_critical_pct: float = 5.0

    min_dl_mbps: float = 10.0
    min_ul_mbps: float = 3.0
    dns_warn_ms: float = 250.0
    dns_critical_ms: float = 1000.0

    minimum_hypothesis_confidence: float = 0.18
    strong_hypothesis_confidence: float = 0.60


ALIASES = {
    "rsrp_dbm": "rsrp",
    "rsrq_db": "rsrq",
    "sinr_db": "sinr",
    "snr": "sinr",
    "dl_mbps": "download_mbps",
    "down_mbps": "download_mbps",
    "throughput_dl_mbps": "download_mbps",
    "ul_mbps": "upload_mbps",
    "up_mbps": "upload_mbps",
    "throughput_ul_mbps": "upload_mbps",
    "loss_pct": "packet_loss_pct",
    "packet_loss": "packet_loss_pct",
    "latency": "latency_ms",
    "ping_ms": "latency_ms",
    "jitter": "jitter_ms",
    "dns_ms": "dns_latency_ms",
    "first_hop_ms": "gateway_latency_ms",
    "gateway_ping_ms": "gateway_latency_ms",
    "mtu_bytes": "mtu",
}


def _f(v: Any) -> Optional[float]:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> Optional[int]:
    try:
        return None if v is None or v == "" else int(v)
    except (TypeError, ValueError):
        return None


class MetricNormalizer:
    FLOATS = {
        "rsrp", "rsrq", "sinr", "latency_ms", "gateway_latency_ms",
        "jitter_ms", "packet_loss_pct", "download_mbps", "upload_mbps",
        "dns_latency_ms", "cpu_pct", "memory_pct", "temperature_c",
        "wifi_rssi_dbm", "wifi_signal_pct", "wifi_retry_pct", "wifi_channel_util_pct",
        "spectrum_noise_floor_dbm", "spectrum_peak_dbm",
        "lte_rsrp", "lte_rsrq", "lte_rssi", "lte_sinr",
        "nr_rsrp", "nr_rsrq", "nr_rssi", "nr_sinr",
        "modem_temperature_c", "modem_tx_power_dbm",
    }
    INTS = {"mtu", "pci", "earfcn", "nrarfcn", "bandwidth_mhz", "carrier_aggregation_count",
            "lte_pci", "nr_pci", "lte_earfcn", "nr_nrarfcn", "lte_bandwidth_mhz",
            "nr_bandwidth_mhz", "neighbor_cell_count"}
    BOOLS = {
        "dns_success", "gateway_reachable", "internet_reachable",
        "ipv4_present", "ipv6_present", "gps_fix", "modem_registered",
        "sim_ready", "apn_attached",
    }

    def normalize(self, raw: Mapping[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in raw.items():
            k = str(key).strip().lower()
            out[ALIASES.get(k, k)] = value

        for k in self.FLOATS:
            if k in out:
                out[k] = _f(out[k])
        for k in self.INTS:
            if k in out:
                out[k] = _i(out[k])
        for k in self.BOOLS:
            if k in out:
                v = out[k]
                if isinstance(v, str):
                    out[k] = v.strip().lower() in {"1", "true", "yes", "up", "ok", "ready"}
                else:
                    out[k] = bool(v)

        if out.get("technology") is not None:
            tech = str(out["technology"]).upper().replace("_", " ").strip()
            out["technology"] = tech.replace("5GNSA", "5G NSA").replace("5GSA", "5G SA")
        return out


# =============================================================================
# REASONING ENGINE
# =============================================================================

class VeilbreakerLogicEngine:
    VERSION = "1.0.0-expert"

    def __init__(self, profile: Optional[DiagnosticProfile] = None):
        self.profile = profile or DiagnosticProfile()
        self.normalizer = MetricNormalizer()

    def analyze(self, raw_metrics: Mapping[str, Any]) -> DiagnosticReport:
        m = self.normalizer.normalize(raw_metrics)
        findings: List[Finding] = []
        evidence: List[Evidence] = []

        dq = self._data_quality(m, findings)
        self._registration(m, findings, evidence)
        self._cellular_rf(m, findings, evidence)
        self._multirat_cellular_reasoning(m, findings, evidence)
        self._transport(m, findings, evidence)
        self._dns(m, findings, evidence)
        self._mtu(m, findings, evidence)
        self._performance(m, findings, evidence)
        self._wifi(m, findings, evidence)
        self._device(m, findings, evidence)
        self._cross_domain(m, findings, evidence)

        hypotheses = self._rank_hypotheses(evidence)
        tests = self._next_tests(m, hypotheses)
        health = self._health(findings, dq)
        status = self._status(health)
        summary = self._summary(hypotheses, findings, tests, health, status, dq)

        sev_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.NOTICE: 2, Severity.INFO: 3}
        findings.sort(key=lambda x: (sev_order[x.severity], -x.confidence))

        return DiagnosticReport(
            status=status,
            health_score=health,
            data_quality_score=dq,
            findings=findings,
            hypotheses=hypotheses,
            next_tests=tests,
            summary=summary,
            normalized_metrics=m,
            engine_version=self.VERSION,
        )

    # ---------------------------------------------------------------------
    # plumbing
    # ---------------------------------------------------------------------

    @staticmethod
    def _present(m: Mapping[str, Any], *keys: str) -> bool:
        return all(m.get(k) is not None for k in keys)

    @staticmethod
    def _finding(findings: List[Finding], finding_id: str, severity: Severity,
                 domain: Domain, title: str, observation: str, interpretation: str,
                 recommendation: str, confidence: float, keys: Sequence[str]) -> None:
        findings.append(Finding(
            finding_id, severity, domain, title, observation, interpretation,
            recommendation, max(0.0, min(1.0, confidence)), list(keys)
        ))

    @staticmethod
    def _evidence(evidence: List[Evidence], hid: str, direction: Direction,
                  weight: float, statement: str, keys: Sequence[str],
                  quality: Quality = Quality.HIGH) -> None:
        evidence.append(Evidence(hid, direction, weight, statement, list(keys), quality))

    # ---------------------------------------------------------------------
    # data quality
    # ---------------------------------------------------------------------

    def _data_quality(self, m: Mapping[str, Any], findings: List[Finding]) -> int:
        score = 100
        bounds = {
            "rsrp": (-160, -30), "rsrq": (-40, 5), "sinr": (-30, 60),
            "latency_ms": (0, 10000), "jitter_ms": (0, 10000),
            "packet_loss_pct": (0, 100), "download_mbps": (0, 100000),
            "upload_mbps": (0, 100000), "mtu": (576, 10000),
            "dns_latency_ms": (0, 30000),
            "satellite_latency_ms": (0, 10000),
            "satellite_packet_loss_pct": (0, 100),
            "satellite_obstructed_pct": (0, 100),
            "starlink_pop_ping_latency_ms": (0, 10000),
        }
        bad = []
        for key, (lo, hi) in bounds.items():
            if m.get(key) is not None and not (lo <= m[key] <= hi):
                bad.append(f"{key}={m[key]!r}")
                score -= 18

        satellite_context = (
            str(m.get("satellite_provider") or "").lower() != ""
            or any(str(k).startswith("satellite_") or str(k).startswith("starlink_") for k in m)
        )
        cellular_context = any(m.get(k) is not None for k in (
            "rsrp", "rsrq", "sinr", "modem_registered", "apn_attached", "lte_band", "nr_band"
        ))
        if satellite_context and not cellular_context:
            core = ["satellite_registered", "satellite_latency_ms", "satellite_packet_loss_pct", "satellite_obstructed_pct"]
            coverage_action = "Capture terminal state, obstruction, Starlink/access-path latency/drop, and an independent downstream path test together whenever possible."
        else:
            core = ["rsrp", "rsrq", "sinr", "latency_ms", "packet_loss_pct", "download_mbps"]
            coverage_action = "Capture RF quality, loss/latency and throughput together whenever possible."
        missing = [k for k in core if m.get(k) is None]
        score -= min(30, 5 * len(missing))

        if bad:
            self._finding(findings, "DATA-001", Severity.WARNING, Domain.DATA_QUALITY,
                "Questionable measurement input", "; ".join(bad),
                "One or more measurements are outside plausible input bounds.",
                "Validate units and source output before trusting downstream diagnosis.",
                0.98, [])
        if len(missing) >= 4:
            self._finding(findings, "DATA-002", Severity.NOTICE, Domain.DATA_QUALITY,
                "Limited diagnostic coverage", f"Missing: {', '.join(missing)}.",
                "Root-cause confidence is constrained because several independent domains were not sampled.",
                coverage_action,
                0.95, [])
        return max(0, min(100, score))

    # ---------------------------------------------------------------------
    # registration / provisioning
    # ---------------------------------------------------------------------

    def _registration(self, m, findings, evidence):
        if m.get("sim_ready") is False:
            self._finding(findings, "CELL-REG-001", Severity.CRITICAL, Domain.DEVICE,
                "SIM not ready", "The modem reports SIM state not ready.",
                "Normal packet service cannot be established until SIM/eSIM state is valid.",
                "Validate SIM presence/PIN, activation, entitlement and selected SIM slot/profile.",
                0.99, ["sim_ready"])
            self._evidence(evidence, "device_provisioning", Direction.SUPPORT, 5,
                           "SIM state is not ready.", ["sim_ready"])

        if m.get("modem_registered") is False:
            self._finding(findings, "CELL-REG-002", Severity.CRITICAL, Domain.RAN,
                "Modem not registered", "Network registration is false.",
                "The failure occurs before normal IP-service validation.",
                "Check RF availability, allowed RAT/bands, SIM entitlement, roaming and carrier provisioning.",
                0.98, ["modem_registered"])
            self._evidence(evidence, "registration_failure", Direction.SUPPORT, 5,
                           "Modem is not registered.", ["modem_registered"])
        elif m.get("modem_registered") is True:
            self._evidence(evidence, "registration_failure", Direction.CONTRADICT, 4,
                           "Modem is registered.", ["modem_registered"])

        if m.get("apn_attached") is False:
            self._finding(findings, "CELL-REG-003", Severity.CRITICAL, Domain.CARRIER_CORE,
                "Packet-data attach/APN failure", "Radio registration exists but data attachment is false.",
                "The RF/RAN registration stage succeeded; session establishment is failing later.",
                "Validate APN, private-network entitlement, PDP/PDN profile, SIM provisioning and core policy.",
                0.97, ["apn_attached", "modem_registered"])
            self._evidence(evidence, "apn_or_core", Direction.SUPPORT, 5,
                           "Packet-data attach failed after network registration.", ["apn_attached", "modem_registered"])

    # ---------------------------------------------------------------------
    # cellular / RAN
    # ---------------------------------------------------------------------

    def _cellular_rf(self, m, findings, evidence):
        p = self.profile
        rsrp, rsrq, sinr = m.get("rsrp"), m.get("rsrq"), m.get("sinr")

        if rsrp is not None:
            if rsrp <= p.rsrp_poor:
                self._finding(findings, "CELL-RF-001", Severity.CRITICAL, Domain.CELLULAR_RF,
                    "Very weak serving-cell signal", f"RSRP is {rsrp:.1f} dBm.",
                    "The modem has little downlink reference-signal margin. Path loss, penetration, antenna loss or cell-edge operation may dominate.",
                    "Compare indoor/outdoor placement, antenna path, serving cell/band, cable loss and antenna position.",
                    0.94, ["rsrp"])
                self._evidence(evidence, "weak_coverage", Direction.SUPPORT, 4.5,
                               f"RSRP is very weak ({rsrp:.1f} dBm).", ["rsrp"])
            elif rsrp <= p.rsrp_fair:
                self._finding(findings, "CELL-RF-002", Severity.WARNING, Domain.CELLULAR_RF,
                    "Marginal serving-cell signal", f"RSRP is {rsrp:.1f} dBm.",
                    "Coverage may work but has reduced fade and load margin.",
                    "Validate stability under load and compare alternate placement/bands.",
                    0.86, ["rsrp"])
                self._evidence(evidence, "weak_coverage", Direction.SUPPORT, 2.5,
                               f"RSRP is marginal ({rsrp:.1f} dBm).", ["rsrp"])
            elif rsrp >= p.rsrp_good:
                self._evidence(evidence, "weak_coverage", Direction.CONTRADICT, 3.2,
                               f"RSRP is healthy ({rsrp:.1f} dBm).", ["rsrp"])

        if rsrq is not None:
            if rsrq <= p.rsrq_poor:
                self._finding(findings, "CELL-RF-010", Severity.CRITICAL, Domain.RAN,
                    "Severely degraded radio quality", f"RSRQ is {rsrq:.1f} dB.",
                    "Reference-signal quality is poor relative to total received power; interference, load, overlap or geometry may be involved.",
                    "Correlate with SINR, serving/neighbor cells, band, time-of-day and spectrum occupancy.",
                    0.90, ["rsrq"])
                self._evidence(evidence, "ran_interference_or_load", Direction.SUPPORT, 3.7,
                               f"RSRQ is poor ({rsrq:.1f} dB).", ["rsrq"])
            elif rsrq <= p.rsrq_fair:
                self._evidence(evidence, "ran_interference_or_load", Direction.SUPPORT, 2.0,
                               f"RSRQ is degraded ({rsrq:.1f} dB).", ["rsrq"])

        if sinr is not None:
            if sinr <= p.sinr_poor:
                self._finding(findings, "CELL-RF-011", Severity.CRITICAL, Domain.SPECTRUM,
                    "Poor SINR", f"SINR is {sinr:.1f} dB.",
                    "The wanted signal is not sufficiently separated from interference/noise for efficient modulation and coding.",
                    "Inspect spectrum/neighbor conditions and compare bands, cells, antenna orientation and location.",
                    0.95, ["sinr"])
                self._evidence(evidence, "ran_interference_or_load", Direction.SUPPORT, 4.7,
                               f"SINR is poor ({sinr:.1f} dB).", ["sinr"])
            elif sinr < p.sinr_fair:
                self._evidence(evidence, "ran_interference_or_load", Direction.SUPPORT, 3.1,
                               f"SINR is weak ({sinr:.1f} dB).", ["sinr"])
            elif sinr >= p.sinr_good:
                self._evidence(evidence, "ran_interference_or_load", Direction.CONTRADICT, 3.0,
                               f"SINR is healthy ({sinr:.1f} dB).", ["sinr"])

        # Expert pattern: strong energy, poor quality -> not classic weak coverage.
        if self._present(m, "rsrp", "sinr") and rsrp >= p.rsrp_good and sinr < p.sinr_fair:
            self._finding(findings, "CELL-CORR-001", Severity.WARNING, Domain.RAN,
                "Strong signal but poor radio quality", f"RSRP {rsrp:.1f} dBm; SINR {sinr:.1f} dB.",
                "This is not a classic weak-coverage pattern. The modem receives ample energy but the wanted signal is degraded by interference, overlap, loading or geometry.",
                "Prioritize spectrum/neighbor-cell analysis, band comparison and time-of-day load testing over simply adding gain.",
                0.96, ["rsrp", "sinr"])
            self._evidence(evidence, "ran_interference_or_load", Direction.SUPPORT, 5,
                           "Healthy signal strength coexists with poor SINR.", ["rsrp", "sinr"])
            self._evidence(evidence, "weak_coverage", Direction.CONTRADICT, 4,
                           "Strong RSRP argues against simple weak coverage.", ["rsrp"])

        # Expert pattern: weak energy, clean channel -> coverage/path loss more plausible.
        if self._present(m, "rsrp", "sinr") and rsrp <= p.rsrp_fair and sinr >= p.sinr_good:
            self._finding(findings, "CELL-CORR-002", Severity.NOTICE, Domain.CELLULAR_RF,
                "Weak but comparatively clean radio link", f"RSRP {rsrp:.1f} dBm; SINR {sinr:.1f} dB.",
                "The link is weak without strong evidence of a noisy/interference-dominated environment.",
                "Test antenna/location improvement before treating the issue primarily as congestion/interference.",
                0.91, ["rsrp", "sinr"])
            self._evidence(evidence, "weak_coverage", Direction.SUPPORT, 4,
                           "Weak RSRP with good SINR is consistent with clean but weak coverage.", ["rsrp", "sinr"])
            self._evidence(evidence, "ran_interference_or_load", Direction.CONTRADICT, 2.5,
                           "Good SINR argues against severe interference.", ["sinr"])

    def _multirat_cellular_reasoning(self, m, findings, evidence):
        """Reason separately about LTE anchor and NR leg instead of collapsing NSA to one number."""
        tech = str(m.get("technology") or "").upper()
        lrsrp, lsinr = _f(m.get("lte_rsrp")), _f(m.get("lte_sinr"))
        nrsrp, nsinr = _f(m.get("nr_rsrp")), _f(m.get("nr_sinr"))
        temp = _f(m.get("modem_temperature_c"))
        p = self.profile

        if "NSA" in tech:
            if lrsrp is not None and nrsrp is not None and lrsrp <= p.rsrp_fair and nrsrp >= p.rsrp_good:
                self._finding(findings, "CELL-NSA-001", Severity.WARNING, Domain.RAN,
                    "5G NSA has a weak LTE anchor", f"LTE anchor RSRP {lrsrp:.1f} dBm; NR RSRP {nrsrp:.1f} dBm.",
                    "The NR leg is stronger than the LTE anchor that still carries important NSA control/signaling responsibilities.",
                    "Compare the LTE anchor band/cell and antenna response; do not judge NSA quality from the NR carrier alone.",
                    0.93, ["lte_rsrp", "nr_rsrp", "technology"])
                self._evidence(evidence, "lte_anchor_impairment", Direction.SUPPORT, 4.3,
                    "NR is healthy while the NSA LTE anchor is weak.", ["lte_rsrp", "nr_rsrp", "technology"])
            if lrsrp is not None and nrsrp is not None and lrsrp >= p.rsrp_good and nrsrp <= p.rsrp_fair:
                self._finding(findings, "CELL-NSA-002", Severity.WARNING, Domain.RAN,
                    "5G NSA NR leg is weaker than the LTE anchor", f"LTE RSRP {lrsrp:.1f} dBm; NR RSRP {nrsrp:.1f} dBm.",
                    "The LTE anchor is healthy, but the NR secondary carrier has materially less link margin.",
                    "Compare NR band/ARFCN, placement and throughput while tracking whether the NR leg remains assigned.",
                    0.90, ["lte_rsrp", "nr_rsrp", "technology"])
                self._evidence(evidence, "nr_secondary_impairment", Direction.SUPPORT, 3.8,
                    "LTE anchor is healthy while the NR secondary leg is weak.", ["lte_rsrp", "nr_rsrp", "technology"])
            if m.get("nr_band") and nrsrp is None:
                self._finding(findings, "CELL-NSA-003", Severity.NOTICE, Domain.RAN,
                    "NSA indicated without valid NR RF measurements",
                    f"Modem reports {m.get('nr_band')} / NSA context but no valid NR RSRP sample.",
                    "The network may advertise/retain NR context without an active measurable NR resource at this instant, or the vendor query may be sparse in idle state.",
                    "Repeat the radio snapshot during traffic before concluding that 5G NR is actively carrying data.",
                    0.72, ["technology", "nr_band", "nr_rsrp"])

        # Modem thermal thresholds are intentionally conservative and informational;
        # vendor-specific throttling points vary and should be learned per hardware.
        if temp is not None and temp >= 85:
            self._finding(findings, "CELL-DEV-THERM", Severity.WARNING, Domain.DEVICE,
                "Cellular modem is running hot", f"Modem reports {temp:.1f} C.",
                "High module temperature can precede vendor thermal mitigation and can make performance tests less repeatable.",
                "Improve airflow/cooling and repeat the same test after temperature stabilizes; inspect vendor mitigation state when available.",
                0.80, ["modem_temperature_c"])
            self._evidence(evidence, "modem_thermal", Direction.SUPPORT, 3.0,
                f"Modem temperature is high ({temp:.1f} C).", ["modem_temperature_c"])

    # ---------------------------------------------------------------------
    # transport / path localization
    # ---------------------------------------------------------------------

    def _transport(self, m, findings, evidence):
        p = self.profile
        latency, gateway = m.get("latency_ms"), m.get("gateway_latency_ms")
        loss, jitter = m.get("packet_loss_pct"), m.get("jitter_ms")

        if m.get("gateway_reachable") is False:
            self._finding(findings, "WAN-001", Severity.CRITICAL, Domain.LOCAL_LAN,
                "Upstream gateway unreachable", "The first routed hop is not reachable.",
                "The failure is at or before the local/default-gateway boundary.",
                "Validate interface state, VLAN, addressing, gateway, ARP/ND, cabling and router/modem handoff.",
                0.97, ["gateway_reachable"])
            self._evidence(evidence, "local_handoff", Direction.SUPPORT, 5,
                           "Default/upstream gateway is unreachable.", ["gateway_reachable"])
        elif m.get("gateway_reachable") is True:
            self._evidence(evidence, "local_handoff", Direction.CONTRADICT, 3.5,
                           "Default/upstream gateway is reachable.", ["gateway_reachable"])

        if loss is not None:
            if loss >= p.loss_critical_pct:
                sev, conf, weight = Severity.CRITICAL, 0.96, 4.5
            elif loss >= p.loss_warn_pct:
                sev, conf, weight = Severity.WARNING, 0.90, 2.7
            else:
                sev = None
            if sev:
                self._finding(findings, "WAN-LOSS-001" if sev == Severity.CRITICAL else "WAN-LOSS-002",
                    sev, Domain.WAN, "Severe packet loss" if sev == Severity.CRITICAL else "Elevated packet loss",
                    f"Packet loss is {loss:.2f}%.",
                    "Transport reliability is impaired, but loss must be localized before assigning root cause.",
                    "Compare loss to first hop, carrier/private-network target, tunnel endpoint and public target.",
                    conf, ["packet_loss_pct"])
                self._evidence(evidence, "wan_path", Direction.SUPPORT, weight,
                               f"Packet loss is elevated ({loss:.2f}%).", ["packet_loss_pct"])

        if latency is not None and latency >= p.latency_warn_ms:
            sev = Severity.CRITICAL if latency >= p.latency_critical_ms else Severity.WARNING
            conf = 0.94 if sev == Severity.CRITICAL else 0.86
            weight = 4.0 if sev == Severity.CRITICAL else 2.5
            self._finding(findings, "WAN-LAT-001" if sev == Severity.CRITICAL else "WAN-LAT-002",
                sev, Domain.WAN, "Excessive end-to-end latency" if sev == Severity.CRITICAL else "Elevated end-to-end latency",
                f"Latency is {latency:.1f} ms.",
                "Delay exceeds the preferred range; the point where delay begins must be established.",
                "Compare gateway/first-hop latency with carrier/core and internet targets.",
                conf, ["latency_ms"])
            self._evidence(evidence, "wan_path", Direction.SUPPORT, weight,
                           f"End-to-end latency is elevated ({latency:.1f} ms).", ["latency_ms"])

        if jitter is not None and jitter >= p.jitter_warn_ms:
            self._finding(findings, "WAN-JIT-001", Severity.WARNING, Domain.WAN,
                "High packet-delay variation", f"Jitter is {jitter:.1f} ms.",
                "Real-time applications may be impaired even if average throughput is acceptable.",
                "Compare jitter idle vs loaded and correlate with loss and RF quality.",
                0.88, ["jitter_ms"])
            self._evidence(evidence, "wan_path", Direction.SUPPORT, 2.3,
                           f"Jitter is elevated ({jitter:.1f} ms).", ["jitter_ms"])

        if gateway is not None and latency is not None:
            if gateway < 25 and latency >= p.latency_warn_ms:
                self._finding(findings, "WAN-CORR-001", Severity.WARNING, Domain.CARRIER_CORE,
                    "Latency appears beyond the local gateway",
                    f"Gateway latency {gateway:.1f} ms; end-to-end latency {latency:.1f} ms.",
                    "The local handoff responds quickly while delay accumulates farther along the path.",
                    "Inspect carrier transport, private APN routing, tunnel/SD-WAN path and upstream route.",
                    0.94, ["gateway_latency_ms", "latency_ms"])
                self._evidence(evidence, "carrier_or_core_path", Direction.SUPPORT, 4.3,
                               "Low first-hop latency but high end-to-end latency localizes delay upstream.",
                               ["gateway_latency_ms", "latency_ms"])
                self._evidence(evidence, "local_handoff", Direction.CONTRADICT, 3.5,
                               "Healthy first-hop latency argues against local handoff delay.", ["gateway_latency_ms"])
            elif gateway >= p.latency_warn_ms and latency >= gateway:
                self._finding(findings, "WAN-CORR-002", Severity.WARNING, Domain.LOCAL_LAN,
                    "Latency begins at the first routed hop", f"Gateway latency is already {gateway:.1f} ms.",
                    "A significant part of the delay is present before traffic reaches the wider WAN.",
                    "Inspect modem/RAN scheduling, local queueing, VLAN/handoff and gateway utilization.",
                    0.91, ["gateway_latency_ms", "latency_ms"])
                self._evidence(evidence, "local_handoff", Direction.SUPPORT, 3.7,
                               "First-hop latency is already excessive.", ["gateway_latency_ms"])

    # ---------------------------------------------------------------------
    # DNS / MTU / performance
    # ---------------------------------------------------------------------

    def _dns(self, m, findings, evidence):
        if m.get("dns_success") is False and m.get("internet_reachable") is True:
            self._finding(findings, "DNS-001", Severity.CRITICAL, Domain.DNS,
                "DNS failure with IP reachability intact",
                "IP reachability succeeds while DNS resolution fails.",
                "Transport is at least partially functional; name resolution is a distinct failure domain.",
                "Validate resolver addresses, DNS reachability, split-DNS/private-domain policy and firewall rules.",
                0.98, ["dns_success", "internet_reachable"])
            self._evidence(evidence, "dns_failure", Direction.SUPPORT, 5,
                           "DNS fails while raw IP connectivity works.", ["dns_success", "internet_reachable"])

        dns_ms = m.get("dns_latency_ms")
        if dns_ms is not None and dns_ms >= self.profile.dns_critical_ms:
            self._finding(findings, "DNS-002", Severity.WARNING, Domain.DNS,
                "Very slow DNS resolution", f"DNS resolution latency is {dns_ms:.1f} ms.",
                "DNS delay can make applications feel slow even if raw IP transport is acceptable.",
                "Compare configured resolver performance and private-DNS forwarding/tunnel dependencies.",
                0.90, ["dns_latency_ms"])
            self._evidence(evidence, "dns_failure", Direction.SUPPORT, 3,
                           "DNS response time is severely elevated.", ["dns_latency_ms"])

    def _mtu(self, m, findings, evidence):
        mtu = m.get("mtu")
        if mtu is None:
            return
        if mtu < 1280:
            self._finding(findings, "MTU-001", Severity.CRITICAL, Domain.MTU,
                "Abnormally small interface MTU", f"MTU is {mtu} bytes.",
                "The value is below the IPv6 minimum and unusual for general-purpose IP transport.",
                "Verify interface/tunnel configuration and confirm this is the intended path MTU.",
                0.98, ["mtu"])
            self._evidence(evidence, "mtu_or_fragmentation", Direction.SUPPORT, 4.5,
                           f"MTU is abnormally low ({mtu}).", ["mtu"])
        elif mtu < 1400:
            self._finding(findings, "MTU-002", Severity.NOTICE, Domain.MTU,
                "Reduced path/interface MTU", f"MTU is {mtu} bytes.",
                "A reduced MTU can be normal on mobile/tunneled paths but becomes suspicious when larger transfers or specific apps fail.",
                "Run a path-MTU test before changing configuration.",
                0.74, ["mtu"])
            self._evidence(evidence, "mtu_or_fragmentation", Direction.SUPPORT, 1.2,
                           f"Path uses a reduced MTU ({mtu}).", ["mtu"])

    def _performance(self, m, findings, evidence):
        p = self.profile
        dl, ul = m.get("download_mbps"), m.get("upload_mbps")
        if dl is not None and dl < p.min_dl_mbps:
            self._finding(findings, "PERF-DL-001", Severity.WARNING, Domain.WAN,
                "Low downstream throughput", f"Download is {dl:.2f} Mbps.",
                "Observed capacity is below the field baseline; throughput alone cannot identify the fault domain.",
                "Interpret with RF, loss, latency, interface rate, APN path and repeated tests.",
                0.86, ["download_mbps"])
            self._evidence(evidence, "throughput_degradation", Direction.SUPPORT, 3,
                           f"Download throughput is low ({dl:.2f} Mbps).", ["download_mbps"])
        if ul is not None and ul < p.min_ul_mbps:
            self._finding(findings, "PERF-UL-001", Severity.WARNING, Domain.WAN,
                "Low upstream throughput", f"Upload is {ul:.2f} Mbps.",
                "Upstream capacity is below the profile baseline.",
                "Compare uplink RF quality, loaded latency, carrier scheduling and alternate targets.",
                0.85, ["upload_mbps"])
            self._evidence(evidence, "throughput_degradation", Direction.SUPPORT, 2.8,
                           f"Upload throughput is low ({ul:.2f} Mbps).", ["upload_mbps"])

    # ---------------------------------------------------------------------
    # Wi-Fi and device health
    # ---------------------------------------------------------------------

    def _wifi(self, m, findings, evidence):
        rssi = m.get("wifi_rssi_dbm")
        signal_pct = m.get("wifi_signal_pct")
        retry = m.get("wifi_retry_pct")
        util = m.get("wifi_channel_util_pct")
        if rssi is not None and rssi < -75:
            self._finding(findings, "WIFI-001", Severity.WARNING, Domain.WIFI,
                "Weak Wi-Fi client signal", f"Wi-Fi RSSI is {rssi:.1f} dBm.",
                "The WLAN link may have reduced modulation rate and retransmission margin.",
                "Compare nearer the AP; validate band/channel and client/AP antenna geometry.",
                0.90, ["wifi_rssi_dbm"])
            self._evidence(evidence, "wifi_access", Direction.SUPPORT, 3.6,
                           "Wi-Fi RSSI is weak.", ["wifi_rssi_dbm"])
        elif rssi is None and signal_pct is not None and signal_pct < 40:
            # Windows netsh reports quality percent, not calibrated RSSI.
            self._finding(findings, "WIFI-001W", Severity.WARNING, Domain.WIFI,
                "Weak Wi-Fi signal indication", f"Windows reports Wi-Fi signal quality at {signal_pct:.0f}%.",
                "The native Windows signal-quality indication is low. It is useful for A/B comparisons but is not treated as calibrated RSSI.",
                "Compare nearer the AP and validate band/channel, rate, and client/AP geometry.",
                0.82, ["wifi_signal_pct"])
            self._evidence(evidence, "wifi_access", Direction.SUPPORT, 2.8,
                           "Windows Wi-Fi signal-quality indication is weak.", ["wifi_signal_pct"])
        if retry is not None and retry >= 20:
            self._finding(findings, "WIFI-002", Severity.WARNING, Domain.WIFI,
                "High Wi-Fi retry rate", f"Retry rate is {retry:.1f}%.",
                "Contention, interference, hidden-node behavior, weak signal or radio/client issues are plausible.",
                "Inspect channel utilization, neighboring BSSs, RSSI/SNR and retries by band/channel.",
                0.91, ["wifi_retry_pct"])
            self._evidence(evidence, "wifi_access", Direction.SUPPORT, 3.8,
                           "Wi-Fi retry rate is high.", ["wifi_retry_pct"])
        if util is not None and util >= 70:
            self._finding(findings, "WIFI-003", Severity.WARNING, Domain.WIFI,
                "High Wi-Fi channel utilization", f"Channel utilization is {util:.1f}%.",
                "Airtime contention can constrain performance even when RSSI is strong.",
                "Compare alternate channels/bands and identify dominant neighboring transmitters.",
                0.89, ["wifi_channel_util_pct"])
            self._evidence(evidence, "wifi_access", Direction.SUPPORT, 3.4,
                           "Wi-Fi channel utilization is high.", ["wifi_channel_util_pct"])

    def _device(self, m, findings, evidence):
        cpu, mem, temp = m.get("cpu_pct"), m.get("memory_pct"), m.get("temperature_c")
        if cpu is not None and cpu >= 95:
            self._finding(findings, "DEV-001", Severity.WARNING, Domain.DEVICE,
                "Device CPU saturation", f"CPU is {cpu:.1f}%.",
                "Local saturation can distort throughput/latency testing and impair routing/inspection workloads.",
                "Repeat tests after reducing load and inspect process utilization.", 0.88, ["cpu_pct"])
            self._evidence(evidence, "device_resource", Direction.SUPPORT, 3,
                           "CPU is saturated.", ["cpu_pct"])
        if mem is not None and mem >= 95:
            self._finding(findings, "DEV-002", Severity.WARNING, Domain.DEVICE,
                "Device memory pressure", f"Memory is {mem:.1f}%.",
                "Severe memory pressure can destabilize diagnostics or networking services.",
                "Check swapping/OOM events and repeat under normal load.", 0.82, ["memory_pct"])
            self._evidence(evidence, "device_resource", Direction.SUPPORT, 2.5,
                           "Memory utilization is extremely high.", ["memory_pct"])
        if temp is not None and temp >= 90:
            self._finding(findings, "DEV-003", Severity.WARNING, Domain.DEVICE,
                "High device temperature", f"Temperature is {temp:.1f} C.",
                "Thermal throttling or instability may affect repeatability.",
                "Improve airflow and repeat after cooling.", 0.80, ["temperature_c"])
            self._evidence(evidence, "device_resource", Direction.SUPPORT, 2,
                           "Device temperature is high.", ["temperature_c"])

    # ---------------------------------------------------------------------
    # cross-domain expert correlations
    # ---------------------------------------------------------------------

    def _cross_domain(self, m, findings, evidence):
        p = self.profile
        rsrp, sinr = m.get("rsrp"), m.get("sinr")
        dl, ul = m.get("download_mbps"), m.get("upload_mbps")
        loss = m.get("packet_loss_pct")

        # Healthy radio + poor performance -> move suspicion up-stack.
        if None not in (rsrp, sinr, dl) and rsrp >= p.rsrp_good and sinr >= p.sinr_good and dl < p.min_dl_mbps:
            self._finding(findings, "XDOM-001", Severity.WARNING, Domain.CARRIER_CORE,
                "Poor throughput despite healthy RF",
                f"RSRP {rsrp:.1f} dBm, SINR {sinr:.1f} dB, download {dl:.2f} Mbps.",
                "The radio measurements do not adequately explain the performance problem; simple weak coverage is a poor hypothesis.",
                "Prioritize cell loading/scheduling, APN/private-core routing, shaping/policy, MTU, endpoint limits and test-target path.",
                0.96, ["rsrp", "sinr", "download_mbps"])
            self._evidence(evidence, "carrier_or_core_path", Direction.SUPPORT, 4.5,
                           "Good RF with poor throughput points beyond basic coverage.", ["rsrp", "sinr", "download_mbps"])
            self._evidence(evidence, "weak_coverage", Direction.CONTRADICT, 4.8,
                           "Good RSRP/SINR contradicts weak coverage as the primary cause.", ["rsrp", "sinr"])

        # Poor RF + loss + slow speed -> radio-side impairment becomes much stronger.
        if None not in (rsrp, sinr, dl, loss) and rsrp <= p.rsrp_fair and sinr < p.sinr_fair and dl < p.min_dl_mbps and loss >= p.loss_warn_pct:
            self._finding(findings, "XDOM-002", Severity.CRITICAL, Domain.CELLULAR_RF,
                "RF degradation aligns with transport impairment",
                f"RSRP {rsrp:.1f} dBm, SINR {sinr:.1f} dB, loss {loss:.2f}%, download {dl:.2f} Mbps.",
                "Multiple independent symptoms align with a radio-side impairment; this is much stronger than a single RF threshold.",
                "Improve/compare RF conditions first, then rerun identical WAN tests to verify causality.",
                0.97, ["rsrp", "sinr", "packet_loss_pct", "download_mbps"])
            self._evidence(evidence, "weak_coverage", Direction.SUPPORT, 4,
                           "Weak RF coincides with low throughput and packet loss.", ["rsrp", "sinr", "packet_loss_pct", "download_mbps"])

        # Healthy RF + packet loss -> path/core becomes more likely.
        if None not in (rsrp, sinr, loss) and rsrp >= p.rsrp_good and sinr >= p.sinr_good and loss >= p.loss_warn_pct:
            self._finding(findings, "XDOM-003", Severity.WARNING, Domain.WAN,
                "Transport loss is not explained by RF quality",
                f"RF is healthy (RSRP {rsrp:.1f} dBm, SINR {sinr:.1f} dB) while loss is {loss:.2f}%.",
                "Measured radio quality does not support a simple RF-loss explanation.",
                "Localize loss by first hop, carrier/private target, tunnel endpoint and public target.",
                0.93, ["rsrp", "sinr", "packet_loss_pct"])
            self._evidence(evidence, "wan_path", Direction.SUPPORT, 4,
                           "Packet loss occurs despite healthy RF.", ["rsrp", "sinr", "packet_loss_pct"])
            self._evidence(evidence, "weak_coverage", Direction.CONTRADICT, 3.5,
                           "Healthy RF contradicts weak coverage as primary cause.", ["rsrp", "sinr"])

        # Large directional asymmetry should be called out but not overdiagnosed.
        if dl is not None and ul is not None and max(dl, ul) > 0:
            ratio = (max(dl, ul) + 0.01) / (min(dl, ul) + 0.01)
            if ratio >= 8:
                slower = "download" if dl < ul else "upload"
                self._finding(findings, "XDOM-004", Severity.NOTICE, Domain.RAN,
                    "Strong throughput asymmetry", f"Download {dl:.2f} Mbps; upload {ul:.2f} Mbps.",
                    f"The {slower} direction is disproportionately constrained. Scheduling, band/carrier behavior, shaping, RF asymmetry or test-path effects are possible.",
                    "Repeat against alternate targets and record serving-cell/band state during each direction.",
                    0.79, ["download_mbps", "upload_mbps"])

        if m.get("gateway_reachable") is True and m.get("internet_reachable") is False:
            self._finding(findings, "XDOM-005", Severity.CRITICAL, Domain.WAN,
                "Gateway works but external path fails",
                "The gateway is reachable while internet reachability is false.",
                "The local handoff is alive; failure is more likely in routing, APN/core, tunnel policy, upstream firewall or WAN path.",
                "Test carrier/private destinations, inspect routes/policy and identify the first failing hop.",
                0.96, ["gateway_reachable", "internet_reachable"])
            self._evidence(evidence, "carrier_or_core_path", Direction.SUPPORT, 4.5,
                           "Gateway works but external path does not.", ["gateway_reachable", "internet_reachable"])
            self._evidence(evidence, "local_handoff", Direction.CONTRADICT, 3.2,
                           "Reachable gateway argues against a basic local handoff failure.", ["gateway_reachable"])

    # ---------------------------------------------------------------------
    # hypothesis ranking
    # ---------------------------------------------------------------------

    def _rank_hypotheses(self, evidence: Sequence[Evidence]) -> List[Hypothesis]:
        catalog = {
            "weak_coverage": ("Weak / obstructed cellular coverage", Domain.CELLULAR_RF, 0.22),
            "ran_interference_or_load": ("RAN interference, overlap, or cell loading", Domain.RAN, 0.22),
            "registration_failure": ("Cellular registration failure", Domain.RAN, 0.10),
            "apn_or_core": ("APN / packet-core session problem", Domain.CARRIER_CORE, 0.12),
            "carrier_or_core_path": ("Carrier/core/private-WAN path problem", Domain.CARRIER_CORE, 0.20),
            "wan_path": ("WAN transport impairment", Domain.WAN, 0.22),
            "local_handoff": ("Local Ethernet/VLAN/gateway handoff problem", Domain.LOCAL_LAN, 0.18),
            "dns_failure": ("DNS / resolver path problem", Domain.DNS, 0.10),
            "mtu_or_fragmentation": ("MTU / fragmentation / tunnel overhead issue", Domain.MTU, 0.10),
            "throughput_degradation": ("General throughput degradation", Domain.WAN, 0.15),
            "wifi_access": ("Wi-Fi access-layer impairment", Domain.WIFI, 0.12),
            "device_resource": ("Local device resource constraint", Domain.DEVICE, 0.08),
            "device_provisioning": ("SIM/device provisioning problem", Domain.DEVICE, 0.08),
        }
        hs = {hid: Hypothesis(hid, title, domain, prior) for hid, (title, domain, prior) in catalog.items()}
        for ev in evidence:
            if ev.hypothesis_id in hs:
                hs[ev.hypothesis_id].add(ev)

        for h in hs.values():
            if not h.evidence:
                continue
            net = h.support - h.contradiction
            logit_prior = math.log(max(h.prior, 0.01) / max(1 - h.prior, 0.01))
            raw = logit_prior + 0.60 * net
            h.confidence = 1 / (1 + math.exp(-raw))
            if h.confidence >= 0.75:
                h.status = "strong"
            elif h.confidence >= 0.50:
                h.status = "plausible"
            elif h.confidence >= self.profile.minimum_hypothesis_confidence:
                h.status = "possible"
            else:
                h.status = "weak"

        ranked = [h for h in hs.values() if h.evidence]
        ranked.sort(key=lambda h: (h.confidence, h.support), reverse=True)
        return ranked

    # ---------------------------------------------------------------------
    # next-best-test planner
    # ---------------------------------------------------------------------

    def _next_tests(self, m: Mapping[str, Any], hypotheses: Sequence[Hypothesis]) -> List[NextTest]:
        tests: List[NextTest] = []
        top = {h.hypothesis_id for h in hypotheses[:4]}
        uncertain = len(hypotheses) < 2 or (len(hypotheses) >= 2 and abs(hypotheses[0].confidence - hypotheses[1].confidence) < 0.15)

        def add(test_id, title, purpose, action, expected, priority, value, domains):
            if not any(t.test_id == test_id for t in tests):
                tests.append(NextTest(test_id, title, purpose, action, expected, priority, value, list(domains)))

        satellite_only = (
            (str(m.get("satellite_provider") or "").lower() != "" or any(str(k).startswith("starlink_") for k in m))
            and not any(m.get(k) is not None for k in ("rsrp", "rsrq", "sinr", "modem_registered", "lte_band", "nr_band"))
        )
        if not satellite_only and any(m.get(k) is None for k in ("rsrp", "rsrq", "sinr")):
            add("TEST-RF-SNAPSHOT", "Capture a complete radio snapshot",
                "Separate weak coverage from interference/load.",
                "Capture RSRP, RSRQ, SINR, serving cell, LTE/NR bands, PCI, EARFCN/NRARFCN and carrier aggregation state at the same time.",
                "A simultaneous snapshot materially strengthens RF interpretation.",
                1, 0.95, [Domain.CELLULAR_RF, Domain.RAN])

        if "weak_coverage" in top or "ran_interference_or_load" in top:
            add("TEST-RF-A-B", "Perform an RF A/B location test",
                "Determine whether placement/path loss is causal.",
                "Repeat the same test at the current position and at a known-better RF position/antenna configuration while recording cell and band.",
                "RF and performance improving together supports a radio-path cause; RF improvement without performance improvement shifts suspicion upstream.",
                1, 0.93, [Domain.CELLULAR_RF, Domain.RAN])

        if "ran_interference_or_load" in top:
            add("TEST-BAND-CELL", "Compare band / cell behavior",
                "Determine whether the issue follows a particular cell, carrier or band.",
                "Record PCI/cell ID/band and repeat during the issue, another time-of-day, or alternate location/band.",
                "A problem following one cell/band supports RAN conditions rather than endpoint failure.",
                2, 0.89, [Domain.RAN, Domain.SPECTRUM])

        if "carrier_or_core_path" in top or "wan_path" in top or uncertain:
            add("TEST-PATH-STAGES", "Test the path in stages",
                "Localize where latency/loss begins.",
                "Measure default gateway -> carrier/private target -> tunnel/SD-WAN endpoint -> public IP using equal sample counts and payload sizes.",
                "The first stage where latency/loss materially increases identifies the next fault domain.",
                1, 0.97, [Domain.LOCAL_LAN, Domain.CARRIER_CORE, Domain.WAN])

        if "mtu_or_fragmentation" in top or m.get("mtu") is not None:
            add("TEST-PMTU", "Validate path MTU",
                "Detect tunnel/mobile overhead or PMTUD failure.",
                "Run progressively sized packets with fragmentation disabled where supported; compare the cutoff with configured interface MTU.",
                "A repeatable payload-size cutoff indicates an MTU/PMTUD issue.",
                2, 0.83, [Domain.MTU, Domain.WAN])

        if "dns_failure" in top or m.get("dns_success") is False:
            add("TEST-DNS", "Compare DNS and raw IP reachability",
                "Separate resolver failure from transport failure.",
                "Resolve the same hostname using the configured resolver and an approved alternate; separately test the destination by IP.",
                "IP success with DNS failure isolates resolver/split-DNS/forwarding policy.",
                1, 0.95, [Domain.DNS, Domain.WAN])

        if "throughput_degradation" in top or m.get("download_mbps") is not None:
            add("TEST-THROUGHPUT-REPEAT", "Run controlled repeated throughput tests",
                "Avoid diagnosing from one speed-test sample.",
                "Run at least three tests to one nearby target plus one alternate target while capturing RF and latency during each run.",
                "Consistent degradation across targets supports access/path limitation; one-target degradation suggests route/server effects.",
                2, 0.88, [Domain.RAN, Domain.CARRIER_CORE, Domain.WAN])

        if "wifi_access" in top:
            add("TEST-WIFI-WIRED", "Compare Wi-Fi against wired Ethernet",
                "Determine whether the WLAN is the bottleneck.",
                "Repeat the same latency/loss/throughput test over wired Ethernet if available.",
                "Wired-good/Wi-Fi-bad isolates the access layer.",
                1, 0.96, [Domain.WIFI, Domain.LOCAL_LAN])

        tests.sort(key=lambda t: (t.priority, -t.diagnostic_value))
        return tests[:6]

    # ---------------------------------------------------------------------
    # health / summary
    # ---------------------------------------------------------------------

    @staticmethod
    def _health(findings: Sequence[Finding], dq: int) -> int:
        penalty = {Severity.INFO: 0, Severity.NOTICE: 2, Severity.WARNING: 8, Severity.CRITICAL: 20}
        score = 100.0
        for idx, f in enumerate(findings):
            score -= penalty[f.severity] * f.confidence / (1 + 0.08 * idx)
        if dq < 70:
            score = min(score, 85)
        return max(0, min(100, round(score)))

    @staticmethod
    def _status(score: int) -> str:
        if score >= 90:
            return "HEALTHY"
        if score >= 75:
            return "DEGRADED"
        if score >= 50:
            return "IMPAIRED"
        return "CRITICAL"

    def _summary(self, hypotheses, findings, tests, health, status, dq):
        out = [
            f"Overall diagnostic health: {health}/100 ({status}).",
            f"Evidence completeness / input quality: {dq}/100.",
        ]
        if hypotheses:
            top = hypotheses[0]
            if top.confidence >= self.profile.strong_hypothesis_confidence:
                out.append(f"Leading hypothesis: {top.title} ({top.confidence:.0%} confidence-like score).")
            else:
                out.append(f"No root cause is strongly established. Current leader: {top.title} ({top.confidence:.0%}).")
        else:
            out.append("Insufficient evidence to rank a root-cause hypothesis.")
        out.append(f"Findings: {sum(f.severity == Severity.CRITICAL for f in findings)} critical, {sum(f.severity == Severity.WARNING for f in findings)} warning.")
        if tests:
            out.append(f"Best next test: {tests[0].title}.")
        return out


# =============================================================================
# HUMAN-READABLE RENDERER
# =============================================================================

def render_console(report: DiagnosticReport) -> str:
    lines: List[str] = []
    lines += ["=" * 78, "VEILBREAKER DIAGNOSTIC REASONING ENGINE", "=" * 78]
    lines += [f"[+] {x}" for x in report.summary]

    lines += ["", "RANKED HYPOTHESES", "-" * 78]
    if not report.hypotheses:
        lines.append("No hypotheses could be ranked from the supplied evidence.")
    else:
        for idx, h in enumerate(report.hypotheses[:6], 1):
            lines.append(f"{idx:>2}. {h.title:<46} {h.confidence:>6.0%}  [{h.status}]")
            for ev in h.evidence[:3]:
                symbol = "+" if ev.direction == Direction.SUPPORT else "-"
                lines.append(f"      {symbol} {ev.statement}")

    lines += ["", "FINDINGS", "-" * 78]
    if not report.findings:
        lines.append("No material findings.")
    else:
        for f in report.findings:
            lines += [
                f"[{f.severity.value.upper():8}] {f.finding_id}  {f.title}",
                f"  Observation   : {f.observation}",
                f"  Interpretation: {f.interpretation}",
                f"  Action        : {f.recommendation}",
                f"  Confidence    : {f.confidence:.0%}",
                "",
            ]

    lines += ["NEXT BEST TESTS", "-" * 78]
    if not report.next_tests:
        lines.append("No additional test is currently recommended.")
    else:
        for idx, t in enumerate(report.next_tests, 1):
            lines += [
                f"{idx}. {t.title}  [diagnostic value {t.diagnostic_value:.0%}]",
                f"   Why    : {t.purpose}",
                f"   Action : {t.action}",
                f"   Signal : {t.expected_signal}",
                "",
            ]
    return "\n".join(lines)


# =============================================================================
# APPLICATION INFRASTRUCTURE
# =============================================================================

import argparse
import csv
import datetime as _dt
import hashlib
import html
import importlib
import os
import pathlib
import platform
import re
import shlex
import shutil
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Iterable, Iterator, Tuple

APP_NAME = "Veilbreaker"
from . import __version__ as APP_VERSION
from .paths import data_root
SCHEMA_VERSION = 2


def utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def safe_median(values: Sequence[float]) -> Optional[float]:
    vals = [float(x) for x in values if isinstance(x, (int, float)) and math.isfinite(float(x))]
    return statistics.median(vals) if vals else None


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    vals = sorted(float(x) for x in values if isinstance(x, (int, float)) and math.isfinite(float(x)))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    p = clamp(p, 0.0, 1.0)
    idx = p * (len(vals) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return vals[lo]
    frac = idx - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def median_abs_deviation(values: Sequence[float]) -> Optional[float]:
    med = safe_median(values)
    if med is None:
        return None
    dev = [abs(float(x) - med) for x in values if isinstance(x, (int, float))]
    return safe_median(dev)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


@dataclass
class CommandResult:
    argv: List[str]
    returncode: int
    stdout: str
    stderr: str
    elapsed_s: float
    timed_out: bool = False


def run_command(argv: Sequence[str], timeout_s: float = 15.0, env: Optional[Mapping[str, str]] = None) -> CommandResult:
    """Run a command without shell expansion.  This is intentionally boring and safe."""
    started = time.monotonic()
    try:
        kwargs: Dict[str, Any] = {}
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        cp = subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=timeout_s,
            env=dict(os.environ, **(dict(env) if env else {})),
            check=False,
            **kwargs,
        )
        return CommandResult(list(argv), cp.returncode, cp.stdout or "", cp.stderr or "", time.monotonic() - started)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            list(argv), 124,
            (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            (exc.stderr or "") if isinstance(exc.stderr, str) else "",
            time.monotonic() - started,
            timed_out=True,
        )
    except FileNotFoundError as exc:
        return CommandResult(list(argv), 127, "", str(exc), time.monotonic() - started)


# =============================================================================
# CONFIGURATION / SCENARIOS
# =============================================================================

@dataclass
class SDRRange:
    label: str
    min_mhz: float
    max_mhz: float


@dataclass
class AdapterConfig:
    command: Optional[List[str]] = None
    field_map: Dict[str, str] = field(default_factory=dict)
    timeout_s: float = 8.0

@dataclass
class CellularConfig:
    """Cross-platform cellular modem integration.

    backend:
      auto   - native AT first, JSON command fallback if configured
      serial - native read-only AT commands
      json   - external command that emits one JSON object

    driver:
      auto, sierra_em9, quectel_rm5xx, generic_3gpp

    Auto-discovery deliberately probes only ports identified as likely WWAN/modem
    ports unless scan_all_ports is explicitly enabled.  Veilbreaker never changes
    modem bands, RAT preference, firmware, USB composition, APN, or other state.
    Hardware identifiers such as IMEI are not queried unless explicitly enabled.
    """
    enabled: bool = False
    backend: str = "auto"
    driver: str = "auto"
    port: str = "auto"
    baudrate: int = 115200
    timeout_s: float = 2.5
    probe_timeout_s: float = 1.2
    scan_all_ports: bool = False
    capture_neighbors: bool = True
    include_raw_responses: bool = False
    collect_device_identifiers: bool = False
    json_command: Optional[List[str]] = None
    field_map: Dict[str, str] = field(default_factory=dict)


@dataclass
class StarlinkConfig:
    """Read-only Starlink user-terminal telemetry configuration.

    The local dish management service is normally reachable at
    192.168.100.1:9200.  backend=auto prefers the Python starlink_grpc module
    when installed and otherwise falls back to grpcurl reflection.
    """
    enabled: bool = False
    host: str = "192.168.100.1"
    port: int = 9200
    backend: str = "auto"              # auto | python | grpcurl
    timeout_s: float = 7.0
    collect_location: bool = False      # explicit opt-in; location can be sensitive


@dataclass
class SDRConfig:
    enabled: bool = False
    tools_dir: Optional[str] = None
    serial: Optional[str] = None
    ranges: List[SDRRange] = field(default_factory=lambda: [
        SDRRange("sub1g", 600.0, 1000.0),
        SDRRange("midband", 1700.0, 2700.0),
        SDRRange("cband", 3300.0, 4200.0),
        SDRRange("wifi5", 5150.0, 5850.0),
    ])
    bin_width_hz: int = 1_000_000
    sweeps: int = 1
    lna_gain_db: int = 16
    vga_gain_db: int = 20
    amp_enable: bool = False
    antenna_power: bool = False


@dataclass
class AppConfig:
    data_dir: str = field(default_factory=lambda: str(data_root()))
    site_id: str = "default"
    scenario: str = "field_validation"
    public_ping_target: str = "1.1.1.1"
    dns_test_host: str = "example.com"
    path_targets: List[str] = field(default_factory=list)
    baseline_run_count: int = 20
    baseline_min_samples: int = 5
    cellular: CellularConfig = field(default_factory=CellularConfig)
    satellite: AdapterConfig = field(default_factory=AdapterConfig)
    starlink: StarlinkConfig = field(default_factory=StarlinkConfig)
    sdr: SDRConfig = field(default_factory=SDRConfig)
    iperf3_server: Optional[str] = None
    iperf3_port: int = 5201
    report_format: str = "text"

    @property
    def root(self) -> Path:
        return Path(os.path.expanduser(self.data_dir)).resolve()

    @property
    def db_path(self) -> Path:
        return self.root / "veilbreaker.db"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "AppConfig":
        if not isinstance(raw, Mapping):
            raise ValueError("Configuration must be a JSON object")
        for name in ("data_dir", "site_id", "scenario", "public_ping_target", "dns_test_host", "report_format"):
            if name in raw and not isinstance(raw[name], str):
                raise ValueError(f"{name} must be text")
        if "data_dir" in raw and not raw["data_dir"].strip():
            raise ValueError("data_dir must be a nonempty path")
        if raw.get("scenario", "field_validation") not in SCENARIO_OVERRIDES:
            raise ValueError("Unknown diagnostic scenario")
        for section in ("cellular", "satellite", "starlink", "sdr"):
            if section in raw and not isinstance(raw[section], Mapping):
                raise ValueError(f"{section} must be a JSON object")
            values = raw.get(section, {})
            for key in ("enabled", "scan_all_ports", "capture_neighbors", "include_raw_responses", "collect_device_identifiers", "collect_location", "amp_enable", "antenna_power"):
                if key in values and not isinstance(values[key], bool):
                    raise ValueError(f"{section}.{key} must be true or false")
            for key in ("timeout_s", "probe_timeout_s", "baudrate", "bin_width_hz", "sweeps"):
                if key in values and (isinstance(values[key], bool) or not isinstance(values[key], (int, float)) or not math.isfinite(values[key]) or values[key] <= 0):
                    raise ValueError(f"{section}.{key} must be a positive finite number")
        for name in ("baseline_run_count", "baseline_min_samples", "iperf3_port"):
            if name in raw and (type(raw[name]) is not int or raw[name] < 1):
                raise ValueError(f"{name} must be a positive integer")
        if not 1 <= raw.get("iperf3_port", 5201) <= 65535:
            raise ValueError("iperf3_port must be between 1 and 65535")
        c = cls()
        for name in ("data_dir", "site_id", "scenario", "public_ping_target", "dns_test_host",
                     "baseline_run_count", "baseline_min_samples", "iperf3_server", "iperf3_port", "report_format"):
            if name in raw:
                setattr(c, name, raw[name])
        if isinstance(raw.get("path_targets"), list):
            c.path_targets = [str(x) for x in raw["path_targets"]]

        def parse_adapter(obj: Any) -> AdapterConfig:
            if not isinstance(obj, Mapping):
                return AdapterConfig()
            cmd = obj.get("command")
            if isinstance(cmd, str):
                cmd = shlex.split(cmd, posix=(os.name != "nt"))
                if os.name == "nt":
                    cmd = [x[1:-1] if len(x) >= 2 and x[0] == x[-1] == '"' else x for x in cmd]
            elif not isinstance(cmd, list):
                cmd = None
            return AdapterConfig(
                command=[str(x) for x in cmd] if cmd else None,
                field_map={str(k): str(v) for k, v in dict(obj.get("field_map") or {}).items()},
                timeout_s=float(obj.get("timeout_s", 8.0)),
            )

        def parse_cellular(obj: Any) -> CellularConfig:
            if not isinstance(obj, Mapping):
                return CellularConfig()
            cc = CellularConfig()
            for name in ("enabled", "backend", "driver", "port", "baudrate", "timeout_s",
                         "probe_timeout_s", "scan_all_ports", "capture_neighbors", "include_raw_responses",
                         "collect_device_identifiers"):
                if name in obj:
                    setattr(cc, name, obj[name])
            # Backward compatibility: v0.9.2 used cellular.command + field_map.
            cmd = obj.get("json_command", obj.get("command"))
            if isinstance(cmd, str):
                cmd = shlex.split(cmd, posix=(os.name != "nt"))
                if os.name == "nt":
                    cmd = [x[1:-1] if len(x) >= 2 and x[0] == x[-1] == '"' else x for x in cmd]
            elif not isinstance(cmd, list):
                cmd = None
            cc.json_command = [str(x) for x in cmd] if cmd else None
            cc.field_map = {str(k): str(v) for k, v in dict(obj.get("field_map") or {}).items()}
            cc.backend = str(cc.backend).lower().strip()
            if cc.backend not in {"auto", "serial", "json"}:
                cc.backend = "auto"
            cc.driver = str(cc.driver).lower().strip()
            cc.port = str(cc.port).strip() if cc.port is not None else "auto"
            cc.baudrate = int(cc.baudrate)
            cc.timeout_s = float(cc.timeout_s)
            cc.probe_timeout_s = float(cc.probe_timeout_s)
            return cc

        c.cellular = parse_cellular(raw.get("cellular"))
        c.satellite = parse_adapter(raw.get("satellite"))

        star_raw = raw.get("starlink")
        if isinstance(star_raw, Mapping):
            st = StarlinkConfig()
            for name in ("enabled", "host", "port", "backend", "timeout_s", "collect_location"):
                if name in star_raw:
                    setattr(st, name, star_raw[name])
            st.port = int(st.port)
            st.timeout_s = float(st.timeout_s)
            st.backend = str(st.backend).lower().strip()
            if st.backend not in {"auto", "python", "grpcurl"}:
                st.backend = "auto"
            c.starlink = st

        sdr_raw = raw.get("sdr")
        if isinstance(sdr_raw, Mapping):
            s = SDRConfig()
            for name in ("enabled", "tools_dir", "serial", "bin_width_hz", "sweeps", "lna_gain_db", "vga_gain_db", "amp_enable", "antenna_power"):
                if name in sdr_raw:
                    setattr(s, name, sdr_raw[name])
            ranges = []
            for item in sdr_raw.get("ranges", []) or []:
                if isinstance(item, Mapping):
                    ranges.append(SDRRange(str(item.get("label", "range")), float(item["min_mhz"]), float(item["max_mhz"])))
            if ranges:
                s.ranges = ranges
            c.sdr = s
        return c

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def default_config_path() -> Path:
    return data_root() / "config.json"


def load_config(path: Optional[str]) -> AppConfig:
    p = Path(path).expanduser() if path else default_config_path()
    if not p.exists():
        if path:
            raise FileNotFoundError(f"Configuration not found: {p}")
        return AppConfig()
    with p.open("r", encoding="utf-8") as fh:
        return AppConfig.from_dict(json.load(fh))


def save_default_config(path: Path, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Config already exists: {path}")
    cfg = AppConfig()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(cfg.to_dict(), fh, indent=2)
        fh.write("\n")


SCENARIO_OVERRIDES: Dict[str, Dict[str, float]] = {
    "field_validation": {},
    "cellular_fwa": {},
    "private_apn": {},
    "realtime_voice": {
        "latency_warn_ms": 80.0,
        "latency_critical_ms": 180.0,
        "jitter_warn_ms": 20.0,
        "loss_warn_pct": 0.7,
    },
    "remote_telemetry": {
        "latency_warn_ms": 250.0,
        "latency_critical_ms": 600.0,
        "min_dl_mbps": 2.0,
        "min_ul_mbps": 1.0,
        "loss_warn_pct": 2.0,
    },
    "satellite_wan": {
        "latency_warn_ms": 180.0,
        "latency_critical_ms": 500.0,
        "jitter_warn_ms": 50.0,
    },
}


def profile_for_scenario(name: str) -> DiagnosticProfile:
    profile = DiagnosticProfile(name=name)
    for key, value in SCENARIO_OVERRIDES.get(name, {}).items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    return profile


# =============================================================================
# PERSISTENCE: SITE MEMORY, RUNS, CASES
# =============================================================================

class VeilbreakerStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.db.close()

    def _init_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                ts_utc TEXT NOT NULL,
                site_id TEXT NOT NULL,
                scenario TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                report_json TEXT NOT NULL,
                artifact_dir TEXT,
                note TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_runs_site_time ON runs(site_id, ts_utc DESC);
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                created_utc TEXT NOT NULL,
                site_id TEXT,
                source_run_id TEXT,
                scenario TEXT,
                hypothesis_id TEXT,
                cause TEXT NOT NULL,
                resolution TEXT,
                signature_json TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                confirmed INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_cases_site ON cases(site_id);
            CREATE TABLE IF NOT EXISTS case_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                action TEXT NOT NULL,
                details_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_case_events_case ON case_events(case_id, event_id);
            """
        )
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        self.db.commit()

    def save_run(self, run_id: str, site_id: str, scenario: str, metrics: Mapping[str, Any], report: DiagnosticReport,
                 artifact_dir: Optional[str] = None, note: Optional[str] = None) -> None:
        self.db.execute(
            """INSERT OR REPLACE INTO runs
               (run_id, ts_utc, site_id, scenario, metrics_json, report_json, artifact_dir, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, utcnow_iso(), site_id, scenario, json.dumps(dict(metrics), default=str), report.to_json(), artifact_dir, note),
        )
        self.db.commit()

    def get_run(self, run_id: str) -> Optional[sqlite3.Row]:
        return self.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()

    def list_runs(self, site_id: Optional[str] = None, limit: int = 20) -> List[sqlite3.Row]:
        if site_id:
            return list(self.db.execute("SELECT * FROM runs WHERE site_id=? ORDER BY ts_utc DESC LIMIT ?", (site_id, limit)))
        return list(self.db.execute("SELECT * FROM runs ORDER BY ts_utc DESC LIMIT ?", (limit,)))

    def search_runs(self, query="", limit=200, offset=0):
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("Invalid history page")
        # Literal substring matching: %, _ and quotes are not SQL operators.
        where = "instr(lower(run_id || ' ' || ts_utc || ' ' || site_id || ' ' || scenario || ' ' || coalesce(note, '')), lower(?)) > 0"
        total = self.db.execute("SELECT count(*) FROM runs WHERE " + where, (query.strip(),)).fetchone()[0]
        rows = self.db.execute("SELECT * FROM runs WHERE " + where + " ORDER BY ts_utc DESC, run_id DESC LIMIT ? OFFSET ?",
                               (query.strip(), limit, offset)).fetchall()
        return rows, total

    def preceding_run(self, row):
        return self.db.execute(
            "SELECT * FROM runs WHERE site_id=? AND scenario=? AND (ts_utc < ? OR (ts_utc = ? AND run_id < ?)) ORDER BY ts_utc DESC, run_id DESC LIMIT 1",
            (row["site_id"], row["scenario"], row["ts_utc"], row["ts_utc"], row["run_id"])).fetchone()

    def recent_metric_sets(self, site_id: str, scenario: Optional[str], limit: int) -> List[Dict[str, Any]]:
        if scenario:
            rows = self.db.execute(
                "SELECT metrics_json FROM runs WHERE site_id=? AND scenario=? ORDER BY ts_utc DESC LIMIT ?",
                (site_id, scenario, limit),
            )
        else:
            rows = self.db.execute(
                "SELECT metrics_json FROM runs WHERE site_id=? ORDER BY ts_utc DESC LIMIT ?",
                (site_id, limit),
            )
        out = []
        for row in rows:
            try:
                out.append(json.loads(row[0]))
            except Exception:
                pass
        return out

    def baseline(self, site_id: str, scenario: str, limit: int = 20, min_samples: int = 5) -> Dict[str, Dict[str, float]]:
        rows = self.recent_metric_sets(site_id, scenario, limit)
        buckets: Dict[str, List[float]] = defaultdict(list)
        for m in rows:
            for k, v in m.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)):
                    buckets[k].append(float(v))
        result: Dict[str, Dict[str, float]] = {}
        for k, vals in buckets.items():
            if len(vals) < min_samples:
                continue
            med = safe_median(vals)
            mad = median_abs_deviation(vals)
            result[k] = {
                "n": float(len(vals)),
                "median": float(med),
                "mad": float(mad or 0.0),
                "p10": float(percentile(vals, 0.10)),
                "p90": float(percentile(vals, 0.90)),
                "min": min(vals),
                "max": max(vals),
            }
        return result

    @staticmethod
    def case_signature(metrics: Mapping[str, Any]) -> Dict[str, Any]:
        keep = [
            "technology", "lte_band", "nr_band", "carrier", "apn",
            "rsrp", "rsrq", "sinr", "latency_ms", "gateway_latency_ms",
            "jitter_ms", "packet_loss_pct", "download_mbps", "upload_mbps",
            "mtu", "wifi_rssi_dbm", "wifi_retry_pct", "wifi_channel_util_pct",
            "satellite_snr_db", "satellite_latency_ms", "satellite_packet_loss_pct",
        ]
        sig = {k: metrics[k] for k in keep if metrics.get(k) is not None}
        for k, v in metrics.items():
            if k.startswith("sdr_") and (k.endswith("_median_db") or k.endswith("_occupancy_pct") or k.endswith("_peak_excess_db")):
                sig[k] = v
        return sig

    def add_case(self, source_run_id: str, cause: str, resolution: str = "", hypothesis_id: Optional[str] = None,
                 tags: Optional[List[str]] = None) -> str:
        if not isinstance(cause, str) or not cause.strip() or len(cause) > 2000:
            raise ValueError("Describe the confirmed cause using 1–2000 characters")
        if not isinstance(resolution, str) or len(resolution) > 4000:
            raise ValueError("Resolution must be text up to 4000 characters")
        cause = cause.strip()
        row = self.get_run(source_run_id)
        if not row:
            raise KeyError(f"Unknown run id: {source_run_id}")
        metrics = json.loads(row["metrics_json"])
        case_id = "case-" + uuid.uuid4().hex[:10]
        with self.db:
            self.db.execute(
                """INSERT INTO cases(case_id,created_utc,site_id,source_run_id,scenario,hypothesis_id,cause,resolution,signature_json,tags_json,confirmed)
                   VALUES(?,?,?,?,?,?,?,?,?,?,1)""",
                (case_id, utcnow_iso(), row["site_id"], source_run_id, row["scenario"], hypothesis_id, cause, resolution,
                 json.dumps(self.case_signature(metrics)), json.dumps(tags or [])),
            )
            self.db.execute("INSERT INTO case_events(case_id,timestamp_utc,action,details_json) VALUES(?,?,?,?)",
                            (case_id, utcnow_iso(), "confirmed", json.dumps({"cause": cause, "resolution": resolution})))
        return case_id

    def list_cases(self, limit: int = 50) -> List[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM cases ORDER BY created_utc DESC LIMIT ?", (limit,)))

    def search_cases(self, query="", state="All states", limit=200, offset=0):
        if state not in ("All states", "Confirmed", "Withdrawn") or not 1 <= limit <= 200 or offset < 0:
            raise ValueError("Invalid case search")
        where = "instr(lower(case_id || ' ' || coalesce(site_id,'') || ' ' || coalesce(source_run_id,'') || ' ' || cause || ' ' || coalesce(resolution,'')),lower(?)) > 0"
        params = [query.strip()]
        if state != "All states":
            where += " AND confirmed=?"
            params.append(1 if state == "Confirmed" else 0)
        total = self.db.execute("SELECT count(*) FROM cases WHERE " + where, params).fetchone()[0]
        rows = self.db.execute("SELECT * FROM cases WHERE " + where + " ORDER BY created_utc DESC, case_id DESC LIMIT ? OFFSET ?", [*params,limit,offset]).fetchall()
        return rows,total

    def case_record(self, case_id):
        row = self.db.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            raise KeyError("Unknown case")
        case = dict(row)
        case["signature"] = json.loads(case.pop("signature_json"))
        case["tags"] = json.loads(case.pop("tags_json"))
        events = []
        for event in self.db.execute("SELECT * FROM case_events WHERE case_id=? ORDER BY event_id", (case_id,)):
            item = dict(event)
            item["details"] = json.loads(item.pop("details_json"))
            events.append(item)
        source = self.get_run(case["source_run_id"])
        return {"schema_version": 1, "case": case, "events": events,
                "source": {k: source[k] for k in ("run_id","ts_utc","site_id","scenario")} if source else None,
                "history_note": "Events recorded since case audit support was introduced; earlier changes are unavailable. This is an operator record, not independent proof of cause."}

    def withdraw_case(self, case_id, reason=""):
        if not isinstance(reason,str) or len(reason) > 2000:
            raise ValueError("Withdrawal reason must be text up to 2000 characters")
        with self.db:
            row = self.db.execute("SELECT confirmed FROM cases WHERE case_id=?",(case_id,)).fetchone()
            if row is None:
                raise KeyError("Unknown case")
            if not row["confirmed"]:
                return False
            self.db.execute("UPDATE cases SET confirmed=0 WHERE case_id=?", (case_id,))
            self.db.execute("INSERT INTO case_events(case_id,timestamp_utc,action,details_json) VALUES(?,?,?,?)",
                            (case_id,utcnow_iso(),"withdrawn",json.dumps({"reason":reason.strip()})))
        return True

    @staticmethod
    def _case_similarity(a: Mapping[str, Any], b: Mapping[str, Any]) -> Tuple[float, int]:
        scales = {
            "rsrp": 15.0, "rsrq": 8.0, "sinr": 15.0,
            "latency_ms": 200.0, "gateway_latency_ms": 100.0,
            "jitter_ms": 50.0, "packet_loss_pct": 5.0,
            "download_mbps": 100.0, "upload_mbps": 50.0,
            "mtu": 100.0, "wifi_rssi_dbm": 15.0,
            "wifi_retry_pct": 25.0, "wifi_channel_util_pct": 40.0,
            "satellite_snr_db": 10.0, "satellite_latency_ms": 250.0,
            "satellite_packet_loss_pct": 5.0,
        }
        distances: List[float] = []
        categorical = {"technology", "lte_band", "nr_band", "carrier", "apn"}
        for k in set(a) & set(b):
            av, bv = a[k], b[k]
            if k in categorical:
                distances.append(0.0 if str(av).lower() == str(bv).lower() else 1.0)
            elif isinstance(av, (int, float)) and isinstance(bv, (int, float)):
                scale = scales.get(k, 20.0 if k.startswith("sdr_") else None)
                if scale:
                    # Throughput differences are more naturally relative at high rates.
                    if k in {"download_mbps", "upload_mbps"}:
                        av2, bv2 = math.log1p(max(0.0, float(av))), math.log1p(max(0.0, float(bv)))
                        distances.append(min(2.0, abs(av2 - bv2) / math.log(3.0)))
                    else:
                        distances.append(min(2.0, abs(float(av) - float(bv)) / scale))
        n = len(distances)
        if n < 3:
            return 0.0, n
        mean_d = sum(distances) / n
        return math.exp(-1.6 * mean_d), n

    def match_cases(self, metrics: Mapping[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        sig = self.case_signature(metrics)
        matches = []
        for row in self.db.execute("SELECT * FROM cases WHERE confirmed=1"):
            try:
                other = json.loads(row["signature_json"])
            except Exception:
                continue
            score, compared = self._case_similarity(sig, other)
            if compared >= 3 and score >= 0.45:
                matches.append({
                    "case_id": row["case_id"],
                    "similarity": score,
                    "compared_features": compared,
                    "cause": row["cause"],
                    "resolution": row["resolution"],
                    "hypothesis_id": row["hypothesis_id"],
                    "source_run_id": row["source_run_id"],
                })
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches[:limit]


# =============================================================================
# COLLECTORS
# =============================================================================

class Collector:
    name = "collector"

    def available(self) -> bool:
        return True

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        return {}, []


class SystemCollector(Collector):
    name = "system"

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        m: Dict[str, Any] = {
            "host_name": socket.gethostname(),
            "host_os": platform.system(),
            "host_release": platform.release(),
            "host_arch": platform.machine(),
        }
        notes: List[str] = []
        try:
            load1 = os.getloadavg()[0]
            cpus = os.cpu_count() or 1
            m["load1_per_cpu"] = round(load1 / cpus, 3)
        except Exception:
            pass
        try:
            meminfo = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meminfo[k] = int(v.strip().split()[0])
            total = meminfo.get("MemTotal")
            avail = meminfo.get("MemAvailable")
            if total and avail is not None:
                m["memory_pct"] = round((1 - avail / total) * 100, 1)
        except Exception:
            pass
        try:
            temps = []
            for p in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
                try:
                    raw = float(p.read_text().strip())
                    temps.append(raw / 1000.0 if raw > 1000 else raw)
                except Exception:
                    pass
            if temps:
                m["temperature_c"] = round(max(temps), 1)
        except Exception:
            pass
        try:
            up = float(Path("/proc/uptime").read_text().split()[0])
            m["host_uptime_s"] = round(up)
        except Exception:
            pass

        # Native Windows fallbacks using only the Python standard library.
        if platform.system().lower() == "windows":
            try:
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                state = MEMORYSTATUSEX()
                state.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
                    m["memory_pct"] = float(state.dwMemoryLoad)
                    m["memory_total_bytes"] = int(state.ullTotalPhys)
                    m["memory_available_bytes"] = int(state.ullAvailPhys)
                ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
                m["host_uptime_s"] = round(ctypes.windll.kernel32.GetTickCount64() / 1000.0)
            except Exception as exc:
                notes.append(f"Windows system metrics partially unavailable: {exc}")
        return m, notes


class LinuxNetworkCollector(Collector):
    name = "linux_network"

    def available(self) -> bool:
        return command_exists("ip")

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        m: Dict[str, Any] = {}
        notes: List[str] = []
        if not self.available():
            return m, ["ip command not found"]
        result = run_command(["ip", "-j", "route", "show", "default"], 3)
        if result.returncode == 0:
            try:
                routes = json.loads(result.stdout or "[]")
                if routes:
                    r = routes[0]
                    if r.get("gateway"):
                        m["gateway_ip"] = r["gateway"]
                    if r.get("dev"):
                        m["interface"] = r["dev"]
            except Exception as exc:
                notes.append(f"Could not parse default route: {exc}")
        iface = m.get("interface")
        if iface:
            link = run_command(["ip", "-j", "link", "show", "dev", str(iface)], 3)
            if link.returncode == 0:
                try:
                    arr = json.loads(link.stdout or "[]")
                    if arr:
                        m["interface_state"] = arr[0].get("operstate")
                        if arr[0].get("mtu") is not None:
                            m["mtu"] = int(arr[0]["mtu"])
                except Exception:
                    pass
            addr = run_command(["ip", "-j", "addr", "show", "dev", str(iface)], 3)
            if addr.returncode == 0:
                try:
                    arr = json.loads(addr.stdout or "[]")
                    infos = arr[0].get("addr_info", []) if arr else []
                    v4 = [x for x in infos if x.get("family") == "inet"]
                    v6 = [x for x in infos if x.get("family") == "inet6" and x.get("scope") == "global"]
                    m["ipv4_present"] = bool(v4)
                    m["ipv6_present"] = bool(v6)
                    if v4:
                        m["local_ipv4"] = v4[0].get("local")
                except Exception:
                    pass
        return m, notes


class LinuxWiFiCollector(Collector):
    name = "wifi"

    def available(self) -> bool:
        return command_exists("iw")

    @staticmethod
    def _discover_iface() -> Optional[str]:
        res = run_command(["iw", "dev"], 3)
        if res.returncode != 0:
            return None
        m = re.search(r"^\s*Interface\s+(\S+)", res.stdout, re.M)
        return m.group(1) if m else None

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        if not self.available():
            return {}, ["iw not installed"]
        iface = self._discover_iface()
        if not iface:
            return {}, []
        res = run_command(["iw", "dev", iface, "link"], 3)
        if res.returncode != 0 or "Not connected" in res.stdout:
            return {"wifi_interface": iface, "wifi_connected": False}, []
        out = res.stdout
        m: Dict[str, Any] = {"wifi_interface": iface, "wifi_connected": True}
        patterns = {
            "wifi_ssid": r"SSID:\s*(.+)$",
            "wifi_freq_mhz": r"freq:\s*(\d+)",
            "wifi_rssi_dbm": r"signal:\s*(-?\d+(?:\.\d+)?)\s*dBm",
            "wifi_tx_bitrate_mbps": r"tx bitrate:\s*(\d+(?:\.\d+)?)\s*MBit/s",
            "wifi_rx_bitrate_mbps": r"rx bitrate:\s*(\d+(?:\.\d+)?)\s*MBit/s",
        }
        for key, pat in patterns.items():
            mm = re.search(pat, out, re.M)
            if mm:
                value: Any = mm.group(1).strip()
                if key != "wifi_ssid":
                    try:
                        value = float(value)
                    except Exception:
                        pass
                m[key] = value
        return m, []


def _powershell_executable() -> Optional[str]:
    """Return an available PowerShell executable without requiring PowerShell 7."""
    for candidate in ("powershell.exe", "pwsh.exe", "powershell", "pwsh"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def _powershell_json(script: str, timeout_s: float = 8.0) -> Tuple[Optional[Any], Optional[str]]:
    exe = _powershell_executable()
    if not exe:
        return None, "PowerShell not found"
    res = run_command([exe, "-NoProfile", "-NonInteractive", "-Command", script], timeout_s)
    if res.returncode != 0:
        return None, (res.stderr.strip() or res.stdout.strip() or f"PowerShell rc={res.returncode}")
    text = res.stdout.strip()
    if not text:
        return None, "PowerShell returned no data"
    try:
        return json.loads(text), None
    except Exception as exc:
        return None, f"PowerShell JSON parse failed: {exc}: {text[:240]}"


class WindowsNetworkCollector(Collector):
    """Native Windows default-route/interface collector."""

    name = "windows_network"

    def available(self) -> bool:
        return platform.system().lower() == "windows"

    @staticmethod
    def _parse_route_print(text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        candidates = []
        for line in text.splitlines():
            mm = re.match(
                r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s*$",
                line,
            )
            if mm:
                candidates.append((int(mm.group(3)), mm.group(1), mm.group(2)))
        if candidates:
            metric, gateway, local = sorted(candidates)[0]
            out["gateway_ip"] = gateway
            out["local_ipv4"] = local
            out["ipv4_present"] = True
            out["route_metric"] = metric
        return out

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        m: Dict[str, Any] = {}
        notes: List[str] = []
        if not self.available():
            return m, ["Windows network collector selected on a non-Windows host"]

        script = r"""$ErrorActionPreference = 'Stop'
$route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' |
    Where-Object { $_.NextHop -and $_.NextHop -ne '0.0.0.0' } |
    Sort-Object RouteMetric | Select-Object -First 1
if ($null -eq $route) { throw 'No active IPv4 default route found' }
$cfg = Get-NetIPConfiguration -InterfaceIndex $route.InterfaceIndex
$if4 = Get-NetIPInterface -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -First 1
$adapter = Get-NetAdapter -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue
$v4 = @($cfg.IPv4Address | ForEach-Object { $_.IPAddress })
$v6 = @($cfg.IPv6Address | Where-Object { $_.IPAddress -notlike 'fe80:*' } | ForEach-Object { $_.IPAddress })
[pscustomobject]@{
  gateway_ip       = [string]$route.NextHop
  interface        = [string]$cfg.InterfaceAlias
  interface_index  = [int]$route.InterfaceIndex
  interface_state  = if ($adapter) { [string]$adapter.Status } else { [string]$if4.ConnectionState }
  mtu              = if ($if4) { [int]$if4.NlMtu } else { $null }
  local_ipv4       = if ($v4.Count -gt 0) { [string]$v4[0] } else { $null }
  ipv4_present     = [bool]($v4.Count -gt 0)
  ipv6_present     = [bool]($v6.Count -gt 0)
  route_metric     = [int]$route.RouteMetric
  interface_metric = if ($if4) { [int]$if4.InterfaceMetric } else { $null }
  link_speed       = if ($adapter) { [string]$adapter.LinkSpeed } else { $null }
  adapter_name     = if ($adapter) { [string]$adapter.Name } else { $null }
  adapter_desc     = if ($adapter) { [string]$adapter.InterfaceDescription } else { $null }
} | ConvertTo-Json -Compress -Depth 3"""
        obj, err = _powershell_json(script, 8.0)
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                if v is not None and v != "":
                    m[str(k)] = v
        elif err:
            notes.append(f"NetTCPIP query failed: {err}")

        if not m.get("gateway_ip") and command_exists("route"):
            res = run_command(["route", "print", "-4"], 5)
            if res.returncode == 0:
                m.update(self._parse_route_print(res.stdout))
            elif res.stderr.strip():
                notes.append(f"route fallback failed: {res.stderr.strip()}")

        return m, notes


class WindowsWiFiCollector(Collector):
    name = "windows_wifi"

    def available(self) -> bool:
        return platform.system().lower() == "windows" and command_exists("netsh")

    @staticmethod
    def _parse_interfaces(text: str) -> Dict[str, Any]:
        values: Dict[str, str] = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = re.sub(r"\s+", " ", key.strip().lower())
            value = value.strip()
            if key and value and key not in values:
                values[key] = value
        if not values:
            return {}

        state = values.get("state", "").lower()
        out: Dict[str, Any] = {
            "wifi_interface": values.get("name"),
            "wifi_connected": state == "connected",
        }
        if state != "connected":
            return {k: v for k, v in out.items() if v is not None}

        mapping = {
            "ssid": "wifi_ssid",
            "bssid": "wifi_bssid",
            "radio type": "wifi_radio_type",
            "authentication": "wifi_authentication",
            "cipher": "wifi_cipher",
        }
        for src, dst in mapping.items():
            if src in values:
                out[dst] = values[src]

        numeric = {
            "channel": ("wifi_channel", int),
            "receive rate (mbps)": ("wifi_rx_bitrate_mbps", float),
            "transmit rate (mbps)": ("wifi_tx_bitrate_mbps", float),
        }
        for src, (dst, converter) in numeric.items():
            if src in values:
                try:
                    out[dst] = converter(values[src])
                except Exception:
                    pass

        if "signal" in values:
            mm = re.search(r"(\d+(?:\.\d+)?)\s*%", values["signal"])
            if mm:
                out["wifi_signal_pct"] = float(mm.group(1))
                out["wifi_signal_source"] = "windows_netsh_quality_percent"
        return {k: v for k, v in out.items() if v is not None}

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        if not self.available():
            return {}, ["netsh WLAN interface query unavailable"]
        res = run_command(["netsh", "wlan", "show", "interfaces"], 5)
        if res.returncode != 0:
            return {}, [f"netsh wlan failed: {res.stderr.strip() or res.stdout.strip()}"]
        return self._parse_interfaces(res.stdout), []


class GenericNetworkCollector(Collector):
    name = "generic_network"

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        return {}, [f"No native network collector implemented for {platform.system()}"]


def make_network_collector() -> Collector:
    system = platform.system().lower()
    if system == "windows":
        return WindowsNetworkCollector()
    if system == "linux":
        return LinuxNetworkCollector()
    return GenericNetworkCollector()


def make_wifi_collector() -> Collector:
    if platform.system().lower() == "windows":
        return WindowsWiFiCollector()
    return LinuxWiFiCollector()


class GPSDCollector(Collector):
    name = "gpsd"

    def __init__(self, host: str = "127.0.0.1", port: int = 2947, timeout_s: float = 1.5):
        self.host, self.port, self.timeout_s = host, port, timeout_s

    def available(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=0.25):
                return True
        except OSError:
            return False

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        m: Dict[str, Any] = {}
        if not self.available():
            return m, []
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
            sock.settimeout(self.timeout_s)
            sock.sendall(b'?WATCH={"enable":true,"json":true};\n')
            buf = b""
            deadline = time.monotonic() + self.timeout_s
            while time.monotonic() < deadline:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        obj = json.loads(line.decode("utf-8", errors="replace"))
                    except Exception:
                        continue
                    if obj.get("class") == "TPV":
                        mode = int(obj.get("mode", 0) or 0)
                        m["gps_fix"] = mode >= 2
                        m["gps_mode"] = mode
                        mapping = {
                            "lat": "gps_lat", "lon": "gps_lon", "altMSL": "gps_alt_m",
                            "alt": "gps_alt_m", "speed": "gps_speed_mps", "track": "gps_track_deg",
                            "epx": "gps_epx_m", "epy": "gps_epy_m", "epv": "gps_epv_m",
                        }
                        for src, dst in mapping.items():
                            if src in obj and dst not in m:
                                m[dst] = obj[src]
                        sock.close()
                        return m, []
            sock.close()
        except Exception as exc:
            return m, [f"gpsd read failed: {exc}"]
        return m, []


class JSONCommandAdapter(Collector):
    """Vendor-neutral modem/satellite bridge.

    The configured command must print one JSON object to stdout.  A field_map can
    translate vendor names into Veilbreaker canonical names.  This makes the core
    application independent of the modem chosen later.
    """

    def __init__(self, name: str, config: AdapterConfig, prefix: str = ""):
        self.name = name
        self.config = config
        self.prefix = prefix

    def available(self) -> bool:
        return bool(self.config.command and command_exists(self.config.command[0]))

    @staticmethod
    def _flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, Mapping):
                    out.update(JSONCommandAdapter._flatten(v, key))
                else:
                    out[key] = v
        return out

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        if not self.config.command:
            return {}, []
        if not self.available():
            return {}, [f"{self.name} adapter command unavailable: {self.config.command[0]}"]
        result = run_command(self.config.command, self.config.timeout_s)
        if result.returncode != 0:
            return {}, [f"{self.name} adapter failed rc={result.returncode}: {result.stderr.strip()}"]
        try:
            raw = json.loads(result.stdout)
        except Exception as exc:
            return {}, [f"{self.name} adapter did not return valid JSON: {exc}"]
        flat = self._flatten(raw)
        out: Dict[str, Any] = {}
        field_map = self.config.field_map or {}
        for source_key, value in flat.items():
            target = field_map.get(source_key)
            if target:
                out[target] = value
            elif "." not in source_key:
                out[(self.prefix + source_key) if self.prefix else source_key] = value
        return out, []


# =============================================================================
# NATIVE CELLULAR MODEM STACK
# =============================================================================

@dataclass
class SerialPortInfo:
    device: str
    description: str = ""
    manufacturer: str = ""
    hwid: str = ""
    vid: Optional[int] = None
    pid: Optional[int] = None
    likely_modem: bool = False
    source: str = "unknown"


_MODEM_VIDS = {
    0x1199: "Sierra Wireless / Semtech",
    0x2C7C: "Quectel",
    0x1E0E: "SIMCom",
    0x1BC7: "Telit",
    0x2CB7: "Fibocom",
    0x1546: "u-blox",
}
_MODEM_HINTS = (
    "sierra", "airprime", "quectel", "simcom", "telit", "fibocom", "cinterion",
    "thales", "u-blox", "wwan", "mobile broadband", "cellular", "modem", "at port",
    "diagnostic port", "dm port",
)


def _serial_backend_available() -> bool:
    try:
        import serial  # type: ignore
        return True
    except Exception:
        return os.name != "nt"  # Linux/POSIX stdlib fallback exists below.


def _pyserial_available() -> bool:
    try:
        import serial  # type: ignore
        import serial.tools.list_ports  # type: ignore
        return True
    except Exception:
        return False


def _modemmanager_at_ports() -> List[SerialPortInfo]:
    """Use ModemManager as a conservative source of known AT-capable tty ports."""
    if platform.system().lower() != "linux" or not command_exists("mmcli"):
        return []
    res = run_command(["mmcli", "-L"], 4.0)
    if res.returncode != 0:
        return []
    indexes = re.findall(r"/Modem/(\d+)", res.stdout)
    out: List[SerialPortInfo] = []
    for idx in indexes[:8]:
        detail = run_command(["mmcli", "-m", idx], 4.0)
        if detail.returncode != 0:
            continue
        # ModemManager prints e.g. ttyUSB2 (at), ttyUSB3 (at)
        for name in re.findall(r"([A-Za-z0-9._-]+)\s*\(at(?:-primary|-secondary)?\)", detail.stdout, re.I):
            dev = name if name.startswith("/") else "/dev/" + name
            out.append(SerialPortInfo(dev, "ModemManager AT port", "", "", None, None, True, "mmcli"))
    dedup: Dict[str, SerialPortInfo] = {p.device: p for p in out}
    return list(dedup.values())


def list_serial_ports(include_unlikely: bool = True) -> List[SerialPortInfo]:
    ports: Dict[str, SerialPortInfo] = {}
    try:
        import serial.tools.list_ports  # type: ignore
        for p in serial.tools.list_ports.comports():
            text = " ".join(str(x or "") for x in (p.description, p.manufacturer, p.hwid)).lower()
            likely = (p.vid in _MODEM_VIDS) or any(h in text for h in _MODEM_HINTS)
            info = SerialPortInfo(
                device=str(p.device), description=str(p.description or ""),
                manufacturer=str(p.manufacturer or ""), hwid=str(p.hwid or ""),
                vid=p.vid, pid=p.pid, likely_modem=likely, source="pyserial",
            )
            ports[info.device] = info
    except Exception:
        pass

    for p in _modemmanager_at_ports():
        ports.setdefault(p.device, p)

    system = platform.system().lower()
    if not ports and system == "windows":
        ps = _powershell_executable()
        if ps:
            script = "$ErrorActionPreference='SilentlyContinue'; Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name,Description,PNPDeviceID | ConvertTo-Json -Compress"
            res = run_command([ps, "-NoProfile", "-Command", script], 5.0)
            if res.returncode == 0 and res.stdout.strip():
                try:
                    obj = json.loads(res.stdout)
                    rows = obj if isinstance(obj, list) else [obj]
                    for row in rows:
                        dev = str(row.get("DeviceID") or "").strip()
                        if not dev:
                            continue
                        desc = str(row.get("Name") or row.get("Description") or "")
                        hwid = str(row.get("PNPDeviceID") or "")
                        text = (desc + " " + hwid).lower()
                        likely = any(h in text for h in _MODEM_HINTS)
                        ports[dev] = SerialPortInfo(dev, desc, "", hwid, None, None, likely, "powershell")
                except Exception:
                    pass

    if system == "linux":
        for pattern in ("ttyUSB*", "ttyACM*", "ttyWWAN*", "wwan*at*"):
            for path in Path("/dev").glob(pattern):
                dev = str(path)
                ports.setdefault(dev, SerialPortInfo(dev, "Linux serial device", source="filesystem", likely_modem=False))

    values = sorted(ports.values(), key=lambda p: (not p.likely_modem, p.device))
    return values if include_unlikely else [p for p in values if p.likely_modem]


class ATSerialSession:
    """Small read-only AT transport.  Uses pyserial when available.

    On POSIX hosts a minimal termios implementation keeps the application usable
    without third-party dependencies.  Windows native AT access requires pyserial.
    """
    def __init__(self, port: str, baudrate: int = 115200, timeout_s: float = 2.5):
        self.port = port
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self._ser = None
        self._fd = None

    def __enter__(self):
        try:
            import serial  # type: ignore
            self._ser = serial.Serial(
                self.port, self.baudrate, timeout=0.10, write_timeout=max(1.0, self.timeout_s)
            )
            return self
        except ImportError:
            if os.name == "nt":
                raise RuntimeError("Native AT access on Windows requires pyserial: py -m pip install pyserial")
        except TypeError:
            # Older pyserial versions do not accept exclusive=None.
            import serial  # type: ignore
            self._ser = serial.Serial(self.port, self.baudrate, timeout=0.10, write_timeout=max(1.0, self.timeout_s))
            return self

        import termios, fcntl
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK
        self._fd = os.open(self.port, flags)
        attrs = termios.tcgetattr(self._fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
        attrs[3] = 0
        speed = getattr(termios, f"B{self.baudrate}", termios.B115200)
        attrs[4] = speed
        attrs[5] = speed
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 1
        termios.tcsetattr(self._fd, termios.TCSANOW, attrs)
        termios.tcflush(self._fd, termios.TCIOFLUSH)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._ser is not None:
                self._ser.close()
        finally:
            if self._fd is not None:
                os.close(self._fd)
        return False

    def _write(self, data: bytes) -> None:
        if self._ser is not None:
            self._ser.reset_input_buffer()
            self._ser.write(data)
            self._ser.flush()
            return
        import termios
        termios.tcflush(self._fd, termios.TCIFLUSH)
        os.write(self._fd, data)

    def _read_some(self) -> bytes:
        if self._ser is not None:
            n = max(1, int(getattr(self._ser, "in_waiting", 0) or 1))
            return self._ser.read(n)
        import select
        ready, _, _ = select.select([self._fd], [], [], 0.10)
        if not ready:
            return b""
        try:
            return os.read(self._fd, 4096)
        except BlockingIOError:
            return b""

    def command(self, command: str, timeout_s: Optional[float] = None) -> str:
        if not command.upper().startswith("AT"):
            raise ValueError("Only AT commands are permitted by the native modem transport")
        self._write((command.rstrip("\r\n") + "\r").encode("ascii", errors="ignore"))
        deadline = time.monotonic() + float(timeout_s or self.timeout_s)
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._read_some()
            if chunk:
                buf.extend(chunk)
                text = buf.decode("utf-8", errors="replace")
                if re.search(r"(?:^|[\r\n])(OK|ERROR|\+CME ERROR:.*|\+CMS ERROR:.*)(?:[\r\n]|$)", text, re.I):
                    break
            else:
                time.sleep(0.02)
        return buf.decode("utf-8", errors="replace").strip()


def _at_lines(response: str, command: Optional[str] = None) -> List[str]:
    out = []
    cmd = (command or "").strip().upper()
    for raw in response.replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if cmd and line.upper() == cmd:
            continue
        if line.upper() in {"OK", "ERROR"} or line.upper().startswith(("+CME ERROR", "+CMS ERROR")):
            continue
        out.append(line)
    return out


def _csv_fields(line: str, prefix: Optional[str] = None) -> List[str]:
    if prefix and line.upper().startswith(prefix.upper()):
        line = line[len(prefix):]
    line = line.strip().lstrip(":").strip()
    try:
        return [x.strip() for x in next(csv.reader([line], skipinitialspace=True))]
    except Exception:
        return [x.strip().strip('"') for x in line.split(",")]


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace("—", "").replace("---", "")
    if text in {"", "-", "--", "-32768", "65535"}:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _intnum(value: Any) -> Optional[int]:
    v = _num(value)
    return int(v) if v is not None else None


def _clean_identity_line(response: str, command: str) -> Optional[str]:
    for line in _at_lines(response, command):
        if line.startswith(("+", "!")):
            continue
        if line:
            return line.strip()
    return None


def parse_generic_3gpp(responses: Mapping[str, str]) -> Dict[str, Any]:
    m: Dict[str, Any] = {"cellular_adapter_level": "generic_3gpp"}

    vendor = _clean_identity_line(responses.get("AT+GMI", ""), "AT+GMI")
    model = _clean_identity_line(responses.get("AT+GMM", ""), "AT+GMM")
    fw = _clean_identity_line(responses.get("AT+GMR", ""), "AT+GMR")
    ati_lines = _at_lines(responses.get("ATI", ""), "ATI")
    if vendor: m["modem_vendor"] = vendor
    if model: m["modem_model"] = model
    if fw: m["modem_firmware"] = fw
    if ati_lines: m["modem_identity"] = " | ".join(ati_lines[:8])

    for line in _at_lines(responses.get("AT+CGSN", ""), "AT+CGSN"):
        digits = re.sub(r"\D", "", line)
        if 14 <= len(digits) <= 17:
            m["modem_imei"] = digits
            break

    for line in _at_lines(responses.get("AT+CPIN?", ""), "AT+CPIN?"):
        if line.upper().startswith("+CPIN:"):
            state = line.split(":", 1)[1].strip()
            m["sim_state"] = state
            m["sim_ready"] = state.upper() == "READY"

    reg_candidates = []
    for cmd, label in (("AT+C5GREG?", "5g"), ("AT+CEREG?", "eps"), ("AT+CGREG?", "ps"), ("AT+CREG?", "cs")):
        for line in _at_lines(responses.get(cmd, ""), cmd):
            if "REG:" not in line.upper():
                continue
            vals = _csv_fields(line.split(":",1)[1])
            nums = [_intnum(x) for x in vals[:2]]
            nums = [x for x in nums if x is not None]
            if not nums:
                continue
            stat = nums[-1]
            reg_candidates.append((label, stat))
            m[f"registration_{label}_code"] = stat
    if reg_candidates:
        # Registered home(1) or roaming(5) in 27.007 registration commands.
        registered = any(stat in {1,5} for _, stat in reg_candidates)
        searching = any(stat == 2 for _, stat in reg_candidates)
        denied = any(stat == 3 for _, stat in reg_candidates)
        m["modem_registered"] = registered
        m["registration_state"] = "registered" if registered else ("searching" if searching else ("denied" if denied else "not_registered"))

    for line in _at_lines(responses.get("AT+COPS?", ""), "AT+COPS?"):
        if line.upper().startswith("+COPS:"):
            vals = _csv_fields(line, "+COPS")
            if len(vals) >= 3:
                m["operator_name"] = vals[2].strip('"')
            if len(vals) >= 4:
                m["operator_access_technology_code"] = _intnum(vals[3])

    for line in _at_lines(responses.get("AT+CSQ", ""), "AT+CSQ"):
        if line.upper().startswith("+CSQ:"):
            vals = _csv_fields(line, "+CSQ")
            code = _intnum(vals[0]) if vals else None
            if code is not None:
                m["csq_rssi_code"] = code
                if 0 <= code <= 31:
                    m["rssi"] = -113 + 2 * code
            if len(vals) > 1:
                m["csq_ber_code"] = _intnum(vals[1])

    pdp = []
    for line in _at_lines(responses.get("AT+CGDCONT?", ""), "AT+CGDCONT?"):
        if line.upper().startswith("+CGDCONT:"):
            vals = _csv_fields(line, "+CGDCONT")
            if len(vals) >= 3:
                item = {"cid": _intnum(vals[0]), "type": vals[1].strip('"'), "apn": vals[2].strip('"')}
                pdp.append(item)
    if pdp:
        m["pdp_contexts"] = pdp
        nonempty = [x.get("apn") for x in pdp if x.get("apn")]
        if nonempty:
            m["apn"] = nonempty[0]

    ips: List[str] = []
    for line in _at_lines(responses.get("AT+CGPADDR", ""), "AT+CGPADDR"):
        if line.upper().startswith("+CGPADDR:"):
            vals = _csv_fields(line, "+CGPADDR")
            for val in vals[1:]:
                val = val.strip('"')
                if val and val not in {"0.0.0.0", "::"}:
                    ips.append(val)
    if ips:
        m["modem_ip_addresses"] = ips
        m["apn_attached"] = True
    return m


class ModemDriver:
    driver_id = "generic_3gpp"
    title = "Generic 3GPP AT"

    def matches(self, identity: str) -> bool:
        return True

    def commands(self, capture_neighbors: bool = True) -> List[str]:
        return ["ATI", "AT+GMI", "AT+GMM", "AT+GMR", "AT+CPIN?", "AT+COPS?",
                "AT+C5GREG?", "AT+CEREG?", "AT+CGREG?", "AT+CREG?", "AT+CGDCONT?", "AT+CGPADDR", "AT+CSQ"]

    def parse(self, responses: Mapping[str, str]) -> Dict[str, Any]:
        return parse_generic_3gpp(responses)


class SierraEM9Driver(ModemDriver):
    driver_id = "sierra_em9"
    title = "Sierra Wireless / Semtech EM9"

    def matches(self, identity: str) -> bool:
        x = identity.lower()
        return ("sierra" in x or "airprime" in x or "semtech" in x) and bool(re.search(r"\b(?:em919\d|em7690|em929\d)\b", x)) or bool(re.search(r"\bem(?:9190|9191|7690|9291|9293)\b", x))

    def commands(self, capture_neighbors: bool = True) -> List[str]:
        return super().commands(capture_neighbors) + ["AT!GSTATUS?", "AT!NRINFO?"]

    @staticmethod
    def _rx(text: str, pattern: str) -> Optional[str]:
        mm = re.search(pattern, text, re.I | re.M)
        return mm.group(1).strip() if mm else None

    def parse(self, responses: Mapping[str, str]) -> Dict[str, Any]:
        m = super().parse(responses)
        m["cellular_driver"] = self.driver_id
        m["cellular_adapter_level"] = "native_vendor"
        text = responses.get("AT!GSTATUS?", "")
        nr = responses.get("AT!NRINFO?", "")

        temp = _num(self._rx(text, r"Temperature:\s*(-?\d+(?:\.\d+)?)"))
        if temp is not None: m["modem_temperature_c"] = temp
        mode = self._rx(text, r"System mode:\s*([^\r\n]+?)(?:\s{2,}|\s+PS state:|$)")
        if mode:
            mode = mode.strip()
            m["modem_system_mode"] = mode
        ps = self._rx(text, r"PS state:\s*([A-Za-z ]+?)(?:\s{2,}|\s+LTE band:|\s+EMM state:|$)")
        if ps:
            m["packet_service_state"] = ps.strip()
            m["apn_attached"] = "attached" in ps.lower()
        emm = self._rx(text, r"EMM state:\s*([^\r\n]+?)(?:\s{2,}|\s+RRC state:|$)")
        if emm:
            m["emm_state"] = emm.strip()
            if "registered" in emm.lower(): m["modem_registered"] = True
        rrc = self._rx(text, r"RRC state:\s*([^\r\n]+?)(?:\s{2,}|\s+IMS reg state:|$)")
        if rrc: m["rrc_state"] = rrc.strip()

        lb = self._rx(text, r"LTE band:\s*(B?\d+)")
        if lb: m["lte_band"] = lb.upper() if lb.upper().startswith("B") else "B" + lb
        bw = _num(self._rx(text, r"LTE bw:\s*([\d.]+)\s*MHz"))
        if bw is not None: m["lte_bandwidth_mhz"] = int(bw) if bw.is_integer() else bw
        earfcn = _intnum(self._rx(text, r"LTE Rx chan:\s*(\d+)"))
        if earfcn is not None: m["lte_earfcn"] = m["earfcn"] = earfcn
        tac = self._rx(text, r"TAC:\s*([0-9A-Fa-f]+)")
        if tac: m["tac"] = tac
        cell = self._rx(text, r"Cell ID:\s*([0-9A-Fa-f]+)")
        if cell: m["cell_id"] = cell

        # Prefer primary/main receive chain as anchor RSRP; preserve all numeric chains.
        pcc_vals = [_num(x) for x in re.findall(r"PCC\s+Rx\w*\s+RSRP:\s*(-?\d+(?:\.\d+)?)", text, re.I)]
        pcc_vals = [x for x in pcc_vals if x is not None]
        if pcc_vals:
            m["lte_rsrp_chains_dbm"] = pcc_vals
            m["lte_rsrp"] = pcc_vals[0]
        lte_rsrq = _num(self._rx(text, r"(?<!NR5G )RSRQ \(dB\):\s*(-?\d+(?:\.\d+)?)"))
        lte_sinr = _num(self._rx(text, r"(?<!NR5G )SINR \(dB\):\s*(-?\d+(?:\.\d+)?)"))
        if lte_rsrq is not None: m["lte_rsrq"] = lte_rsrq
        if lte_sinr is not None: m["lte_sinr"] = lte_sinr

        alltext = text + "\n" + nr
        nb = self._rx(alltext, r"(?:SCC\d+\s+)?NR5G band:\s*(n?\d+)")
        if nb: m["nr_band"] = nb.lower() if nb.lower().startswith("n") else "n" + nb
        nchan = _intnum(self._rx(alltext, r"NR5G Rx chan:\s*(\d+)"))
        if nchan is not None: m["nr_nrarfcn"] = m["nrarfcn"] = nchan
        nrsrp = _num(self._rx(alltext, r"NR5G RSRP \(dBm\):\s*(-?\d+(?:\.\d+)?)"))
        nrsrq = _num(self._rx(alltext, r"NR5G RSRQ \(dB\):\s*(-?\d+(?:\.\d+)?)"))
        nsinr = _num(self._rx(alltext, r"NR5G SINR \(dB\):\s*(-?\d+(?:\.\d+)?)"))
        if nrsrp is not None: m["nr_rsrp"] = nrsrp
        if nrsrq is not None: m["nr_rsrq"] = nrsrq
        if nsinr is not None: m["nr_sinr"] = nsinr
        conn = self._rx(alltext, r"Connectivity Mode:\s*(SA|NSA)")
        if conn: m["nr_connectivity_mode"] = conn.upper()

        smode = str(m.get("modem_system_mode") or "").upper()
        conn = str(m.get("nr_connectivity_mode") or "").upper()
        if "ENDC" in smode or conn == "NSA":
            m["technology"] = "5G NSA"
        elif "NR5G" in smode or conn == "SA":
            m["technology"] = "5G SA" if conn == "SA" else "5G"
        elif "LTE" in smode:
            m["technology"] = "LTE"

        # Canonical RF represents the control/serving anchor in NSA and NR in SA.
        if m.get("technology") == "5G SA" and m.get("nr_rsrp") is not None:
            m["rsrp"], m["rsrq"], m["sinr"] = m.get("nr_rsrp"), m.get("nr_rsrq"), m.get("nr_sinr")
            if m.get("nr_band"): m["band"] = m["nr_band"]
        elif m.get("lte_rsrp") is not None:
            m["rsrp"], m["rsrq"], m["sinr"] = m.get("lte_rsrp"), m.get("lte_rsrq"), m.get("lte_sinr")
            if m.get("lte_band"): m["band"] = m["lte_band"]
        elif m.get("nr_rsrp") is not None:
            m["rsrp"], m["rsrq"], m["sinr"] = m.get("nr_rsrp"), m.get("nr_rsrq"), m.get("nr_sinr")
        return m


class QuectelRM5xxDriver(ModemDriver):
    driver_id = "quectel_rm5xx"
    title = "Quectel RM/RG 5G"

    def matches(self, identity: str) -> bool:
        x = identity.lower()
        return "quectel" in x and bool(re.search(r"\b(?:rm|rg)5\w+", x))

    def commands(self, capture_neighbors: bool = True) -> List[str]:
        cmds = super().commands(capture_neighbors) + ["AT+QNWINFO", 'AT+QENG="servingcell"', "AT+QCSQ"]
        if capture_neighbors:
            cmds.append('AT+QENG="neighbourcell"')
        return cmds

    def parse(self, responses: Mapping[str, str]) -> Dict[str, Any]:
        m = super().parse(responses)
        m["cellular_driver"] = self.driver_id
        m["cellular_adapter_level"] = "native_vendor"

        qnw = responses.get("AT+QNWINFO", "")
        for line in _at_lines(qnw, "AT+QNWINFO"):
            if line.upper().startswith("+QNWINFO:"):
                vals = _csv_fields(line, "+QNWINFO")
                if vals:
                    rat = vals[0].strip('"').upper()
                    m["quectel_network_info_rat"] = rat
                    if "NR5G" in rat: m["technology"] = "5G"
                    elif "LTE" in rat: m["technology"] = "LTE"
                if len(vals) > 1: m["operator_plmn"] = vals[1].strip('"')
                if len(vals) > 2:
                    bandtxt = vals[2].strip('"')
                    m["network_band_text"] = bandtxt
                    mm = re.search(r"BAND\s+(\d+)", bandtxt, re.I)
                    if mm:
                        b = mm.group(1)
                        if "NR5G" in bandtxt.upper(): m["nr_band"] = "n" + b
                        elif "LTE" in bandtxt.upper(): m["lte_band"] = "B" + b
                if len(vals) > 3:
                    ch = _intnum(vals[3])
                    if ch is not None:
                        if "NR5G" in str(m.get("quectel_network_info_rat", "")): m["nr_nrarfcn"] = m["nrarfcn"] = ch
                        else: m["lte_earfcn"] = m["earfcn"] = ch

        qeng = responses.get('AT+QENG="servingcell"', "")
        parsed_lines = []
        for line in _at_lines(qeng, 'AT+QENG="servingcell"'):
            if not line.upper().startswith("+QENG:"):
                continue
            vals = _csv_fields(line, "+QENG")
            vals = [x.strip('"') for x in vals]
            if not vals:
                continue
            parsed_lines.append(vals)
            # Single-line LTE: servingcell,state,LTE,duplex,mcc,mnc,cell,pci,earfcn,band,ulbw,dlbw,tac,rsrp,rsrq,rssi,sinr,...
            if vals[0].lower() == "servingcell" and len(vals) >= 17 and vals[2].upper() == "LTE":
                m["cellular_rrc_state"] = vals[1]
                m["technology"] = "LTE"
                m["duplex_mode"] = vals[3]
                m["mcc"], m["mnc"] = vals[4], vals[5]
                m["cell_id"] = vals[6]
                m["lte_pci"] = m["pci"] = _intnum(vals[7])
                m["lte_earfcn"] = m["earfcn"] = _intnum(vals[8])
                m["lte_band"] = "B" + str(vals[9]).lstrip("Bb")
                m["lte_bandwidth_code_ul"] = _intnum(vals[10])
                m["lte_bandwidth_code_dl"] = _intnum(vals[11])
                m["tac"] = vals[12]
                m["lte_rsrp"], m["lte_rsrq"], m["lte_rssi"], m["lte_sinr"] = map(_num, vals[13:17])
            # NSA LTE anchor line: LTE,duplex,mcc,mnc,cell,pci,earfcn,band,ulbw,dlbw,tac,rsrp,rsrq,rssi,sinr,...
            elif vals[0].upper() == "LTE" and len(vals) >= 15:
                m["technology"] = "5G NSA"
                m["duplex_mode"] = vals[1]
                m["mcc"], m["mnc"] = vals[2], vals[3]
                m["cell_id"] = vals[4]
                m["lte_pci"] = m["pci"] = _intnum(vals[5])
                m["lte_earfcn"] = m["earfcn"] = _intnum(vals[6])
                m["lte_band"] = "B" + str(vals[7]).lstrip("Bb")
                m["lte_bandwidth_code_ul"] = _intnum(vals[8])
                m["lte_bandwidth_code_dl"] = _intnum(vals[9])
                m["tac"] = vals[10]
                m["lte_rsrp"], m["lte_rsrq"], m["lte_rssi"], m["lte_sinr"] = map(_num, vals[11:15])
            # NSA NR line: NR5G-NSA,mcc,mnc,pci,rsrp,sinr,rsrq,arfcn,band,bw,scs
            elif vals[0].upper() == "NR5G-NSA" and len(vals) >= 10:
                m["technology"] = "5G NSA"
                m["nr_connectivity_mode"] = "NSA"
                m["nr_pci"] = _intnum(vals[3])
                m["nr_rsrp"] = _num(vals[4])
                m["nr_sinr"] = _num(vals[5])
                m["nr_rsrq"] = _num(vals[6])
                m["nr_nrarfcn"] = m["nrarfcn"] = _intnum(vals[7])
                m["nr_band"] = "n" + str(vals[8]).lstrip("Nn")
                m["nr_bandwidth_code"] = _intnum(vals[9])
                if len(vals) > 10: m["nr_scs_code"] = _intnum(vals[10])
            # SA: servingcell,state,NR5G-SA,duplex,mcc,mnc,cell,pci,tac,arfcn,band,bw,rsrp,rsrq,sinr,...
            elif vals[0].lower() == "servingcell" and len(vals) >= 15 and vals[2].upper() == "NR5G-SA":
                m["cellular_rrc_state"] = vals[1]
                m["technology"] = "5G SA"
                m["nr_connectivity_mode"] = "SA"
                m["duplex_mode"] = vals[3]
                m["mcc"], m["mnc"] = vals[4], vals[5]
                m["cell_id"] = vals[6]
                m["nr_pci"] = m["pci"] = _intnum(vals[7])
                m["tac"] = vals[8]
                m["nr_nrarfcn"] = m["nrarfcn"] = _intnum(vals[9])
                m["nr_band"] = "n" + str(vals[10]).lstrip("Nn")
                m["nr_bandwidth_code"] = _intnum(vals[11])
                m["nr_rsrp"], m["nr_rsrq"], m["nr_sinr"] = map(_num, vals[12:15])

        # QCSQ is a useful fallback if QENG is temporarily sparse.
        qcsq = responses.get("AT+QCSQ", "")
        for line in _at_lines(qcsq, "AT+QCSQ"):
            if line.upper().startswith("+QCSQ:"):
                vals = [x.strip('"') for x in _csv_fields(line, "+QCSQ")]
                if len(vals) >= 5 and vals[0].upper() in {"LTE", "NR5G", "NR5G-SA", "NR5G-NSA"}:
                    # Quectel 5G family commonly returns RAT,RSSI,RSRP,SINR,RSRQ.
                    q_rssi, q_rsrp, q_sinr, q_rsrq = map(_num, vals[1:5])
                    if vals[0].upper().startswith("NR5G"):
                        m.setdefault("nr_rssi", q_rssi); m.setdefault("nr_rsrp", q_rsrp)
                        m.setdefault("nr_sinr", q_sinr); m.setdefault("nr_rsrq", q_rsrq)
                    else:
                        m.setdefault("lte_rssi", q_rssi); m.setdefault("lte_rsrp", q_rsrp)
                        m.setdefault("lte_sinr", q_sinr); m.setdefault("lte_rsrq", q_rsrq)

        neigh = responses.get('AT+QENG="neighbourcell"', "")
        raw_neigh = [x for x in _at_lines(neigh, 'AT+QENG="neighbourcell"') if x.upper().startswith("+QENG:")]
        if raw_neigh:
            m["neighbor_cell_count"] = len(raw_neigh)
            # Preserve a bounded raw representation: vendor formats vary by RAT and firmware.
            m["neighbor_cells_raw"] = raw_neigh[:32]

        # Canonical RF: LTE anchor for NSA, NR serving carrier for SA.
        if m.get("technology") == "5G SA" and m.get("nr_rsrp") is not None:
            m["rsrp"], m["rsrq"], m["sinr"] = m.get("nr_rsrp"), m.get("nr_rsrq"), m.get("nr_sinr")
            if m.get("nr_band"): m["band"] = m["nr_band"]
        elif m.get("lte_rsrp") is not None:
            m["rsrp"], m["rsrq"], m["sinr"] = m.get("lte_rsrp"), m.get("lte_rsrq"), m.get("lte_sinr")
            if m.get("lte_band"): m["band"] = m["lte_band"]
        elif m.get("nr_rsrp") is not None:
            m["rsrp"], m["rsrq"], m["sinr"] = m.get("nr_rsrp"), m.get("nr_rsrq"), m.get("nr_sinr")
        return m


MODEM_DRIVERS: Dict[str, ModemDriver] = {
    "sierra_em9": SierraEM9Driver(),
    "quectel_rm5xx": QuectelRM5xxDriver(),
    "generic_3gpp": ModemDriver(),
}


def detect_modem_driver(identity: str, forced: str = "auto") -> ModemDriver:
    forced = (forced or "auto").lower().strip()
    if forced != "auto":
        if forced not in MODEM_DRIVERS:
            raise ValueError(f"Unknown modem driver {forced!r}; choose from {', '.join(MODEM_DRIVERS)}")
        return MODEM_DRIVERS[forced]
    for key in ("sierra_em9", "quectel_rm5xx"):
        if MODEM_DRIVERS[key].matches(identity):
            return MODEM_DRIVERS[key]
    return MODEM_DRIVERS["generic_3gpp"]


class CellularModemCollector(Collector):
    """Read-only cross-platform cellular collector with driver auto-detection."""
    name = "cellular_modem"

    def __init__(self, config: CellularConfig):
        self.config = config

    def _candidate_ports(self) -> List[SerialPortInfo]:
        if self.config.port and self.config.port.lower() != "auto":
            return [SerialPortInfo(self.config.port, "configured port", likely_modem=True, source="config")]
        ports = list_serial_ports(include_unlikely=True)
        likely = [p for p in ports if p.likely_modem]
        if likely:
            return likely
        return ports if self.config.scan_all_ports else []

    def _probe_one(self, port: SerialPortInfo) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            with ATSerialSession(port.device, self.config.baudrate, self.config.probe_timeout_s) as at:
                ping = at.command("AT", self.config.probe_timeout_s)
                if "OK" not in ping.upper():
                    return None, "no AT response"
                responses = {}
                for cmd in ("ATI", "AT+GMI", "AT+GMM", "AT+GMR"):
                    responses[cmd] = at.command(cmd, self.config.probe_timeout_s)
                g = parse_generic_3gpp(responses)
                identity = " ".join(str(g.get(k) or "") for k in ("modem_vendor", "modem_model", "modem_identity", "modem_firmware"))
                driver = detect_modem_driver(identity, self.config.driver)
                return {
                    "port": port.device,
                    "identity": identity.strip(),
                    "driver": driver.driver_id,
                    "driver_title": driver.title,
                    "vendor": g.get("modem_vendor"),
                    "model": g.get("modem_model"),
                    "firmware": g.get("modem_firmware"),
                    "port_source": port.source,
                }, None
        except Exception as exc:
            return None, str(exc)

    def probe(self) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        notes: List[str] = []
        if platform.system().lower() == "windows" and not _pyserial_available():
            return None, ["Native Windows AT modem access requires pyserial: py -m pip install pyserial"]
        candidates = self._candidate_ports()
        if not candidates:
            return None, ["No safe auto-probe modem ports found. Install pyserial/ModemManager, configure cellular.port, or explicitly enable scan_all_ports."]
        for port in candidates:
            info, err = self._probe_one(port)
            if info:
                return info, notes
            if err:
                notes.append(f"{port.device}: {err}")
        return None, notes or ["No AT-responsive modem found"]

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        if self.config.backend == "json" or (self.config.backend == "auto" and self.config.json_command and not _serial_backend_available()):
            ac = AdapterConfig(self.config.json_command, self.config.field_map, self.config.timeout_s)
            return JSONCommandAdapter("cellular_json", ac, prefix="").collect()

        probe, notes = self.probe()
        if not probe:
            if self.config.backend == "auto" and self.config.json_command:
                ac = AdapterConfig(self.config.json_command, self.config.field_map, self.config.timeout_s)
                jm, jn = JSONCommandAdapter("cellular_json", ac, prefix="").collect()
                return jm, notes + jn
            return {}, notes

        port = str(probe["port"])
        driver = detect_modem_driver(str(probe.get("identity") or ""), self.config.driver)
        responses: Dict[str, str] = {}
        try:
            with ATSerialSession(port, self.config.baudrate, self.config.timeout_s) as at:
                commands = list(driver.commands(self.config.capture_neighbors))
                if self.config.collect_device_identifiers and "AT+CGSN" not in commands:
                    commands.append("AT+CGSN")
                for cmd in commands:
                    try:
                        responses[cmd] = at.command(cmd, self.config.timeout_s)
                    except Exception as exc:
                        notes.append(f"{cmd}: {exc}")
        except Exception as exc:
            return {}, notes + [f"Could not open/probe modem AT port {port}: {exc}"]

        metrics = driver.parse(responses)
        metrics.update({
            "cellular_port": port,
            "cellular_driver": driver.driver_id,
            "cellular_driver_title": driver.title,
            "cellular_read_only": True,
        })
        if self.config.include_raw_responses:
            # Evidence/debug mode; still bounded to prevent pathological modem output.
            metrics["cellular_raw_at"] = {k: v[:12000] for k, v in responses.items()}
        return metrics, notes

    @staticmethod
    def compatibility_matrix() -> List[Dict[str, Any]]:
        return [
            {"family": "Sierra/Semtech EM9190/EM9191/EM7690/EM929x", "driver": "sierra_em9", "depth": "native/deep", "transport": "AT serial"},
            {"family": "Quectel RM520N + compatible RM/RG 5G (QENG)", "driver": "quectel_rm5xx", "depth": "native/deep", "transport": "AT serial"},
            {"family": "SIMCom (standards-compliant AT)", "driver": "generic_3gpp", "depth": "baseline", "transport": "AT serial"},
            {"family": "Telit (standards-compliant AT)", "driver": "generic_3gpp", "depth": "baseline", "transport": "AT serial"},
            {"family": "Fibocom (standards-compliant AT)", "driver": "generic_3gpp", "depth": "baseline", "transport": "AT serial"},
            {"family": "Cinterion/Thales (standards-compliant AT)", "driver": "generic_3gpp", "depth": "baseline", "transport": "AT serial"},
            {"family": "u-blox (standards-compliant AT)", "driver": "generic_3gpp", "depth": "baseline", "transport": "AT serial"},
            {"family": "Any external modem/router", "driver": "json", "depth": "adapter-defined", "transport": "JSON command"},
        ]


class StarlinkCollector(Collector):
    """Read-only Starlink terminal telemetry collector.

    Backend order in ``auto`` mode:
      1. ``starlink_grpc`` from sparky8512/starlink-grpc-tools, if importable.
      2. ``grpcurl`` using server reflection.

    No reboot, stow, GPS-control, sleep-control, or other state-changing RPCs
    are implemented here.  Veilbreaker treats Starlink as a diagnostic sensor.
    """

    name = "starlink"
    SERVICE = "SpaceX.API.Device.Device/Handle"

    def __init__(self, config: StarlinkConfig):
        self.config = config

    @property
    def target(self) -> str:
        return f"{self.config.host}:{int(self.config.port)}"

    @staticmethod
    def _snake(name: str) -> str:
        name = str(name).replace("-", "_")
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        return name

    @classmethod
    def _snake_obj(cls, obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return {cls._snake(k): cls._snake_obj(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [cls._snake_obj(v) for v in obj]
        return obj

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_bool(value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"true", "1", "yes", "on"}: return True
            if v in {"false", "0", "no", "off"}: return False
        return bool(value)

    def backend_availability(self) -> Dict[str, bool]:
        try:
            spec = importlib.util.find_spec("starlink_grpc")
            py_ok = spec is not None
        except Exception:
            py_ok = False
        return {
            "python": py_ok,
            "grpcurl": command_exists("grpcurl"),
        }

    def _choose_backend(self) -> Optional[str]:
        avail = self.backend_availability()
        wanted = self.config.backend
        if wanted == "python":
            return "python" if avail["python"] else None
        if wanted == "grpcurl":
            return "grpcurl" if avail["grpcurl"] else None
        if avail["python"]:
            return "python"
        if avail["grpcurl"]:
            return "grpcurl"
        return None

    def probe(self) -> Tuple[bool, str]:
        """TCP reachability only; does not prove the target is a Starlink dish."""
        try:
            with socket.create_connection((self.config.host, int(self.config.port)), timeout=min(2.5, self.config.timeout_s)):
                return True, f"{self.target} reachable"
        except OSError as exc:
            return False, str(exc)

    def _canonicalize(self, status: Mapping[str, Any], alerts: Optional[Mapping[str, Any]] = None,
                      location: Optional[Mapping[str, Any]] = None, backend: str = "unknown") -> Dict[str, Any]:
        st = self._snake_obj(status)
        al = self._snake_obj(alerts or {})
        loc = self._snake_obj(location or {})

        state = str(st.get("state") or "UNKNOWN").upper()
        fraction = self._as_float(st.get("fraction_obstructed"))
        drop = self._as_float(st.get("pop_ping_drop_rate"))
        down_bps = self._as_float(st.get("downlink_throughput_bps"))
        up_bps = self._as_float(st.get("uplink_throughput_bps"))

        out: Dict[str, Any] = {
            "satellite_provider": "starlink",
            "satellite_terminal_type": "starlink_user_terminal",
            "starlink_backend": backend,
            "starlink_target": self.target,
            "starlink_state": state,
            "satellite_registered": state == "CONNECTED",
        }

        simple_map = {
            "id": "starlink_terminal_id",
            "hardware_version": "starlink_hardware_version",
            "software_version": "starlink_software_version",
            "uptime": "starlink_uptime_s",
            "seconds_to_first_nonempty_slot": "starlink_seconds_to_next_slot",
            "alerts": "starlink_alert_bits",
            "currently_obstructed": "starlink_currently_obstructed",
            "obstruction_duration": "starlink_obstruction_duration_s",
            "obstruction_interval": "starlink_obstruction_interval_s",
            "direction_azimuth": "starlink_boresight_azimuth_deg",
            "direction_elevation": "starlink_boresight_elevation_deg",
            "is_snr_above_noise_floor": "starlink_snr_above_noise_floor",
            "gps_ready": "starlink_gps_ready",
            "gps_enabled": "starlink_gps_enabled",
            "gps_sats": "starlink_gps_sats",
        }
        for src, dst in simple_map.items():
            if st.get(src) is not None:
                out[dst] = st.get(src)

        latency = self._as_float(st.get("pop_ping_latency_ms"))
        if latency is not None:
            out["starlink_pop_ping_latency_ms"] = latency
            out["satellite_latency_ms"] = latency
        if drop is not None:
            out["starlink_pop_ping_drop_rate"] = drop
            out["satellite_packet_loss_pct"] = max(0.0, min(100.0, drop * 100.0))
        if fraction is not None:
            out["starlink_fraction_obstructed"] = fraction
            out["satellite_obstructed_pct"] = max(0.0, min(100.0, fraction * 100.0))
        if down_bps is not None:
            out["starlink_downlink_mbps_instant"] = down_bps / 1_000_000.0
        if up_bps is not None:
            out["starlink_uplink_mbps_instant"] = up_bps / 1_000_000.0

        active_alerts: List[str] = []
        for key, value in al.items():
            if key.startswith("alert_") and self._as_bool(value) is True:
                active_alerts.append(key[6:])
                out[f"starlink_{key}"] = True
        if active_alerts:
            out["starlink_active_alerts"] = sorted(active_alerts)
            out["starlink_active_alert_count"] = len(active_alerts)
        else:
            out["starlink_active_alert_count"] = 0

        if self.config.collect_location and loc:
            if loc.get("latitude") is not None: out["starlink_lat"] = loc.get("latitude")
            if loc.get("longitude") is not None: out["starlink_lon"] = loc.get("longitude")
            if loc.get("altitude") is not None: out["starlink_alt_m"] = loc.get("altitude")

        return out

    def _collect_python(self) -> Tuple[Dict[str, Any], List[str]]:
        try:
            mod = importlib.import_module("starlink_grpc")
        except Exception as exc:
            return {}, [f"starlink_grpc import failed: {exc}"]
        context = None
        try:
            context = mod.ChannelContext(target=self.target)
            groups = mod.status_data(context=context)
            status = dict(groups[0] or {})
            alerts = dict(groups[2] or {}) if len(groups) > 2 else {}
            location = {}
            if self.config.collect_location:
                try:
                    location = dict(mod.location_data(context=context) or {})
                except Exception as exc:
                    # Location is optional and often permission-gated.
                    location = {}
                    note = f"Starlink location unavailable: {exc}"
                    metrics = self._canonicalize(status, alerts, location, backend="python-starlink_grpc")
                    return metrics, [note]
            return self._canonicalize(status, alerts, location, backend="python-starlink_grpc"), []
        except Exception as exc:
            return {}, [f"Starlink gRPC status failed: {exc}"]
        finally:
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass

    @classmethod
    def _status_from_grpcurl_json(cls, raw: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        obj = cls._snake_obj(raw)
        body = obj.get("dish_get_status") if isinstance(obj, Mapping) else None
        if not isinstance(body, Mapping):
            # grpcurl may already return the DishGetStatus body depending on proto/version.
            body = obj if isinstance(obj, Mapping) else {}

        device_info = body.get("device_info") if isinstance(body.get("device_info"), Mapping) else {}
        device_state = body.get("device_state") if isinstance(body.get("device_state"), Mapping) else {}
        obs = body.get("obstruction_stats") if isinstance(body.get("obstruction_stats"), Mapping) else {}
        gps = body.get("gps_stats") if isinstance(body.get("gps_stats"), Mapping) else {}
        alert_obj = body.get("alerts") if isinstance(body.get("alerts"), Mapping) else {}

        state = body.get("state")
        outage = body.get("outage") if isinstance(body.get("outage"), Mapping) else None
        if not state:
            if outage and outage.get("cause"):
                cause = str(outage.get("cause")).upper()
                state = "SEARCHING" if cause == "NO_SCHEDULE" else cause
            else:
                state = "CONNECTED"

        status = {
            "id": device_info.get("id"),
            "hardware_version": device_info.get("hardware_version"),
            "software_version": device_info.get("software_version"),
            "state": state,
            "uptime": device_state.get("uptime_s"),
            "seconds_to_first_nonempty_slot": body.get("seconds_to_first_nonempty_slot"),
            "pop_ping_drop_rate": body.get("pop_ping_drop_rate"),
            "downlink_throughput_bps": body.get("downlink_throughput_bps"),
            "uplink_throughput_bps": body.get("uplink_throughput_bps"),
            "pop_ping_latency_ms": body.get("pop_ping_latency_ms"),
            "fraction_obstructed": obs.get("fraction_obstructed"),
            "currently_obstructed": obs.get("currently_obstructed"),
            "obstruction_duration": obs.get("avg_prolonged_obstruction_duration_s"),
            "obstruction_interval": obs.get("avg_prolonged_obstruction_interval_s"),
            "direction_azimuth": body.get("boresight_azimuth_deg"),
            "direction_elevation": body.get("boresight_elevation_deg"),
            "is_snr_above_noise_floor": body.get("is_snr_above_noise_floor"),
            "gps_ready": gps.get("gps_valid"),
            "gps_enabled": None if gps.get("inhibit_gps") is None else not bool(gps.get("inhibit_gps")),
            "gps_sats": gps.get("gps_sats"),
        }
        alerts = {f"alert_{k}": v for k, v in alert_obj.items()}
        return status, alerts

    def _collect_grpcurl(self) -> Tuple[Dict[str, Any], List[str]]:
        if not command_exists("grpcurl"):
            return {}, ["grpcurl is not installed or not on PATH"]
        argv = [
            "grpcurl", "-plaintext", "-d", '{"get_status":{}}',
            self.target, self.SERVICE,
        ]
        result = run_command(argv, self.config.timeout_s)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            return {}, [f"grpcurl Starlink status failed rc={result.returncode}: {detail}"]
        try:
            raw = json.loads(result.stdout)
        except Exception as exc:
            return {}, [f"grpcurl returned non-JSON Starlink status: {exc}"]
        status, alerts = self._status_from_grpcurl_json(raw)
        return self._canonicalize(status, alerts, {}, backend="grpcurl-reflection"), []

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        backend = self._choose_backend()
        if backend == "python":
            metrics, notes = self._collect_python()
            # In auto mode, allow a grpcurl fallback when the Python module is
            # present but incompatible with a newer terminal firmware/proto.
            if metrics or self.config.backend == "python" or not command_exists("grpcurl"):
                return metrics, notes
            m2, n2 = self._collect_grpcurl()
            return m2, notes + ["Fell back to grpcurl after Python backend failure."] + n2
        if backend == "grpcurl":
            return self._collect_grpcurl()
        reachable, detail = self.probe()
        base = {
            "satellite_provider": "starlink",
            "starlink_target": self.target,
            "starlink_management_reachable": reachable,
        }
        notes = [
            "Starlink telemetry backend unavailable. Install starlink-grpc-tools (starlink_grpc) "
            "or grpcurl for full read-only terminal telemetry.",
            f"Management probe: {detail}",
        ]
        return base, notes


@dataclass
class PingResult:
    reachable: bool
    transmitted: int = 0
    received: int = 0
    loss_pct: Optional[float] = None
    min_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    max_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    raw: str = ""


def _parse_ping_output(text: str, system: Optional[str] = None, returncode: int = 0) -> PingResult:
    """Parse Linux or English Windows ping output."""
    system = (system or platform.system()).lower()
    tx = rx = 0
    loss: Optional[float] = None
    mn = avg = mx = jit = None

    if system == "windows":
        stats = re.search(
            r"Packets:\s*Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+),\s*Lost\s*=\s*(\d+)\s*\((\d+(?:\.\d+)?)%\s*loss\)",
            text, re.I,
        )
        if stats:
            tx, rx = int(stats.group(1)), int(stats.group(2))
            loss = float(stats.group(4))
        timing = re.search(
            r"Minimum\s*=\s*(\d+)ms,\s*Maximum\s*=\s*(\d+)ms,\s*Average\s*=\s*(\d+)ms",
            text, re.I,
        )
        if timing:
            mn, mx, avg = map(float, timing.groups())
        times: List[float] = []
        for token in re.findall(r"time[=<]\s*(\d+)ms", text, re.I):
            try:
                times.append(float(token))
            except Exception:
                pass
        if len(times) >= 2:
            deltas = [abs(times[i] - times[i-1]) for i in range(1, len(times))]
            jit = statistics.mean(deltas) if deltas else 0.0
        reachable = (rx > 0) if stats else (returncode == 0)
        return PingResult(reachable, tx, rx, loss, mn, avg, mx, jit, text.strip())

    stats = re.search(r"(\d+) packets transmitted, (\d+) received,.*?(\d+(?:\.\d+)?)% packet loss", text)
    if stats:
        tx, rx, loss = int(stats.group(1)), int(stats.group(2)), float(stats.group(3))
    timing = re.search(r"(?:rtt|round-trip) min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", text)
    if timing:
        mn, avg, mx, jit = map(float, timing.groups())
    return PingResult(bool(rx > 0 and returncode in (0, 1)), tx, rx, loss, mn, avg, mx, jit, text.strip())


def ping_host(target: str, count: int = 5, timeout_s: float = 8.0, payload_size: Optional[int] = None,
              do_not_fragment: bool = False) -> PingResult:
    if not command_exists("ping"):
        return PingResult(False, raw="ping command not installed")

    system = platform.system().lower()
    if system == "windows":
        argv = ["ping", "-n", str(max(1, count)), "-w", "2000"]
        if payload_size is not None:
            argv += ["-l", str(int(payload_size))]
        if do_not_fragment:
            argv += ["-f"]
        argv.append(target)
    else:
        argv = ["ping", "-n", "-c", str(max(1, count)), "-W", "2"]
        if payload_size is not None:
            argv += ["-s", str(int(payload_size))]
        if do_not_fragment and system == "linux":
            argv += ["-M", "do"]
        argv.append(target)

    res = run_command(argv, timeout_s, env={"LC_ALL": "C"} if system == "linux" else None)
    text = (res.stdout or "") + "\n" + (res.stderr or "")
    return _parse_ping_output(text, system=system, returncode=res.returncode)


class ActiveNetworkCollector(Collector):
    name = "active_network"

    def __init__(self, config: AppConfig, seed_metrics: Mapping[str, Any]):
        self.config = config
        self.seed = seed_metrics

    def collect(self) -> Tuple[Dict[str, Any], List[str]]:
        m: Dict[str, Any] = {}
        notes: List[str] = []
        gateway = self.seed.get("gateway_ip")
        if gateway:
            p = ping_host(str(gateway), count=5)
            m["gateway_reachable"] = p.reachable
            if p.avg_ms is not None:
                m["gateway_latency_ms"] = p.avg_ms
            if p.loss_pct is not None:
                m["gateway_packet_loss_pct"] = p.loss_pct
        target = self.config.public_ping_target
        if target:
            p = ping_host(str(target), count=8, timeout_s=12)
            m["internet_reachable"] = p.reachable
            if p.avg_ms is not None:
                m["latency_ms"] = p.avg_ms
            if p.loss_pct is not None:
                m["packet_loss_pct"] = p.loss_pct
            if p.jitter_ms is not None:
                m["jitter_ms"] = p.jitter_ms
        host = self.config.dns_test_host
        if host:
            t0 = time.monotonic()
            try:
                infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
                elapsed = (time.monotonic() - t0) * 1000.0
                m["dns_success"] = bool(infos)
                m["dns_latency_ms"] = round(elapsed, 2)
            except Exception as exc:
                m["dns_success"] = False
                notes.append(f"DNS test failed for {host}: {exc}")
        return m, notes


# =============================================================================
# HACKRF PRO: RECEIVE-ONLY SPECTRUM SUPPORT
# =============================================================================

@dataclass
class SweepBin:
    hz: float
    power_db: float


@dataclass
class SweepSummary:
    label: str
    min_mhz: float
    max_mhz: float
    bin_width_hz: float
    bins: int
    median_db: float
    p10_db: float
    p90_db: float
    peak_db: float
    peak_freq_mhz: float
    peak_excess_db: float
    occupancy_pct: float
    flatness: float
    top_peaks: List[Tuple[float, float]]
    csv_path: str


class HackRFCollector:
    """HackRF Pro integration using official HackRF host tools.

    Veilbreaker intentionally uses only receive/discovery operations here.
    No transmit path is implemented in this application.
    """

    def __init__(self, config: SDRConfig, artifact_dir: Path):
        self.config = config
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def tool_path(self, name: str) -> Optional[str]:
        """Resolve installed tools without changing the user's system PATH."""
        executable = name + (".exe" if os.name == "nt" else "")
        configured = self.config.tools_dir or os.environ.get("VEILBREAKER_HACKRF_DIR")
        if configured:
            candidate = Path(configured).expanduser() / executable
            return str(candidate) if candidate.is_file() else None
        found = shutil.which(name)
        if found:
            return found
        if os.name == "nt":
            for root in (Path(os.environ.get("ProgramData", "C:/ProgramData")) / "radioconda",
                         Path.home() / "radioconda", Path.home() / "AppData/Local/radioconda"):
                candidate = root / "Library/bin" / executable
                if candidate.is_file():
                    return str(candidate)
        return None

    def tools_available(self) -> bool:
        return bool(self.tool_path("hackrf_info") and self.tool_path("hackrf_sweep"))

    def info(self) -> Tuple[Dict[str, Any], List[str]]:
        executable = self.tool_path("hackrf_info")
        if not executable:
            return {}, ["hackrf_info not installed"]
        argv = [executable]
        if self.config.serial:
            argv += ["-d", str(self.config.serial)]
        res = run_command(argv, 5)
        if res.returncode != 0:
            return {}, [f"hackrf_info failed: {res.stderr.strip() or res.stdout.strip()}"]
        text = res.stdout + "\n" + res.stderr
        if "Found HackRF" not in text:
            return {"sdr_present": False}, [text.strip() or "No HackRF reported by host tools"]
        m: Dict[str, Any] = {"sdr_present": True, "sdr_backend": "hackrf_tools", "sdr_tool_path": executable}
        pats = {
            "sdr_serial": r"Serial number:\s*(\S+)",
            "sdr_board_id": r"Board ID Number:\s*(.+)$",
            "sdr_firmware": r"Firmware Version:\s*(.+)$",
            "sdr_part_id": r"Part ID Number:\s*(.+)$",
        }
        for k, pat in pats.items():
            mm = re.search(pat, text, re.M | re.I)
            if mm:
                m[k] = mm.group(1).strip()
        version = re.search(r"hackrf_info version:\s*(.+)", text)
        if version:
            m["sdr_host_version"] = version.group(1).strip()
        self.device_serial = m.get("sdr_serial")
        notes = []
        if "unknown" in str(m.get("sdr_board_id", "")).lower() or "unknown" in str(m.get("sdr_firmware", "")).lower():
            notes.append("Installed host tools do not identify this board/firmware version. Capture compatibility must be verified separately.")
        return m, notes

    def _validate(self, r: SDRRange) -> None:
        # The host sweep CLI accepts whole MHz. Do not silently truncate fractional ranges.
        if not all(math.isfinite(v) and float(v).is_integer() for v in (r.min_mhz, r.max_mhz)) or r.min_mhz < 1 or r.max_mhz > 6000 or r.min_mhz >= r.max_mhz:
            raise ValueError(f"SDR range {r.label} requires whole MHz inside 1-6000 and min < max")
        if not 1 <= int(self.config.sweeps) <= 10000:
            raise ValueError("Sweep count must be 1..10000")
        if not (2445 <= int(self.config.bin_width_hz) <= 5_000_000):
            raise ValueError("hackrf_sweep bin width must be 2445..5000000 Hz")
        if int(self.config.lna_gain_db) not in range(0, 41, 8):
            raise ValueError("HackRF RX LNA gain must be 0..40 dB in 8 dB steps")
        if int(self.config.vga_gain_db) < 0 or int(self.config.vga_gain_db) > 62 or int(self.config.vga_gain_db) % 2:
            raise ValueError("HackRF RX VGA gain must be 0..62 dB in 2 dB steps")

    @staticmethod
    def parse_sweep_csv(path: Path) -> List[SweepBin]:
        bins: List[SweepBin] = []
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 7:
                    continue
                try:
                    hz_low = float(row[2])
                    bin_width = float(row[4])
                    powers = [float(x) for x in row[6:] if str(x).strip()]
                except ValueError:
                    continue
                for i, power in enumerate(powers):
                    center = hz_low + (i + 0.5) * bin_width
                    if math.isfinite(center) and math.isfinite(power) and bin_width > 0:
                        bins.append(SweepBin(center, power))
        # hackrf_sweep can emit rows out of frequency order; normalize here.
        bins.sort(key=lambda x: x.hz)
        return bins

    @staticmethod
    def summarize(label: str, r: SDRRange, bins: Sequence[SweepBin], csv_path: Path) -> SweepSummary:
        if not bins:
            raise ValueError("No spectrum bins were captured")
        powers = [b.power_db for b in bins]
        med = float(safe_median(powers))
        p10 = float(percentile(powers, 0.10))
        p90 = float(percentile(powers, 0.90))
        peak = max(bins, key=lambda b: b.power_db)
        threshold = med + 6.0
        occupancy = sum(1 for b in bins if b.power_db >= threshold) / len(bins) * 100.0

        # Convert relative dB values to linear power for spectral-flatness ratio.
        linear = [10 ** (p / 10.0) for p in powers]
        arithmetic = sum(linear) / len(linear)
        geometric = math.exp(sum(math.log(max(x, 1e-30)) for x in linear) / len(linear))
        flatness = geometric / arithmetic if arithmetic > 0 else 0.0

        # Pick top local maxima with simple frequency separation so the list is useful.
        candidates: List[SweepBin] = []
        for i, b in enumerate(bins):
            left = bins[i - 1].power_db if i else -999.0
            right = bins[i + 1].power_db if i + 1 < len(bins) else -999.0
            if b.power_db >= left and b.power_db >= right and b.power_db >= med + 4.0:
                candidates.append(b)
        candidates.sort(key=lambda b: b.power_db, reverse=True)
        selected: List[SweepBin] = []
        sep_hz = max((bins[1].hz - bins[0].hz) * 2 if len(bins) > 1 else 1e6, 1e6)
        for c in candidates:
            if all(abs(c.hz - s.hz) >= sep_hz for s in selected):
                selected.append(c)
            if len(selected) >= 5:
                break

        frequencies = sorted({b.hz for b in bins})
        width = min((b - a for a, b in zip(frequencies, frequencies[1:])), default=0.0)
        return SweepSummary(
            label=label,
            min_mhz=r.min_mhz,
            max_mhz=r.max_mhz,
            bin_width_hz=width,
            bins=len(bins),
            median_db=round(med, 2),
            p10_db=round(p10, 2),
            p90_db=round(p90, 2),
            peak_db=round(peak.power_db, 2),
            peak_freq_mhz=round(peak.hz / 1e6, 6),
            peak_excess_db=round(peak.power_db - med, 2),
            occupancy_pct=round(occupancy, 2),
            flatness=round(flatness, 4),
            top_peaks=[(round(x.hz / 1e6, 6), round(x.power_db, 2)) for x in selected],
            csv_path=str(csv_path),
        )

    def sweep_range(self, r: SDRRange) -> SweepSummary:
        self._validate(r)
        executable = self.tool_path("hackrf_sweep")
        if not executable:
            raise RuntimeError("hackrf_sweep is not installed")
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", r.label)
        out = self.artifact_dir / f"hackrf_{safe_label}_{uuid.uuid4().hex[:10]}.csv"
        argv = [
            executable,
            "-f", f"{r.min_mhz:g}:{r.max_mhz:g}",
            "-w", str(int(self.config.bin_width_hz)),
            "-N", str(max(1, int(self.config.sweeps))),
            "-a", "1" if self.config.amp_enable else "0",
            "-p", "1" if self.config.antenna_power else "0",
            "-l", str(int(self.config.lna_gain_db)),
            "-g", str(int(self.config.vga_gain_db)),
            "-r", str(out),
        ]
        if self.config.serial:
            argv[1:1] = ["-d", str(self.config.serial)]
        span = max(1.0, r.max_mhz - r.min_mhz)
        timeout = max(10.0, min(120.0, 10.0 + span / 75.0 * max(1, self.config.sweeps)))
        from .recovery import atomic_json
        capture = {"timestamp": utcnow_iso(), "command": argv, "settings": asdict(self.config), "range": asdict(r), "device_serial": getattr(self, "device_serial", None), "state": "running"}
        atomic_json(out.with_suffix(".capture.json"), capture)
        res = run_command(argv, timeout)
        out.with_suffix(".log.txt").write_text(res.stdout + "\n" + res.stderr, encoding="utf-8")
        capture.update(returncode=res.returncode, state="finished")
        atomic_json(out.with_suffix(".capture.json"), capture)
        if res.returncode != 0 or not out.exists():
            raise RuntimeError(f"hackrf_sweep failed rc={res.returncode}: {res.stderr.strip() or res.stdout.strip()}")
        bins = [b for b in self.parse_sweep_csv(out) if r.min_mhz * 1e6 <= b.hz < r.max_mhz * 1e6]
        return self.summarize(r.label, r, bins, out)

    def collect(self, ranges: Optional[Sequence[SDRRange]] = None) -> Tuple[Dict[str, Any], List[str], List[SweepSummary]]:
        metrics, notes = self.info()
        summaries: List[SweepSummary] = []
        if not metrics.get("sdr_present"):
            return metrics, notes, summaries
        for r in (list(ranges) if ranges is not None else self.config.ranges):
            try:
                summary = self.sweep_range(r)
                summaries.append(summary)
                key = re.sub(r"[^a-z0-9]+", "_", r.label.lower()).strip("_")
                metrics[f"sdr_{key}_median_db"] = summary.median_db
                metrics[f"sdr_{key}_p90_db"] = summary.p90_db
                metrics[f"sdr_{key}_peak_db"] = summary.peak_db
                metrics[f"sdr_{key}_peak_freq_mhz"] = summary.peak_freq_mhz
                metrics[f"sdr_{key}_peak_excess_db"] = summary.peak_excess_db
                metrics[f"sdr_{key}_occupancy_pct"] = summary.occupancy_pct
                metrics[f"sdr_{key}_flatness"] = summary.flatness
            except Exception as exc:
                notes.append(f"SDR sweep {r.label} failed: {exc}")
        return metrics, notes, summaries


# =============================================================================
# ACTIVE DIAGNOSTICS
# =============================================================================

class ActiveTestExecutor:
    def __init__(self, config: AppConfig):
        self.config = config

    def path_stages(self, metrics: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        out: Dict[str, Any] = {}
        notes: List[str] = []
        targets: List[Tuple[str, str]] = []
        if metrics.get("gateway_ip"):
            targets.append(("gateway", str(metrics["gateway_ip"])))
        for i, target in enumerate(self.config.path_targets):
            targets.append((f"path{i+1}", target))
        if self.config.public_ping_target:
            targets.append(("public", self.config.public_ping_target))
        seen = set()
        for label, target in targets:
            if target in seen:
                continue
            seen.add(target)
            p = ping_host(target, count=8, timeout_s=12)
            out[f"stage_{label}_reachable"] = p.reachable
            if p.avg_ms is not None:
                out[f"stage_{label}_latency_ms"] = p.avg_ms
            if p.loss_pct is not None:
                out[f"stage_{label}_loss_pct"] = p.loss_pct
            if label == "gateway":
                out["gateway_reachable"] = p.reachable
                if p.avg_ms is not None:
                    out["gateway_latency_ms"] = p.avg_ms
            if label == "public":
                out["internet_reachable"] = p.reachable
                if p.avg_ms is not None:
                    out["latency_ms"] = p.avg_ms
                if p.loss_pct is not None:
                    out["packet_loss_pct"] = p.loss_pct
                if p.jitter_ms is not None:
                    out["jitter_ms"] = p.jitter_ms
        return out, notes

    def path_mtu(self, target: str, max_payload: int = 1472, min_payload: int = 1200) -> Tuple[Dict[str, Any], List[str]]:
        system = platform.system().lower()
        if system not in {"linux", "windows"}:
            return {}, [f"PMTU active test is not implemented for {platform.system()} ping semantics"]
        lo, hi = min_payload, max_payload
        best = None
        attempts = 0
        while lo <= hi and attempts < 12:
            attempts += 1
            mid = (lo + hi) // 2
            p = ping_host(target, count=2, timeout_s=6, payload_size=mid, do_not_fragment=True)
            if p.reachable and (p.loss_pct is None or p.loss_pct < 100):
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best is None:
            return {"pmtu_test_success": False}, [f"No DF payload >= {min_payload} bytes reached {target}"]
        # IPv4 ICMP payload excludes 20 byte IP + 8 byte ICMP header.
        return {
            "pmtu_test_success": True,
            "pmtu_payload_bytes": best,
            "pmtu_estimated_ipv4_bytes": best + 28,
            "pmtu_target": target,
        }, []

    def iperf3(self) -> Tuple[Dict[str, Any], List[str]]:
        if not self.config.iperf3_server:
            return {}, ["iperf3 server is not configured"]
        if not command_exists("iperf3"):
            return {}, ["iperf3 is not installed"]
        argv = ["iperf3", "-c", self.config.iperf3_server, "-p", str(self.config.iperf3_port), "-J", "-t", "5"]
        metrics: Dict[str, Any] = {}
        notes: List[str] = []
        # Sender/receiver totals describe the SAME direction. Measure download
        # separately with reverse mode instead of relabeling upload delivery.
        for key, flags in (("upload_mbps", []), ("download_mbps", ["-R"])):
            res = run_command(argv + flags, 15)
            if res.returncode != 0:
                notes.append(f"iperf3 {key} failed: {res.stderr.strip()}")
                continue
            try:
                obj = json.loads(res.stdout)
                if obj.get("error"):
                    raise ValueError(obj["error"])
                rate = float(obj["end"]["sum_received"]["bits_per_second"])
                if not math.isfinite(rate) or rate < 0:
                    raise ValueError("invalid received bitrate")
                metrics[key] = rate / 1e6
            except (ValueError, TypeError, KeyError) as exc:
                notes.append(f"Could not parse iperf3 {key}: {exc}")
        if metrics:
            metrics["throughput_source"] = "iperf3 (separate forward/reverse tests)"
        return metrics, notes



# =============================================================================
# PROFESSIONAL REASONING LAYER
# =============================================================================

class ProfessionalVeilbreakerEngine(VeilbreakerLogicEngine):
    """Adds temporal/site memory, SDR, satellite, staged-path and case reasoning.

    The confidence values remain *confidence-like expert scores*, not calibrated
    probabilities.  They are intended to rank hypotheses and expose the engine's
    reasoning rather than imply statistical certainty.
    """

    VERSION = APP_VERSION

    HYPOTHESIS_CATALOG = {
        "weak_coverage": ("Weak / obstructed cellular coverage", Domain.CELLULAR_RF, 0.18),
        "antenna_feedline": ("Antenna / feedline / placement degradation", Domain.CELLULAR_RF, 0.10),
        "ran_interference_or_load": ("RAN interference, overlap, or cell loading", Domain.RAN, 0.18),
        "cell_change_instability": ("Serving-cell / band instability", Domain.RAN, 0.08),
        "lte_anchor_impairment": ("LTE anchor impairment in 5G NSA", Domain.RAN, 0.09),
        "nr_secondary_impairment": ("NR secondary-carrier impairment", Domain.RAN, 0.08),
        "modem_thermal": ("Cellular modem thermal/resource impairment", Domain.DEVICE, 0.05),
        "registration_failure": ("Cellular registration failure", Domain.RAN, 0.08),
        "apn_or_core": ("APN / packet-core session problem", Domain.CARRIER_CORE, 0.10),
        "carrier_or_core_path": ("Carrier/core/private-WAN path problem", Domain.CARRIER_CORE, 0.17),
        "wan_path": ("WAN transport impairment", Domain.WAN, 0.18),
        "local_handoff": ("Local Ethernet/VLAN/gateway handoff problem", Domain.LOCAL_LAN, 0.14),
        "dns_failure": ("DNS / resolver path problem", Domain.DNS, 0.07),
        "mtu_or_fragmentation": ("MTU / PMTUD / tunnel-overhead issue", Domain.MTU, 0.08),
        "throughput_degradation": ("General throughput degradation", Domain.WAN, 0.12),
        "wifi_access": ("Wi-Fi access-layer impairment", Domain.WIFI, 0.10),
        "wifi_interference": ("Wi-Fi interference / contention", Domain.WIFI, 0.08),
        "device_resource": ("Local device resource constraint", Domain.DEVICE, 0.06),
        "device_provisioning": ("SIM/device provisioning problem", Domain.DEVICE, 0.06),
        "sdr_interference": ("Abnormal RF energy / interference signature", Domain.SDR, 0.08),
        "satellite_visibility": ("Satellite visibility / terminal RF impairment", Domain.SATELLITE, 0.08),
        "satellite_transport": ("Satellite upstream / transport impairment", Domain.SATELLITE, 0.10),
        "starlink_obstruction": ("Starlink sky obstruction / visibility impairment", Domain.SATELLITE, 0.10),
        "starlink_terminal": ("Starlink terminal / hardware / thermal fault", Domain.SATELLITE, 0.07),
        "starlink_pop_path": ("Starlink access / PoP path impairment", Domain.SATELLITE, 0.12),
    }

    def analyze(self, raw_metrics: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> DiagnosticReport:
        context = dict(context or {})
        m = self.normalizer.normalize(raw_metrics)
        findings: List[Finding] = []
        evidence: List[Evidence] = []

        dq = self._data_quality(m, findings)
        self._registration(m, findings, evidence)
        self._cellular_rf(m, findings, evidence)
        self._multirat_cellular_reasoning(m, findings, evidence)
        self._transport(m, findings, evidence)
        self._dns(m, findings, evidence)
        self._mtu(m, findings, evidence)
        self._performance(m, findings, evidence)
        self._wifi(m, findings, evidence)
        self._device(m, findings, evidence)
        self._cross_domain(m, findings, evidence)

        self._satellite_reasoning(m, findings, evidence)
        self._starlink_reasoning(m, findings, evidence, context.get("baseline") or {})
        self._sdr_reasoning(m, findings, evidence, context.get("baseline") or {})
        self._staged_path_reasoning(m, findings, evidence)
        self._baseline_reasoning(m, findings, evidence, context.get("baseline") or {})
        self._case_reasoning(m, findings, evidence, context.get("case_matches") or [])

        hypotheses = self._rank_hypotheses(evidence)
        tests = self._next_tests(m, hypotheses)
        tests = self._augment_tests(m, hypotheses, tests, context)
        health = self._health(findings, dq)
        status = self._status(health)
        service_keys = ("internet_reachable", "dns_success", "latency_ms", "packet_loss_pct",
                        "download_mbps", "upload_mbps", "satellite_latency_ms", "starlink_pop_ping_latency_ms")
        if status == "HEALTHY" and not any(m.get(key) is not None for key in service_keys):
            status = "INSUFFICIENT_EVIDENCE"
        summary = self._summary(hypotheses, findings, tests, health, status, dq)
        if status == "INSUFFICIENT_EVIDENCE":
            summary.insert(0, "Host/link inventory alone does not establish service health. Collect reachability, loss/latency, DNS or throughput evidence.")
        summary = self._augment_summary(summary, m, context, hypotheses)

        sev_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.NOTICE: 2, Severity.INFO: 3}
        findings.sort(key=lambda x: (sev_order[x.severity], -x.confidence))
        return DiagnosticReport(
            status=status,
            health_score=health,
            data_quality_score=dq,
            findings=findings,
            hypotheses=hypotheses,
            next_tests=tests,
            summary=summary,
            normalized_metrics=m,
            engine_version=self.VERSION,
        )

    @staticmethod
    def _evidence_group(ev: Evidence) -> str:
        keys = set(ev.keys)
        families = []
        if keys & {"rsrp", "rsrq", "sinr", "lte_rsrp", "lte_rsrq", "lte_sinr", "nr_rsrp", "nr_rsrq", "nr_sinr", "lte_band", "nr_band", "pci", "lte_pci", "nr_pci", "earfcn", "nrarfcn", "lte_earfcn", "nr_nrarfcn"}:
            families.append("rf")
        if keys & {"latency_ms", "gateway_latency_ms", "packet_loss_pct", "jitter_ms", "gateway_reachable", "internet_reachable"}:
            families.append("transport")
        if keys & {"download_mbps", "upload_mbps"}:
            families.append("performance")
        if any(k.startswith("sdr_") for k in keys):
            families.append("sdr")
        if any(k.startswith("satellite_") or k.startswith("starlink_") for k in keys):
            families.append("satellite")
        if any(k.startswith("wifi_") for k in keys):
            families.append("wifi")
        if any(k.startswith("baseline_") for k in keys):
            families.append("baseline")
        if "dns_success" in keys or "dns_latency_ms" in keys:
            families.append("dns")
        if "mtu" in keys or any(k.startswith("pmtu_") for k in keys):
            families.append("mtu")
        if "modem_registered" in keys or "apn_attached" in keys or "sim_ready" in keys:
            families.append("registration")
        if not families:
            return "other"
        if len(families) > 1:
            return "cross:" + "+".join(sorted(set(families)))
        return families[0]

    def _rank_hypotheses(self, evidence: Sequence[Evidence]) -> List[Hypothesis]:
        hs = {
            hid: Hypothesis(hid, title, domain, prior)
            for hid, (title, domain, prior) in self.HYPOTHESIS_CATALOG.items()
        }
        for ev in evidence:
            if ev.hypothesis_id in hs:
                hs[ev.hypothesis_id].evidence.append(ev)

        qfactor = {Quality.LOW: 0.65, Quality.MEDIUM: 0.85, Quality.HIGH: 1.0}
        for h in hs.values():
            if not h.evidence:
                continue
            # Prevent five statements derived from the same measurement family
            # from masquerading as five independent observations.  Keep the
            # strongest support and contradiction inside each evidence group.
            support_groups: Dict[str, float] = defaultdict(float)
            contradict_groups: Dict[str, float] = defaultdict(float)
            for ev in h.evidence:
                group = self._evidence_group(ev)
                weighted = max(0.0, ev.weight) * qfactor[ev.quality]
                if ev.direction == Direction.SUPPORT:
                    support_groups[group] = max(support_groups[group], weighted)
                else:
                    contradict_groups[group] = max(contradict_groups[group], weighted)
            h.support = sum(support_groups.values())
            h.contradiction = sum(contradict_groups.values())
            net = h.support - h.contradiction
            logit_prior = math.log(max(h.prior, 0.01) / max(1.0 - h.prior, 0.01))
            raw = logit_prior + 0.58 * net
            h.confidence = 1.0 / (1.0 + math.exp(-raw))
            if h.confidence >= 0.78:
                h.status = "strong"
            elif h.confidence >= 0.52:
                h.status = "plausible"
            elif h.confidence >= self.profile.minimum_hypothesis_confidence:
                h.status = "possible"
            else:
                h.status = "weak"
        ranked = [h for h in hs.values() if h.evidence]
        ranked.sort(key=lambda h: (h.confidence, h.support, -h.contradiction), reverse=True)
        return ranked

    def _satellite_reasoning(self, m, findings, evidence) -> None:
        registered = m.get("satellite_registered")
        obstruction = _f(m.get("satellite_obstructed_pct"))
        snr = _f(m.get("satellite_snr_db"))
        latency = _f(m.get("satellite_latency_ms"))
        loss = _f(m.get("satellite_packet_loss_pct"))

        if registered is False:
            self._finding(findings, "SAT-001", Severity.CRITICAL, Domain.SATELLITE,
                          "Satellite terminal is not registered / online",
                          "The satellite adapter reports registration/online state false.",
                          "The failure is before normal routed-service validation.",
                          "Check terminal state, sky visibility, alignment/obstruction reporting, power, cabling, provisioning, and provider status.",
                          0.96, ["satellite_registered"])
            self._evidence(evidence, "satellite_visibility", Direction.SUPPORT, 4.2,
                           "Satellite terminal is not registered/online.", ["satellite_registered"])
        elif registered is True:
            self._evidence(evidence, "satellite_visibility", Direction.CONTRADICT, 2.6,
                           "Satellite terminal is registered/online.", ["satellite_registered"])

        if obstruction is not None:
            if obstruction >= 10:
                self._finding(findings, "SAT-002", Severity.WARNING, Domain.SATELLITE,
                              "Material satellite sky obstruction",
                              f"Terminal reports {obstruction:.1f}% obstruction.",
                              "Obstruction can create intermittent loss, latency spikes, and service interruption even when average signal metrics look acceptable.",
                              "Compare obstruction map/placement and correlate dropouts with obstruction events before blaming downstream transport.",
                              0.93, ["satellite_obstructed_pct"])
                self._evidence(evidence, "satellite_visibility", Direction.SUPPORT, 4.0,
                               "Terminal reports material sky obstruction.", ["satellite_obstructed_pct"])
            elif obstruction <= 1:
                self._evidence(evidence, "satellite_visibility", Direction.CONTRADICT, 2.5,
                               "Reported obstruction is minimal.", ["satellite_obstructed_pct"])

        if registered is True and latency is not None and latency >= self.profile.latency_warn_ms:
            self._evidence(evidence, "satellite_transport", Direction.SUPPORT, 2.7,
                           f"Satellite path latency is elevated ({latency:.1f} ms) while terminal is online.",
                           ["satellite_registered", "satellite_latency_ms"])
        if registered is True and loss is not None and loss >= self.profile.loss_warn_pct:
            self._evidence(evidence, "satellite_transport", Direction.SUPPORT, 3.2,
                           f"Satellite path loss is elevated ({loss:.2f}%) while terminal is online.",
                           ["satellite_registered", "satellite_packet_loss_pct"])
        # No universal SNR thresholds are imposed because terminal families can
        # report differently. Baseline comparison below is the preferred method.
        if snr is not None:
            pass

    def _starlink_reasoning(self, m, findings, evidence, baseline) -> None:
        if str(m.get("satellite_provider") or "").lower() != "starlink" and not any(
            str(k).startswith("starlink_") for k in m
        ):
            return

        state = str(m.get("starlink_state") or "UNKNOWN").upper()
        obstruction = _f(m.get("satellite_obstructed_pct"))
        currently_obstructed = m.get("starlink_currently_obstructed")
        latency = _f(m.get("starlink_pop_ping_latency_ms"))
        drop_pct = _f(m.get("satellite_packet_loss_pct"))
        alert_count = int(_f(m.get("starlink_active_alert_count")) or 0)
        active_alerts = m.get("starlink_active_alerts") or []
        if not isinstance(active_alerts, list):
            active_alerts = [str(active_alerts)]

        visibility_states = {"SEARCHING", "NO_SATS", "OBSTRUCTED", "NO_SCHEDULE"}
        transport_states = {"NO_DOWNLINK", "NO_PINGS"}
        terminal_states = {"THERMAL_SHUTDOWN"}

        if state == "CONNECTED":
            self._evidence(evidence, "starlink_terminal", Direction.CONTRADICT, 2.8,
                           "Starlink terminal reports CONNECTED state.", ["starlink_state"])
        elif state in visibility_states:
            self._finding(findings, "STARLINK-001", Severity.CRITICAL, Domain.SATELLITE,
                          f"Starlink terminal state: {state}",
                          f"The Starlink terminal reports {state} rather than CONNECTED.",
                          "The terminal is not maintaining normal constellation service and the state is consistent with sky visibility/scheduling acquisition trouble.",
                          "Inspect sky view and obstruction telemetry first; then verify terminal power, cabling, provisioning, and whether the state persists after a clean placement comparison.",
                          0.97, ["starlink_state"])
            self._evidence(evidence, "starlink_obstruction", Direction.SUPPORT, 4.7,
                           f"Terminal state {state} supports a Starlink visibility/acquisition problem.", ["starlink_state"])
        elif state in transport_states:
            self._finding(findings, "STARLINK-002", Severity.CRITICAL, Domain.SATELLITE,
                          f"Starlink service state: {state}",
                          f"The terminal reports {state}.",
                          "The terminal has progressed beyond simple local Ethernet visibility but is not sustaining the expected network path.",
                          "Correlate obstruction, active alerts, Starlink PoP latency/drop and an independent internet path test before assigning the fault downstream.",
                          0.95, ["starlink_state"])
            self._evidence(evidence, "starlink_pop_path", Direction.SUPPORT, 4.4,
                           f"Terminal state {state} indicates Starlink access/path impairment.", ["starlink_state"])
        elif state in terminal_states:
            self._finding(findings, "STARLINK-003", Severity.CRITICAL, Domain.SATELLITE,
                          "Starlink terminal thermal shutdown",
                          "The terminal reports THERMAL_SHUTDOWN.",
                          "The terminal itself has stopped normal service because of its thermal state.",
                          "Correct the thermal/environmental condition and validate power/installation before troubleshooting downstream networking.",
                          0.99, ["starlink_state"])
            self._evidence(evidence, "starlink_terminal", Direction.SUPPORT, 5.0,
                           "Terminal reports thermal shutdown.", ["starlink_state"])
        elif state not in {"UNKNOWN", "CONNECTED"}:
            self._evidence(evidence, "starlink_terminal", Direction.SUPPORT, 2.0,
                           f"Terminal is not in CONNECTED state ({state}).", ["starlink_state"])

        # Starlink can be materially affected by much smaller obstruction fractions
        # than the generic 10% satellite threshold. Keep severity proportional and
        # prefer correlation with drops/current obstruction over a single number.
        if currently_obstructed is True:
            self._finding(findings, "STARLINK-010", Severity.WARNING, Domain.SATELLITE,
                          "Starlink is currently obstructed",
                          "The terminal reports an active obstruction condition now.",
                          "A line-of-sight blockage is contemporaneous with the measurement and can directly create packet loss/latency excursions.",
                          "Relocate/reorient the terminal or remove the obstruction, then repeat the same path test to verify causality.",
                          0.98, ["starlink_currently_obstructed"])
            self._evidence(evidence, "starlink_obstruction", Direction.SUPPORT, 5.0,
                           "Terminal reports that it is currently obstructed.", ["starlink_currently_obstructed"])

        if obstruction is not None:
            if obstruction >= 5.0:
                sev, weight, conf = Severity.CRITICAL, 4.8, 0.97
            elif obstruction >= 1.0:
                sev, weight, conf = Severity.WARNING, 3.8, 0.94
            elif obstruction >= 0.1:
                sev, weight, conf = Severity.NOTICE, 2.0, 0.82
            else:
                sev = None
                weight = conf = 0.0
                self._evidence(evidence, "starlink_obstruction", Direction.CONTRADICT, 3.0,
                               f"Starlink obstruction fraction is very low ({obstruction:.3f}%).",
                               ["satellite_obstructed_pct"])
            if sev is not None:
                self._finding(findings, "STARLINK-011", sev, Domain.SATELLITE,
                              "Starlink sky obstruction detected",
                              f"Reported obstruction is {obstruction:.3f}%.",
                              "Even intermittent obstruction can cause transient Starlink dropouts; the diagnostic value becomes much stronger when loss events correlate with obstruction.",
                              "Compare placement/obstruction map and repeat latency/loss tests after improving sky view.",
                              conf, ["satellite_obstructed_pct"])
                self._evidence(evidence, "starlink_obstruction", Direction.SUPPORT, weight,
                               f"Starlink reports {obstruction:.3f}% sky obstruction.", ["satellite_obstructed_pct"])

        if latency is not None:
            # POP latency is an access-network measure, not arbitrary internet RTT.
            if latency >= 250:
                self._finding(findings, "STARLINK-020", Severity.WARNING, Domain.SATELLITE,
                              "Very high Starlink PoP latency",
                              f"Terminal-reported PoP latency is {latency:.1f} ms.",
                              "Delay is already high inside the Starlink access path, before an independent downstream internet/corporate path is considered.",
                              "Repeat over time and correlate with obstruction/drop state; compare against the site's established Starlink baseline.",
                              0.93, ["starlink_pop_ping_latency_ms"])
                self._evidence(evidence, "starlink_pop_path", Direction.SUPPORT, 4.0,
                               f"Starlink PoP latency is very high ({latency:.1f} ms).", ["starlink_pop_ping_latency_ms"])
            elif latency <= 100:
                self._evidence(evidence, "starlink_pop_path", Direction.CONTRADICT, 1.8,
                               f"Starlink PoP latency is not elevated ({latency:.1f} ms).", ["starlink_pop_ping_latency_ms"])

        if drop_pct is not None:
            if drop_pct >= 5.0:
                sev, weight, conf = Severity.CRITICAL, 4.8, 0.97
            elif drop_pct >= 1.0:
                sev, weight, conf = Severity.WARNING, 3.6, 0.93
            elif drop_pct >= 0.2:
                sev, weight, conf = Severity.NOTICE, 1.8, 0.80
            else:
                sev = None
                weight = conf = 0.0
                self._evidence(evidence, "starlink_pop_path", Direction.CONTRADICT, 2.2,
                               f"Starlink terminal-reported ping drop is low ({drop_pct:.2f}%).",
                               ["satellite_packet_loss_pct"])
            if sev is not None:
                self._finding(findings, "STARLINK-021", sev, Domain.SATELLITE,
                              "Starlink access-path packet drop",
                              f"Terminal-reported PoP ping drop is {drop_pct:.2f}%.",
                              "Loss is occurring within the Starlink access measurement and may explain application instability without requiring a downstream WAN fault.",
                              "Correlate with obstruction and terminal state; then compare Starlink PoP behavior with public/corporate path loss.",
                              conf, ["satellite_packet_loss_pct"])
                self._evidence(evidence, "starlink_pop_path", Direction.SUPPORT, weight,
                               f"Starlink PoP ping drop is {drop_pct:.2f}%.", ["satellite_packet_loss_pct"])

        if alert_count > 0:
            severe_tokens = ("thermal", "water", "motor", "mast", "power", "ethernet", "slow_ethernet")
            severe = [a for a in active_alerts if any(tok in str(a).lower() for tok in severe_tokens)]
            sev = Severity.WARNING if severe else Severity.NOTICE
            self._finding(findings, "STARLINK-030", sev, Domain.SATELLITE,
                          "Starlink terminal has active alerts",
                          f"Active alerts ({alert_count}): {', '.join(map(str, active_alerts[:8])) or 'alert bit(s) set'}.",
                          "Terminal alerts provide direct device-side context and can supersede generic WAN assumptions when they align with the observed symptom.",
                          "Resolve or document the terminal alert(s), then repeat the affected network test before escalating to downstream transport.",
                          0.94, ["starlink_active_alert_count", "starlink_active_alerts"])
            self._evidence(evidence, "starlink_terminal", Direction.SUPPORT, 4.0 if severe else 2.2,
                           "Starlink terminal reports active device alerts.", ["starlink_active_alert_count"])

        # Expert localization: healthy Starlink edge but bad external path shifts
        # suspicion downstream; poor Starlink PoP with clean sky shifts it inward.
        internet_latency = _f(m.get("latency_ms"))
        internet_loss = _f(m.get("packet_loss_pct"))
        if state == "CONNECTED" and obstruction is not None and obstruction < 0.1 and latency is not None:
            if latency <= 100 and internet_latency is not None and internet_latency >= max(180.0, latency * 2.5):
                self._finding(findings, "STARLINK-X01", Severity.WARNING, Domain.WAN,
                              "Latency increase occurs after the Starlink access path",
                              f"Starlink PoP latency is {latency:.1f} ms while end-to-end latency is {internet_latency:.1f} ms; obstruction is {obstruction:.3f}%.",
                              "The terminal and immediate Starlink access path appear comparatively healthy, so most excess delay is accumulating farther downstream.",
                              "Inspect internet route, VPN/SD-WAN, corporate ingress, or application path before changing dish placement.",
                              0.95, ["starlink_pop_ping_latency_ms", "latency_ms", "satellite_obstructed_pct"])
                self._evidence(evidence, "wan_path", Direction.SUPPORT, 4.2,
                               "Healthy Starlink edge with much higher end-to-end latency localizes delay downstream.",
                               ["starlink_pop_ping_latency_ms", "latency_ms"])
                self._evidence(evidence, "starlink_obstruction", Direction.CONTRADICT, 3.5,
                               "Very low obstruction and healthy PoP latency argue against dish placement as the primary cause.",
                               ["satellite_obstructed_pct", "starlink_pop_ping_latency_ms"])

        if state == "CONNECTED" and obstruction is not None and obstruction < 0.1 and drop_pct is not None and drop_pct < 0.2:
            if internet_loss is not None and internet_loss >= self.profile.loss_warn_pct:
                self._evidence(evidence, "wan_path", Direction.SUPPORT, 4.0,
                               "External packet loss is elevated while Starlink PoP drop and obstruction are low.",
                               ["packet_loss_pct", "satellite_packet_loss_pct", "satellite_obstructed_pct"])
                self._evidence(evidence, "starlink_pop_path", Direction.CONTRADICT, 3.0,
                               "Low Starlink PoP drop argues against the satellite access path as the source of external loss.",
                               ["satellite_packet_loss_pct"])

        # Baseline-aware Starlink changes are more defensible than universal RTT
        # thresholds because LEO path characteristics vary with geography/time.
        for key, hypothesis, label in (
            ("starlink_pop_ping_latency_ms", "starlink_pop_path", "PoP latency"),
            ("satellite_packet_loss_pct", "starlink_pop_path", "PoP ping drop"),
            ("satellite_obstructed_pct", "starlink_obstruction", "obstruction"),
        ):
            current = _f(m.get(key))
            b = baseline.get(key) if isinstance(baseline, Mapping) else None
            if current is None or not isinstance(b, Mapping):
                continue
            med = _f(b.get("median"))
            mad = _f(b.get("mad"))
            n = int(_f(b.get("n")) or 0)
            if med is None or n < 5:
                continue
            floor = 0.5 if key == "satellite_packet_loss_pct" else (0.2 if key == "satellite_obstructed_pct" else 10.0)
            scale = max((mad or 0.0) * 3.0, floor)
            if current > med + scale:
                self._evidence(evidence, hypothesis, Direction.SUPPORT, 2.8,
                               f"Starlink {label} is materially above the site baseline ({current:.2f} vs median {med:.2f}, n={n}).",
                               [key])

    def _sdr_reasoning(self, m, findings, evidence, baseline) -> None:
        labels = set()
        for key in m:
            mm = re.match(r"sdr_(.+)_median_db$", key)
            if mm:
                labels.add(mm.group(1))
        for label in sorted(labels):
            med_key = f"sdr_{label}_median_db"
            peak_key = f"sdr_{label}_peak_excess_db"
            occ_key = f"sdr_{label}_occupancy_pct"
            peakfreq_key = f"sdr_{label}_peak_freq_mhz"
            med = _f(m.get(med_key))
            excess = _f(m.get(peak_key))
            occ = _f(m.get(occ_key))
            # Single sweep: call out only conspicuous relative concentration,
            # not "interference" as a root cause.
            if excess is not None and excess >= 18.0:
                self._finding(findings, f"SDR-{label}-PEAK", Severity.NOTICE, Domain.SDR,
                              f"Concentrated RF energy detected in {label}",
                              f"Strongest bin is {excess:.1f} dB above the sweep median" +
                              (f" near {float(m[peakfreq_key]):.3f} MHz." if m.get(peakfreq_key) is not None else "."),
                              "The sweep contains a strong narrow/clustered emitter relative to the surrounding captured spectrum. A receive-only sweep alone cannot establish that it is harmful interference.",
                              "Compare against a known-good baseline and correlate the emitter with the affected service frequency/time window.",
                              0.73, [med_key, peak_key, peakfreq_key])
            bmed = baseline.get(med_key) if isinstance(baseline, Mapping) else None
            bocc = baseline.get(occ_key) if isinstance(baseline, Mapping) else None
            if med is not None and isinstance(bmed, Mapping) and bmed.get("n", 0) >= 5:
                delta = med - float(bmed["median"])
                if delta >= 8.0:
                    self._finding(findings, f"SDR-{label}-BASE", Severity.WARNING, Domain.SDR,
                                  f"RF floor elevated versus site baseline in {label}",
                                  f"Current sweep median is {med:.1f} dB, {delta:+.1f} dB relative to the site median.",
                                  "A broad rise in received energy is consistent with a changed RF environment, gain/antenna change, or new emitter population. Because HackRF sweep values are relative receiver measurements, configuration consistency matters.",
                                  "Confirm identical antenna/gain configuration, then correlate with service degradation and inspect the strongest changed frequencies.",
                                  0.88, [med_key, f"baseline_{med_key}"])
                    self._evidence(evidence, "sdr_interference", Direction.SUPPORT, 3.8,
                                   f"{label} RF median is {delta:.1f} dB above its established baseline.",
                                   [med_key, f"baseline_{med_key}"])
            if occ is not None and isinstance(bocc, Mapping) and bocc.get("n", 0) >= 5:
                delta_occ = occ - float(bocc["median"])
                if delta_occ >= 20.0:
                    self._evidence(evidence, "sdr_interference", Direction.SUPPORT, 3.0,
                                   f"{label} spectral occupancy is {delta_occ:.1f} percentage points above baseline.",
                                   [occ_key, f"baseline_{occ_key}"])

    def _staged_path_reasoning(self, m, findings, evidence) -> None:
        stages = []
        for key, value in m.items():
            mm = re.match(r"stage_(.+)_latency_ms$", key)
            if mm and isinstance(value, (int, float)):
                label = mm.group(1)
                loss = _f(m.get(f"stage_{label}_loss_pct"))
                stages.append((label, float(value), loss))
        if len(stages) < 2:
            return
        # Preserve rough configured execution order through dict insertion when
        # possible; otherwise identify largest adjacent jump in collected values.
        largest = None
        for i in range(1, len(stages)):
            prev, cur = stages[i - 1], stages[i]
            jump = cur[1] - prev[1]
            if largest is None or jump > largest[0]:
                largest = (jump, prev, cur)
        if largest and largest[0] >= 50:
            jump, prev, cur = largest
            self._finding(findings, "PATH-STAGE-001", Severity.WARNING, Domain.WAN,
                          "Latency jump localized between path stages",
                          f"Latency rises by about {jump:.1f} ms from {prev[0]} ({prev[1]:.1f} ms) to {cur[0]} ({cur[1]:.1f} ms).",
                          "A staged path test has localized where a material portion of delay appears, which is stronger evidence than end-to-end latency alone.",
                          f"Investigate routing, queueing, tunnel, carrier, or policy between the {prev[0]} and {cur[0]} stages.",
                          0.94, [f"stage_{prev[0]}_latency_ms", f"stage_{cur[0]}_latency_ms"])
            self._evidence(evidence, "wan_path", Direction.SUPPORT, 4.2,
                           f"Staged testing localizes a {jump:.1f} ms latency increase between {prev[0]} and {cur[0]}.",
                           [f"stage_{prev[0]}_latency_ms", f"stage_{cur[0]}_latency_ms"])

    def _baseline_reasoning(self, m, findings, evidence, baseline) -> None:
        if not isinstance(baseline, Mapping) or not baseline:
            return

        def bval(key: str) -> Optional[float]:
            b = baseline.get(key)
            if isinstance(b, Mapping) and float(b.get("n", 0)) >= 5 and b.get("median") is not None:
                return float(b["median"])
            return None

        rsrp, sinr, rsrq = _f(m.get("rsrp")), _f(m.get("sinr")), _f(m.get("rsrq"))
        dl, lat = _f(m.get("download_mbps")), _f(m.get("latency_ms"))
        brsrp, bsinr, brsrq = bval("rsrp"), bval("sinr"), bval("rsrq")
        bdl, blat = bval("download_mbps"), bval("latency_ms")

        # Stable signal power + degraded quality/performance -> interference/load.
        if None not in (rsrp, brsrp, sinr, bsinr):
            d_rsrp = rsrp - brsrp
            d_sinr = sinr - bsinr
            if abs(d_rsrp) <= 4.0 and d_sinr <= -8.0:
                self._finding(findings, "BASE-RF-001", Severity.WARNING, Domain.RAN,
                              "Radio quality deteriorated without comparable signal-power loss",
                              f"RSRP is only {d_rsrp:+.1f} dB from baseline, while SINR is {d_sinr:+.1f} dB from baseline.",
                              "The received signal power is broadly stable, but quality has deteriorated. That pattern argues against simple path loss and toward interference, overlap, loading, or changed radio conditions.",
                              "Compare serving cell/band and SDR spectrum to the established good baseline; repeat at another time/location.",
                              0.95, ["rsrp", "sinr", "baseline_rsrp", "baseline_sinr"])
                self._evidence(evidence, "ran_interference_or_load", Direction.SUPPORT, 4.8,
                               "SINR fell sharply from site baseline while RSRP stayed stable.",
                               ["rsrp", "sinr", "baseline_rsrp", "baseline_sinr"])
                self._evidence(evidence, "weak_coverage", Direction.CONTRADICT, 3.6,
                               "RSRP remains near its historical baseline.", ["rsrp", "baseline_rsrp"])

        # Large RSRP deterioration with relatively preserved quality -> path/antenna.
        if None not in (rsrp, brsrp, sinr, bsinr):
            d_rsrp = rsrp - brsrp
            d_sinr = sinr - bsinr
            if d_rsrp <= -8.0 and d_sinr >= -4.0:
                self._finding(findings, "BASE-RF-002", Severity.WARNING, Domain.CELLULAR_RF,
                              "Signal power has materially fallen versus site baseline",
                              f"RSRP is {d_rsrp:+.1f} dB from baseline while SINR changed {d_sinr:+.1f} dB.",
                              "A broad signal-power loss without an equally severe quality collapse is compatible with placement, obstruction, antenna/feedline loss, or changed serving-cell geometry.",
                              "Inspect antenna/feedline/placement and verify whether the serving cell or band changed before escalating carrier-side.",
                              0.91, ["rsrp", "sinr", "baseline_rsrp", "baseline_sinr"])
                self._evidence(evidence, "antenna_feedline", Direction.SUPPORT, 4.0,
                               "RSRP dropped substantially from baseline without equivalent SINR collapse.",
                               ["rsrp", "sinr", "baseline_rsrp", "baseline_sinr"])
                self._evidence(evidence, "weak_coverage", Direction.SUPPORT, 2.5,
                               "Current signal power is substantially below this site's normal level.",
                               ["rsrp", "baseline_rsrp"])

        # Healthy-ish RF relative to normal, but throughput collapses.
        if None not in (dl, bdl) and bdl > 1:
            ratio = dl / bdl
            stable_rf = True
            if None not in (rsrp, brsrp):
                stable_rf &= abs(rsrp - brsrp) <= 5
            if None not in (sinr, bsinr):
                stable_rf &= (sinr - bsinr) >= -5
            if ratio <= 0.35 and stable_rf:
                self._finding(findings, "BASE-PERF-001", Severity.WARNING, Domain.CARRIER_CORE,
                              "Throughput collapsed relative to site baseline while RF remained similar",
                              f"Download is {dl:.1f} Mbps versus a baseline median of {bdl:.1f} Mbps ({ratio:.0%} of normal).",
                              "This site's own history makes simple weak coverage a less compelling explanation than load, scheduling, policy, core/WAN path, or endpoint/test-target effects.",
                              "Run staged latency/loss tests and repeat throughput to multiple controlled targets while capturing serving-cell state.",
                              0.95, ["download_mbps", "baseline_download_mbps", "rsrp", "sinr"])
                self._evidence(evidence, "carrier_or_core_path", Direction.SUPPORT, 4.4,
                               "Throughput is far below site baseline while RF remains near normal.",
                               ["download_mbps", "baseline_download_mbps", "rsrp", "sinr"])

        if None not in (lat, blat) and (lat - blat) >= 80.0:
            self._finding(findings, "BASE-WAN-001", Severity.WARNING, Domain.WAN,
                          "Latency materially exceeds site baseline",
                          f"Current latency is {lat:.1f} ms versus baseline {blat:.1f} ms ({lat-blat:+.1f} ms).",
                          "The path is behaving abnormally for this site even if a generic threshold would consider the latency borderline.",
                          "Use staged path measurements to identify where the additional delay begins.",
                          0.90, ["latency_ms", "baseline_latency_ms"])

    def _case_reasoning(self, m, findings, evidence, matches) -> None:
        if not matches:
            return
        best = matches[0]
        sim = float(best.get("similarity", 0.0))
        hid = best.get("hypothesis_id")
        if sim >= 0.78:
            self._finding(findings, "CASE-001", Severity.INFO, Domain.UNKNOWN,
                          "Current signature resembles a confirmed prior case",
                          f"Case {best.get('case_id')} similarity is {sim:.0%}; prior confirmed cause: {best.get('cause')}.",
                          "Historical similarity is supporting context, not proof. Repeated local patterns can shorten troubleshooting when corroborated by current measurements.",
                          "Use the prior resolution as a targeted check, then confirm with current evidence before changing production configuration.",
                          min(0.90, sim), [])
            if hid in self.HYPOTHESIS_CATALOG:
                self._evidence(evidence, str(hid), Direction.SUPPORT, 2.0,
                               f"A confirmed historical case with a similar metric signature ({sim:.0%}) had this cause.",
                               ["baseline_case_match"], Quality.MEDIUM)

    def _augment_tests(self, m, hypotheses, tests, context) -> List[NextTest]:
        out = list(tests)
        top = {h.hypothesis_id for h in hypotheses[:5]}

        def add(t: NextTest):
            if not any(x.test_id == t.test_id for x in out):
                out.append(t)

        if "sdr_interference" in top or "ran_interference_or_load" in top:
            add(NextTest(
                "TEST-SDR-COMPARE",
                "Run a matched HackRF spectrum comparison",
                "Determine whether the RF environment changed in the service-relevant band.",
                "Repeat a receive-only HackRF sweep using the same antenna, gain, bin width, range, and physical position as the site baseline.",
                "A broad floor/occupancy rise or new persistent peak that coincides with service degradation strengthens the interference hypothesis; a stable spectrum weakens it.",
                1, 0.92, [Domain.SDR, Domain.RAN]
            ))
        if "starlink_obstruction" in top:
            add(NextTest(
                "TEST-STARLINK-SKY",
                "Validate Starlink sky view against live drop behavior",
                "Determine whether obstruction is actually driving the service impairment.",
                "Capture Starlink obstruction/current-obstruction state while running the same bounded latency/loss test; then repeat after improving terminal sky view without changing the downstream network.",
                "If obstruction and Starlink PoP drop improve together, sky visibility is causal; if obstruction clears but PoP impairment remains, shift toward the Starlink access path/terminal.",
                1, 0.97, [Domain.SATELLITE]
            ))
        if "starlink_pop_path" in top:
            add(NextTest(
                "TEST-STARLINK-PATH",
                "Localize Starlink PoP versus downstream WAN impairment",
                "Separate Starlink access-network degradation from internet/VPN/corporate path degradation.",
                "Compare terminal-reported Starlink PoP latency/drop with default-gateway, public-IP, and corporate/tunnel endpoint tests captured in the same interval.",
                "High Starlink PoP impairment points into the satellite/access path; healthy PoP with degraded external targets shifts the fault downstream.",
                1, 0.98, [Domain.SATELLITE, Domain.WAN]
            ))
        if "starlink_terminal" in top:
            add(NextTest(
                "TEST-STARLINK-TERMINAL",
                "Recheck Starlink state and active terminal alerts",
                "Confirm whether device-side alerts or terminal state persist independently of downstream traffic.",
                "Capture two read-only Starlink status snapshots around the failing test and compare state, alert set, uptime, obstruction, and PoP statistics.",
                "Persistent device alerts/state changes support a terminal-side cause; a stable clean terminal shifts focus to access or downstream transport.",
                1, 0.94, [Domain.SATELLITE]
            ))
        if "satellite_visibility" in top:
            add(NextTest(
                "TEST-SAT-VIS",
                "Compare satellite obstruction / visibility state",
                "Separate terminal/sky-view issues from routed transport issues.",
                "Capture terminal online state, obstruction metric/map, signal metric, uptime/reconnect history, and compare at the time of impairment.",
                "Obstruction/reconnects aligned with packet loss support a visibility/RF cause; clean visibility shifts focus upstream.",
                1, 0.93, [Domain.SATELLITE]
            ))
        if "lte_anchor_impairment" in top:
            add(NextTest(
                "TEST-NSA-ANCHOR", "Compare the LTE anchor against the NR secondary leg",
                "Confirm whether the NSA control/anchor link is limiting an otherwise strong NR connection.",
                "Capture simultaneous LTE band/EARFCN/PCI/RSRP/RSRQ/SINR and NR band/NRARFCN/PCI/RSRP/RSRQ/SINR during idle and active traffic; repeat after an antenna/location A/B change.",
                "If the LTE anchor improves and session stability/performance improves while NR stays similar, the anchor is causal.",
                1, 0.99, [Domain.RAN, Domain.CELLULAR_RF]
            ))
        if "nr_secondary_impairment" in top:
            add(NextTest(
                "TEST-NSA-NR", "Validate the active NR secondary carrier under load",
                "Determine whether the weak NR leg is actually limiting user-plane performance.",
                "Run a bounded throughput/latency test while sampling NR assignment, band/NRARFCN/PCI and NR RF metrics; repeat at an alternate location without changing modem RAT/band configuration.",
                "Performance that tracks NR assignment/quality supports an NR-leg limitation; stable performance despite weak NR shifts focus elsewhere.",
                1, 0.98, [Domain.RAN, Domain.CELLULAR_RF]
            ))
        if "modem_thermal" in top:
            add(NextTest(
                "TEST-MODEM-THERMAL", "Repeat the same test after modem temperature stabilizes",
                "Determine whether temperature is correlated with degraded radio or throughput behavior.",
                "Record modem temperature and RF/performance metrics, improve airflow or allow the module to cool, then repeat the identical test.",
                "Improvement that tracks falling temperature supports thermal mitigation; unchanged behavior weakens it.",
                2, 0.88, [Domain.DEVICE, Domain.RAN]
            ))
        if "cell_change_instability" in top:
            add(NextTest(
                "TEST-CELL-STABILITY", "Track serving cell and band over time",
                "Detect ping-pong handovers or unstable LTE/NR anchoring.",
                "Sample cell ID/PCI, LTE/NR band, EARFCN/NRARFCN, EN-DC/CA state and RF metrics every few seconds during the issue.",
                "Repeated cell/band changes aligned with latency/loss indicate mobility/RAN instability.",
                2, 0.89, [Domain.RAN]
            ))
        out.sort(key=lambda t: (t.priority, -t.diagnostic_value))
        return out[:8]

    @staticmethod
    def _augment_summary(summary, m, context, hypotheses) -> List[str]:
        out = list(summary)
        baseline = context.get("baseline") or {}
        cases = context.get("case_matches") or []
        if baseline:
            out.append(f"Site-history reasoning is active using {len(baseline)} baseline metric(s).")
        else:
            out.append("No mature site baseline is available yet; repeated runs will improve contextual diagnosis.")
        if cases:
            out.append(f"Closest confirmed historical case match: {cases[0]['similarity']:.0%} similarity.")
        if m.get("sdr_present"):
            out.append("HackRF receive-only spectrum evidence is included; sweep power values are treated comparatively, not as calibrated absolute field-strength measurements.")
        if str(m.get("satellite_provider") or "").lower() == "starlink":
            backend = m.get("starlink_backend") or "management probe"
            state = m.get("starlink_state") or "unknown"
            out.append(f"Starlink terminal telemetry is included via {backend}; terminal state is {state}.")
        if m.get("modem_model") or m.get("cellular_driver"):
            vendor = m.get("modem_vendor") or "cellular"
            model = m.get("modem_model") or "modem"
            driver = m.get("cellular_driver") or m.get("cellular_adapter_level") or "adapter"
            tech = m.get("technology") or "unknown RAT"
            out.append(f"Cellular telemetry is included from {vendor} {model} via {driver}; current technology is {tech}.")
        return out


# =============================================================================
# REPORTING / EVIDENCE PACKS
# =============================================================================

def render_professional_console(report: DiagnosticReport, metadata: Optional[Mapping[str, Any]] = None) -> str:
    metadata = dict(metadata or {})
    lines: List[str] = []
    lines += ["=" * 88, f"{APP_NAME.upper()}  |  FIELD DIAGNOSTIC REPORT", "=" * 88]
    if metadata:
        for key in ("run_id", "site_id", "scenario", "timestamp"):
            if metadata.get(key):
                lines.append(f"{key.replace('_',' ').title():<12}: {metadata[key]}")
        lines.append("-")
    lines += [f"[+] {x}" for x in report.summary]

    lines += ["", "LIKELY CAUSES", "-" * 88]
    if not report.hypotheses:
        lines.append("No defensible root-cause hypothesis can be ranked from the available evidence.")
    else:
        for idx, h in enumerate(report.hypotheses[:7], 1):
            lines.append(f"{idx:>2}. {h.title:<52} {h.confidence:>6.0%}  [{h.status}]")
            support = [e for e in h.evidence if e.direction == Direction.SUPPORT]
            contradict = [e for e in h.evidence if e.direction == Direction.CONTRADICT]
            for ev in support[:3]:
                lines.append(f"      + {ev.statement}")
            for ev in contradict[:2]:
                lines.append(f"      - {ev.statement}")

    lines += ["", "ENGINEER'S FINDINGS", "-" * 88]
    if not report.findings:
        lines.append("No material finding was established.")
    else:
        for f in report.findings:
            lines += [
                f"[{f.severity.value.upper():8}] {f.finding_id}  {f.title}",
                f"  Seen : {f.observation}",
                f"  Means: {f.interpretation}",
                f"  Next : {f.recommendation}",
                f"  Confidence: {f.confidence:.0%}",
                "",
            ]

    lines += ["NEXT BEST TESTS", "-" * 88]
    if not report.next_tests:
        lines.append("No additional test is currently recommended.")
    else:
        for idx, t in enumerate(report.next_tests, 1):
            lines += [
                f"{idx}. {t.title}  [diagnostic value {t.diagnostic_value:.0%}]",
                f"   Purpose : {t.purpose}",
                f"   Action  : {t.action}",
                f"   Decide  : {t.expected_signal}",
                "",
            ]
    return "\n".join(lines)


def report_to_html(report: DiagnosticReport, metadata: Mapping[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))
    hyp_rows = "".join(
        f"<tr><td>{i}</td><td>{esc(h.title)}</td><td>{h.confidence:.0%}</td><td>{esc(h.status)}</td></tr>"
        for i, h in enumerate(report.hypotheses[:8], 1)
    )
    finding_blocks = "".join(
        f"<section><h3>{esc(f.severity.value.upper())}: {esc(f.title)}</h3>"
        f"<p><b>Observed:</b> {esc(f.observation)}</p>"
        f"<p><b>Interpretation:</b> {esc(f.interpretation)}</p>"
        f"<p><b>Action:</b> {esc(f.recommendation)}</p>"
        f"<p><b>Confidence:</b> {f.confidence:.0%}</p></section>"
        for f in report.findings
    )
    test_blocks = "".join(
        f"<li><b>{esc(t.title)}</b> — {esc(t.purpose)}<br><span>{esc(t.action)}</span></li>"
        for t in report.next_tests
    )
    summaries = "".join(f"<li>{esc(x)}</li>" for x in report.summary)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Veilbreaker {esc(metadata.get('run_id',''))}</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#13202b}}h1{{margin-bottom:0}}.muted{{color:#617181}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:9px;text-align:left}}section{{border-left:4px solid #778899;padding-left:14px;margin:20px 0}}code{{background:#eef2f4;padding:2px 5px}}</style></head><body>
<h1>Veilbreaker Field Diagnostic Report</h1><p class='muted'>Run {esc(metadata.get('run_id'))} · Site {esc(metadata.get('site_id'))} · {esc(metadata.get('timestamp'))}</p>
<h2>Assessment</h2><ul>{summaries}</ul><h2>Likely causes</h2><table><tr><th>#</th><th>Hypothesis</th><th>Score</th><th>Status</th></tr>{hyp_rows}</table>
<h2>Findings</h2>{finding_blocks}<h2>Next best tests</h2><ol>{test_blocks}</ol></body></html>"""


def write_evidence_pack(config: AppConfig, run_id: str, metrics: Mapping[str, Any], report: DiagnosticReport,
                        notes: Sequence[str], sweep_summaries: Sequence[SweepSummary], collection=None) -> Path:
    run_dir = config.artifacts_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {"run_id": run_id, "site_id": config.site_id, "scenario": config.scenario, "timestamp": utcnow_iso()}
    (run_dir / "metrics.json").write_text(json.dumps(dict(metrics), indent=2, default=str) + "\n", encoding="utf-8")
    (run_dir / "report.json").write_text(report.to_json() + "\n", encoding="utf-8")
    (run_dir / "report.txt").write_text(render_professional_console(report, metadata) + "\n", encoding="utf-8")
    (run_dir / "report.html").write_text(report_to_html(report, metadata), encoding="utf-8")
    (run_dir / "collector_notes.txt").write_text("\n".join(notes) + ("\n" if notes else ""), encoding="utf-8")
    if sweep_summaries:
        (run_dir / "sdr_summaries.json").write_text(json.dumps([asdict(s) for s in sweep_summaries], indent=2) + "\n", encoding="utf-8")
        # Copy raw sweep files into the evidence pack if they were captured elsewhere.
        for s in sweep_summaries:
            p = Path(s.csv_path)
            if p.exists() and p.parent != run_dir:
                try:
                    shutil.copy2(p, run_dir / p.name)
                except Exception:
                    pass
    if collection is not None:
        (run_dir / "collection.json").write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
    from .evidence import write_manifest
    write_manifest(run_dir, metadata)
    zip_path = config.reports_dir / f"{run_id}_evidence.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in run_dir.iterdir():
            if p.is_file():
                zf.write(p, arcname=p.name)
    return zip_path


# =============================================================================
# APPLICATION ORCHESTRATOR
# =============================================================================

@dataclass
class RunResult:
    run_id: str
    metrics: Dict[str, Any]
    report: DiagnosticReport
    notes: List[str]
    evidence_zip: Path
    sweep_summaries: List[SweepSummary]
    collection: Dict[str, Any] = field(default_factory=dict)


class VeilbreakerApplication:
    def __init__(self, config: AppConfig, progress=None):
        from .acquisition import Acquisition
        self.progress = progress
        self.acquisition = Acquisition(progress)
        self.config = config
        self.config.root.mkdir(parents=True, exist_ok=True)
        self.config.reports_dir.mkdir(parents=True, exist_ok=True)
        self.config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.store = VeilbreakerStore(config.db_path)
        self.engine = ProfessionalVeilbreakerEngine(profile_for_scenario(config.scenario))

    def close(self) -> None:
        self.store.close()

    def collect_passive(self, include_starlink: bool = False, include_cellular: bool = False) -> Tuple[Dict[str, Any], List[str]]:
        metrics: Dict[str, Any] = {}
        notes: List[str] = []
        collectors: List[Collector] = [SystemCollector(), make_network_collector(), make_wifi_collector(), GPSDCollector()]
        if include_cellular or self.config.cellular.enabled:
            collectors.append(CellularModemCollector(self.config.cellular))
        if self.config.satellite.command:
            collectors.append(JSONCommandAdapter("satellite", self.config.satellite, prefix="satellite_"))
        if include_starlink or self.config.starlink.enabled:
            collectors.append(StarlinkCollector(self.config.starlink))
        for collector in collectors:
            required = not isinstance(collector, (GPSDCollector, LinuxWiFiCollector, WindowsWiFiCollector))
            complete = None
            expected = ()
            if isinstance(collector, CellularModemCollector):
                expected = (("modem_registered",), ("rsrp", "rssi"))
                complete = lambda result: any(result[0].get(k) is not None for k in
                    ("rsrp", "rsrq", "sinr", "rssi", "modem_registered", "apn_attached", "rat", "operator"))
            if isinstance(collector, StarlinkCollector):
                expected = (("starlink_state",), ("satellite_latency_ms",), ("satellite_packet_loss_pct",))
                complete = lambda result: any(k not in {"satellite_provider", "starlink_target", "starlink_management_reachable"} for k in result[0])
            part, n = self.acquisition.collect(collector.name, collector.collect, required=required, complete=complete, expected=expected)[:2]
            metrics.update(part)
            notes.extend(f"{collector.name}: {x}" for x in n)
        return metrics, notes

    @staticmethod
    def load_metrics_file(path: Optional[str]) -> Dict[str, Any]:
        if not path:
            return {}
        if path == "-":
            obj = json.load(sys.stdin)
        else:
            with open(path, "r", encoding="utf-8") as fh:
                obj = json.load(fh)
        if not isinstance(obj, Mapping):
            raise ValueError("Metrics input must be a JSON object")
        return dict(obj)

    def run(self, *, active: bool = False, sdr: bool = False, throughput: bool = False,
            guided: bool = False, starlink: bool = False, cellular: bool = False,
            metrics_file: Optional[str] = None, note: Optional[str] = None, run_id: Optional[str] = None) -> RunResult:
        from .acquisition import Acquisition, collection_summary
        self.acquisition = Acquisition(self.progress)
        run_id = run_id or (_dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
            raise ValueError("Invalid run identifier")
        if self.store.get_run(run_id):
            raise ValueError("Run identifier already exists")
        artifact_dir = self.config.artifacts_dir / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        from .recovery import checkpoint_writer
        self.acquisition.checkpoint = checkpoint_writer(artifact_dir / "recovery.json", self.config, run_id)
        self.acquisition.persist()

        metrics, notes = self.collect_passive(include_starlink=starlink, include_cellular=cellular)
        if metrics_file:
            imported = self.load_metrics_file(metrics_file)
            part, _ = self.acquisition.collect("imported_metrics", lambda: (imported, []))
            metrics.update(part)
        sweep_summaries: List[SweepSummary] = []

        if active:
            expected = []
            if metrics.get("gateway_ip") or metrics.get("gateway"):
                expected.append(("gateway_reachable",))
            if self.config.public_ping_target:
                expected.extend([("internet_reachable",), ("packet_loss_pct",)])
            if self.config.dns_test_host:
                expected.append(("dns_success",))
            part, n = self.acquisition.collect("active_network", ActiveNetworkCollector(self.config, metrics).collect, expected=expected)
            metrics.update(part)
            notes.extend(f"active_network: {x}" for x in n)

        if throughput:
            part, n = self.acquisition.collect("iperf3", ActiveTestExecutor(self.config).iperf3,
                                               expected=(("download_mbps",), ("upload_mbps",)))
            metrics.update(part)
            notes.extend(f"iperf3: {x}" for x in n)

        if sdr or self.config.sdr.enabled:
            hc = HackRFCollector(self.config.sdr, artifact_dir)
            captured = self.acquisition.collect("hackrf", hc.collect,
                complete=lambda result: bool(self.config.sdr.ranges) and len(result[2]) == len(self.config.sdr.ranges),
                expected=[(f"sdr_{re.sub(r'[^a-z0-9]+', '_', r.label.lower()).strip('_')}_median_db",) for r in self.config.sdr.ranges])
            part, n = captured[:2]
            summaries = captured[2] if len(captured) > 2 else []
            metrics.update(part)
            notes.extend(f"hackrf: {x}" for x in n)
            sweep_summaries.extend(summaries)

        baseline = self.store.baseline(
            self.config.site_id, self.config.scenario,
            limit=int(self.config.baseline_run_count), min_samples=int(self.config.baseline_min_samples),
        )
        case_matches = self.store.match_cases(metrics)
        context = {"baseline": baseline, "case_matches": case_matches}
        report = self.engine.analyze(metrics, context)

        # Guided mode executes only bounded, non-destructive tests that are
        # directly supported by this file. It does one additional reasoning pass.
        if guided:
            executor = ActiveTestExecutor(self.config)
            executed = False
            top_test_ids = [t.test_id for t in report.next_tests[:3]]
            if "TEST-PATH-STAGES" in top_test_ids or "TEST-STARLINK-PATH" in top_test_ids:
                part, n = self.acquisition.collect("guided_path", lambda: executor.path_stages(metrics))
                metrics.update(part)
                notes.extend(f"guided_path: {x}" for x in n)
                executed = True
            if "TEST-PMTU" in top_test_ids and self.config.public_ping_target:
                part, n = self.acquisition.collect("guided_pmtu", lambda: executor.path_mtu(self.config.public_ping_target),
                                                   complete=lambda result: result[0].get("pmtu_test_success") is True)
                metrics.update(part)
                notes.extend(f"guided_pmtu: {x}" for x in n)
                executed = True
            if executed:
                case_matches = self.store.match_cases(metrics)
                context["case_matches"] = case_matches
                report = self.engine.analyze(metrics, context)
                report.summary.append("Guided diagnostics executed one bounded follow-up test cycle and re-ranked the hypotheses.")

        collection = self.acquisition.to_dict()
        report.summary.append(collection_summary(collection))
        evidence_zip = write_evidence_pack(self.config, run_id, metrics, report, notes, sweep_summaries, collection)
        self.store.save_run(run_id, self.config.site_id, self.config.scenario, metrics, report,
                            artifact_dir=str(artifact_dir), note=note)
        return RunResult(run_id, metrics, report, notes, evidence_zip, sweep_summaries, collection)

    def analyze_file(self, path: str) -> RunResult:
        from .acquisition import Acquisition
        self.acquisition = Acquisition(self.progress)
        imported = self.load_metrics_file(path)
        metrics, _ = self.acquisition.collect("imported_metrics", lambda: (imported, []))
        run_id = "analysis-" + _dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        baseline = self.store.baseline(self.config.site_id, self.config.scenario,
                                       self.config.baseline_run_count, self.config.baseline_min_samples)
        cases = self.store.match_cases(metrics)
        report = self.engine.analyze(metrics, {"baseline": baseline, "case_matches": cases})
        zip_path = write_evidence_pack(self.config, run_id, metrics, report, [], [], self.acquisition.to_dict())
        self.store.save_run(run_id, self.config.site_id, self.config.scenario, metrics, report,
                            artifact_dir=str(self.config.artifacts_dir / run_id))
        return RunResult(run_id, metrics, report, [], zip_path, [], self.acquisition.to_dict())


# =============================================================================
# DOCTOR / SELF TESTS
# =============================================================================

def doctor(config: AppConfig) -> Tuple[int, str]:
    checks = []

    def ck(name: str, ok: bool, detail: str = ""):
        checks.append((name, ok, detail))

    ck("Python >= 3.9", sys.version_info >= (3, 9), platform.python_version())
    ck("Writable data directory", True, str(config.root))
    try:
        config.root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=config.root) as test:
            test.write(b"ok")
    except Exception as exc:
        checks[-1] = ("Writable data directory", False, str(exc))

    system = platform.system().lower()
    ck("Host platform", system in {"linux", "windows"}, f"{platform.system()} {platform.release()} ({platform.machine()})")
    ck("ping", command_exists("ping"), shutil.which("ping") or "not found")
    if system == "linux":
        ck("ip", command_exists("ip"), shutil.which("ip") or "not found")
        ck("iw (optional Wi-Fi)", command_exists("iw"), shutil.which("iw") or "not found")
    elif system == "windows":
        ck("PowerShell networking", _powershell_executable() is not None, _powershell_executable() or "not found; route.exe fallback will be used")
        ck("route.exe fallback", command_exists("route"), shutil.which("route") or "not found")
        ck("netsh (optional Wi-Fi)", command_exists("netsh"), shutil.which("netsh") or "not found")
    else:
        ck("Native network collector", False, f"{platform.system()} is not a primary supported platform")
    ck("iperf3 (optional throughput)", command_exists("iperf3"), shutil.which("iperf3") or "not found")
    hackrf = HackRFCollector(config.sdr, config.artifacts_dir / "doctor")
    ck("hackrf_info (optional SDR)", bool(hackrf.tool_path("hackrf_info")), hackrf.tool_path("hackrf_info") or "not found")
    ck("hackrf_sweep (optional SDR)", bool(hackrf.tool_path("hackrf_sweep")), hackrf.tool_path("hackrf_sweep") or "not found")

    if hackrf.tool_path("hackrf_info"):
        info, notes = hackrf.info()
        ck("HackRF detected", bool(info.get("sdr_present")), info.get("sdr_serial") or "; ".join(notes) or "no device")

    ck("pyserial (optional/recommended modem I/O)", _pyserial_available(), "installed" if _pyserial_available() else ("not installed; Linux POSIX fallback available" if system == "linux" else "install with: py -m pip install pyserial"))
    if system == "linux":
        ck("ModemManager/mmcli (optional discovery)", command_exists("mmcli"), shutil.which("mmcli") or "not found")
    modem_ports = list_serial_ports(include_unlikely=False)
    ck("Likely cellular modem port(s) (optional)", bool(modem_ports), ", ".join(p.device for p in modem_ports[:6]) if modem_ports else "none auto-identified")
    if config.cellular.enabled:
        probe, probe_notes = CellularModemCollector(config.cellular).probe()
        ck("Cellular modem AT probe", bool(probe), (f"{probe.get('model') or probe.get('identity')} via {probe.get('port')} [{probe.get('driver')}]" if probe else "; ".join(probe_notes[:3])))
    else:
        ck("Cellular modem enabled (optional)", False, "disabled by config; use --cellular or 'modem status' for one-shot collection")
    sl = StarlinkCollector(config.starlink)
    sl_avail = sl.backend_availability()
    ck("Starlink Python backend (optional)", sl_avail["python"], "starlink_grpc importable" if sl_avail["python"] else "not installed")
    ck("grpcurl Starlink backend (optional)", sl_avail["grpcurl"], shutil.which("grpcurl") or "not found")
    if config.starlink.enabled:
        reachable, detail = sl.probe()
        ck("Starlink management endpoint", reachable, detail)
    if config.satellite.command:
        ck("Generic satellite adapter executable", command_exists(config.satellite.command[0]), config.satellite.command[0])
    else:
        ck("Generic satellite adapter configured", False, "not required when native Starlink support is used")

    required_fail = any(not ok for name, ok, _ in checks if name in {"Python >= 3.9", "Writable data directory"})
    lines = ["VEILBREAKER DOCTOR", "=" * 72]
    for name, ok, detail in checks:
        state = "PASS" if ok else ("INFO" if "optional" in name.lower() or "configured" in name.lower() else "FAIL")
        lines.append(f"[{state:4}] {name:<34} {detail}")
    lines += ["", "Cellular and satellite hardware are optional. Native cellular AT collection is read-only; Starlink native support is also read-only."]
    if platform.system().lower() == "windows":
        lines.append("Windows note: HackRF tools must be installed and visible on PATH; the HackRF USB driver must expose the device to libusb/host tools.")
    return (1 if required_fail else 0), "\n".join(lines)


def selftest() -> Tuple[int, str]:
    engine = ProfessionalVeilbreakerEngine()
    failures = []

    def expect(name: str, metrics: Dict[str, Any], wanted: Sequence[str], context: Optional[Dict[str, Any]] = None):
        r = engine.analyze(metrics, context or {})
        tops = [h.hypothesis_id for h in r.hypotheses[:4]]
        if not any(x in tops for x in wanted):
            failures.append(f"{name}: expected one of {wanted}, got {tops}")

    expect("weak clean coverage", {
        "rsrp": -115, "rsrq": -12, "sinr": 17, "download_mbps": 4,
        "packet_loss_pct": 2.0, "modem_registered": True, "apn_attached": True,
    }, ["weak_coverage", "antenna_feedline"])

    expect("good RF poor throughput", {
        "rsrp": -78, "rsrq": -9, "sinr": 23, "download_mbps": 4,
        "upload_mbps": 18, "latency_ms": 150, "gateway_latency_ms": 12,
        "packet_loss_pct": 0.2, "modem_registered": True, "apn_attached": True,
    }, ["carrier_or_core_path", "throughput_degradation", "wan_path"])

    expect("dns isolation", {
        "dns_success": False, "internet_reachable": True, "gateway_reachable": True,
    }, ["dns_failure"])

    expect("local handoff", {
        "gateway_reachable": False, "internet_reachable": False,
    }, ["local_handoff"])

    expect("baseline interference pattern", {
        "rsrp": -88, "sinr": 5, "download_mbps": 20,
    }, ["ran_interference_or_load"], {
        "baseline": {
            "rsrp": {"n": 10, "median": -87, "mad": 2},
            "sinr": {"n": 10, "median": 18, "mad": 3},
            "download_mbps": {"n": 10, "median": 100, "mad": 15},
        }
    })

    expect("satellite obstruction", {
        "satellite_registered": True, "satellite_obstructed_pct": 25,
        "satellite_latency_ms": 300, "satellite_packet_loss_pct": 4,
    }, ["satellite_visibility", "satellite_transport"])

    # Validate HackRF parser against official CSV field shape.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sweep.csv"
        p.write_text("2019-01-03,11:57:34.967805,2400000000,2405000000,1000000.00,20,-64.72,-63.36,-60.91,-61.74,-58.58\n")
        bins = HackRFCollector.parse_sweep_csv(p)
        if len(bins) != 5 or abs(bins[0].hz - 2400500000) > 1:
            failures.append("HackRF CSV parser did not produce expected bins")

    windows_ping = """
Pinging 1.1.1.1 with 32 bytes of data:
Reply from 1.1.1.1: bytes=32 time=18ms TTL=55
Reply from 1.1.1.1: bytes=32 time=20ms TTL=55
Reply from 1.1.1.1: bytes=32 time=19ms TTL=55
Reply from 1.1.1.1: bytes=32 time=21ms TTL=55

Ping statistics for 1.1.1.1:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 18ms, Maximum = 21ms, Average = 19ms
"""
    wp = _parse_ping_output(windows_ping, system="windows", returncode=0)
    if not wp.reachable or wp.received != 4 or wp.avg_ms != 19.0 or wp.loss_pct != 0.0:
        failures.append("Windows ping parser fixture failed")

    windows_wlan = """
    Name                   : Wi-Fi
    State                  : connected
    SSID                   : VeilbreakerLab
    BSSID                  : aa:bb:cc:dd:ee:ff
    Radio type             : 802.11ax
    Authentication         : WPA2-Personal
    Cipher                 : CCMP
    Channel                : 36
    Receive rate (Mbps)    : 1201
    Transmit rate (Mbps)   : 1201
    Signal                 : 84%
"""
    ww = WindowsWiFiCollector._parse_interfaces(windows_wlan)
    if ww.get("wifi_ssid") != "VeilbreakerLab" or ww.get("wifi_signal_pct") != 84.0 or ww.get("wifi_channel") != 36:
        failures.append("Windows netsh Wi-Fi parser fixture failed")

    route_text = """
          0.0.0.0          0.0.0.0      192.168.1.1     192.168.1.55     25
"""
    wr = WindowsNetworkCollector._parse_route_print(route_text)
    if wr.get("gateway_ip") != "192.168.1.1" or wr.get("local_ipv4") != "192.168.1.55":
        failures.append("Windows route parser fixture failed")

    # Starlink grpcurl fixture/parser and reasoning test.
    star_fixture = {
        "dishGetStatus": {
            "deviceInfo": {"id": "ut-test", "hardwareVersion": "rev-test", "softwareVersion": "test.release"},
            "deviceState": {"uptimeS": "86400"},
            "popPingDropRate": 0.035,
            "downlinkThroughputBps": 12000000,
            "uplinkThroughputBps": 1500000,
            "popPingLatencyMs": 52.5,
            "obstructionStats": {"fractionObstructed": 0.018, "currentlyObstructed": True},
            "alerts": {"thermalThrottle": False, "slowEthernetSpeeds": True},
            "gpsStats": {"gpsValid": True, "inhibitGps": False, "gpsSats": 11}
        }
    }
    st, al = StarlinkCollector._status_from_grpcurl_json(star_fixture)
    sc = StarlinkCollector(StarlinkConfig())
    sm = sc._canonicalize(st, al, backend="selftest")
    if sm.get("starlink_state") != "CONNECTED" or abs(float(sm.get("satellite_obstructed_pct", 0)) - 1.8) > 0.01:
        failures.append(f"starlink parser: unexpected canonical metrics {sm}")
    sr = engine.analyze(sm, {})
    star_tops = [h.hypothesis_id for h in sr.hypotheses[:5]]
    if "starlink_obstruction" not in star_tops:
        failures.append(f"starlink reasoning: expected starlink_obstruction, got {star_tops}")


    # Generic 3GPP parser fixture.
    generic_rsp = {
        "AT+GMI": "AT+GMI\r\nExampleVendor\r\nOK\r\n",
        "AT+GMM": "AT+GMM\r\nExample5G\r\nOK\r\n",
        "AT+CPIN?": "\r\n+CPIN: READY\r\nOK\r\n",
        "AT+CEREG?": "\r\n+CEREG: 0,1\r\nOK\r\n",
        "AT+CSQ": "\r\n+CSQ: 20,99\r\nOK\r\n",
        "AT+CGDCONT?": '\r\n+CGDCONT: 1,"IPV4V6","internet","0.0.0.0",0,0\r\nOK\r\n',
    }
    gm = parse_generic_3gpp(generic_rsp)
    if gm.get("sim_ready") is not True or gm.get("modem_registered") is not True or gm.get("apn") != "internet" or gm.get("rssi") != -73:
        failures.append(f"generic modem parser: {gm}")

    # Sierra EM9190 GSTATUS/NRINFO fixture.
    sierra_rsp = dict(generic_rsp)
    sierra_rsp.update({
        "AT+GMI": "Sierra Wireless\r\nOK\r\n",
        "AT+GMM": "EM9190\r\nOK\r\n",
        "AT!GSTATUS?": """!GSTATUS:\nCurrent Time: 1730657 Temperature: 44\nSystem mode: ENDC PS state: Attached\nLTE band: B1 LTE bw: 20 MHz\nLTE Rx chan: 500 LTE Tx chan: 18500\nEMM state: Registered Normal Service\nRRC state: RRC Connected\nPCC RxM RSSI: -59 PCC RxM RSRP: -86\nPCC Tx Power: -20 TAC: bc7a (48250)\nRSRQ (dB): -7.8 Cell ID: 00066e2b (421419)\nSINR (dB): 14.2\nSCC1 NR5G band: n78 SCC1 NR5G bw: 90 MHz\nSCC1 NR5G Tx chan: 650332\nSCC1 NR5G Rx chan: 650332\nNR5G RSRP (dBm): -94 NR5G RSRQ (dB): -11\nNR5G SINR (dB): 19.5\nOK""",
        "AT!NRINFO?": "Connectivity Mode: NSA\nNR5G band: n78\nNR5G Rx chan: 650332\nNR5G RSRP (dBm): -94\nNR5G RSRQ (dB): -11\nNR5G SINR (dB): 19.5\nOK",
    })
    smod = SierraEM9Driver().parse(sierra_rsp)
    if smod.get("technology") != "5G NSA" or smod.get("lte_band") != "B1" or smod.get("nr_band") != "n78" or smod.get("lte_rsrp") != -86.0 or smod.get("nr_rsrp") != -94.0:
        failures.append(f"sierra EM9 parser: {smod}")
    if detect_modem_driver("Sierra Wireless EM9190").driver_id != "sierra_em9":
        failures.append("sierra driver detection")

    # Quectel RM520N EN-DC fixture using the documented QENG field layout.
    quec_rsp = dict(generic_rsp)
    quec_rsp.update({
        "AT+GMI": "Quectel\r\nOK\r\n",
        "AT+GMM": "RM520N-GL\r\nOK\r\n",
        "AT+QNWINFO": '+QNWINFO: "FDD LTE","310260","LTE BAND 66",66786\r\nOK',
        'AT+QENG="servingcell"': '+QENG: \"servingcell\",\"NOCONN\"\n+QENG: \"LTE\",\"FDD\",310,260,26A0C,115,66786,66,5,5,426C,-83,-9,-51,18,12,100,-\n+QENG: \"NR5G-NSA\",310,260,119,-96,12,-11,650000,77,12,1\nOK',
        "AT+QCSQ": '+QCSQ: "LTE",-51,-83,18,-9\r\nOK',
    })
    qm = QuectelRM5xxDriver().parse(quec_rsp)
    if qm.get("technology") != "5G NSA" or qm.get("lte_band") != "B66" or qm.get("nr_band") != "n77" or qm.get("lte_rsrp") != -83.0 or qm.get("nr_rsrp") != -96.0:
        failures.append(f"quectel RM5xx parser: {qm}")
    if detect_modem_driver("Quectel RM520N-GL").driver_id != "quectel_rm5xx":
        failures.append("quectel driver detection")
    if detect_modem_driver("SIMCom SIM8262A").driver_id != "generic_3gpp":
        failures.append("generic driver fallback")

    if failures:
        return 1, "SELFTEST FAIL\n" + "\n".join(f" - {x}" for x in failures)
    return 0, "SELFTEST PASS\nAll synthetic reasoning, Starlink, HackRF, Linux/Windows, generic 3GPP, Sierra EM9, and Quectel RM5xx parser tests passed."


# =============================================================================
# CLI
# =============================================================================

def _parse_range(text: str) -> SDRRange:
    # label:min:max OR min:max
    parts = text.split(":")
    if len(parts) == 2:
        return SDRRange(f"{parts[0]}_{parts[1]}MHz", float(parts[0]), float(parts[1]))
    if len(parts) == 3:
        return SDRRange(parts[0], float(parts[1]), float(parts[2]))
    raise argparse.ArgumentTypeError("range must be min:max or label:min:max (MHz)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="veilbreaker",
        description="Veilbreaker — cross-platform explainable field network/RF diagnostic reasoning engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Safety model:
          * Passive collection is the default.
          * --active permits bounded ICMP/DNS tests.
          * --guided may run one bounded follow-up diagnostic cycle.
          * SDR support in this application is receive-only; no transmit command is implemented.
          * Starlink support is read-only; Veilbreaker does not expose reboot/stow/control RPCs.
          * Native cellular support issues query-only AT commands; it does not change RAT/bands/APN/firmware.
          * Cellular IMEI/device identifiers are not collected unless explicitly enabled in config.
          * Automatic serial probing is conservative; --scan-all-ports requires explicit opt-in.
          * Primary hosts: Linux (NetworkHub/OR-Base) and Windows 10/11.
        """),
    )
    p.add_argument("--config", help="Config JSON path (default: per-user Veilbreaker data directory)")
    p.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)
    survey = sub.add_parser("survey", help="Run or reopen a grouped session of up to 20 diagnostics")
    survey.add_argument("--name", default="Site survey")
    survey.add_argument("--point", help="Exact point label for --trend")
    survey.add_argument("--metric", help="Numeric metric for --trend")
    survey.add_argument("--manual", action="store_true", help="Pause after each test")
    actions = survey.add_mutually_exclusive_group(required=True)
    actions.add_argument("--plan", help="JSON array of named test steps and boolean options")
    actions.add_argument("--show", help="Saved survey JSON path")
    actions.add_argument("--resume", help="Explicitly continue unrun tests in a saved session")
    actions.add_argument("--export", help="Saved survey JSON path to export as an evidence ZIP")
    actions.add_argument("--trend", help="Baseline survey JSON path for multi-visit trends")
    actions.add_argument("--list", action="store_true")
    verify = sub.add_parser("verify", help="Verify evidence bundle integrity")
    verify.add_argument("bundle")
    recovery = sub.add_parser("recover", help="Recover interrupted acquisitions without contacting hardware")
    recovery.add_argument("--config", default=argparse.SUPPRESS)

    init = sub.add_parser("init", help="Write a starter configuration")
    init.add_argument("--path", help="Output path (default: per-user Veilbreaker data directory)")
    init.add_argument("--force", action="store_true")

    compare = sub.add_parser("compare", help="Compare two saved runs without treating missing values as zero")
    compare.add_argument("before")
    compare.add_argument("after")
    sub.add_parser("doctor", help="Check local dependencies and hardware visibility")
    sub.add_parser("selftest", help="Run built-in synthetic reasoning tests")
    sub.add_parser("platform-info", help="Show native system/network/Wi-Fi collector output without active tests")

    runp = sub.add_parser("run", help="Collect, reason, save history, and produce an evidence pack")
    runp.add_argument("--active", action="store_true", help="Allow bounded ping/DNS measurements")
    runp.add_argument("--guided", action="store_true", help="Execute one bounded next-best-test cycle and re-analyze")
    runp.add_argument("--sdr", action="store_true", help="Run configured receive-only HackRF sweeps")
    runp.add_argument("--throughput", action="store_true", help="Run configured iperf3 test")
    runp.add_argument("--starlink", action="store_true", help="Collect read-only Starlink terminal telemetry for this run")
    runp.add_argument("--cellular", action="store_true", help="Collect native/read-only cellular modem telemetry for this run")
    runp.add_argument("--metrics", help="Merge JSON metrics from a file or '-' for stdin")
    runp.add_argument("--site", help="Override site ID")
    runp.add_argument("--scenario", choices=sorted(SCENARIO_OVERRIDES), help="Override diagnostic scenario")
    runp.add_argument("--note")
    runp.add_argument("--json", action="store_true", help="Print report JSON instead of text")

    analyze = sub.add_parser("analyze", help="Analyze an existing JSON metric snapshot")
    analyze.add_argument("input")
    analyze.add_argument("--site")
    analyze.add_argument("--scenario", choices=sorted(SCENARIO_OVERRIDES))
    analyze.add_argument("--json", action="store_true")

    sdr = sub.add_parser("sdr", help="HackRF Pro receive-only tools")
    sdrsub = sdr.add_subparsers(dest="sdr_command", required=True)
    sdrsub.add_parser("info", help="Show HackRF discovery information")
    sweep = sdrsub.add_parser("sweep", help="Run one or more receive-only spectrum sweeps")
    sweep.add_argument("--range", dest="ranges", type=_parse_range, action="append", required=True,
                       help="min:max or label:min:max in MHz; repeatable")
    sweep.add_argument("--bin-width", type=int)
    sweep.add_argument("--sweeps", type=int)
    sweep.add_argument("--json", action="store_true")

    modem = sub.add_parser("modem", help="Cross-platform read-only cellular modem tools")
    modemsub = modem.add_subparsers(dest="modem_command", required=True)
    ml = modemsub.add_parser("list", help="List serial/WWAN ports without opening them")
    ml.add_argument("--json", action="store_true")
    md = modemsub.add_parser("drivers", help="Show built-in modem compatibility/driver matrix")
    md.add_argument("--json", action="store_true")
    for _name in ("probe", "status"):
        mp = modemsub.add_parser(_name, help=("Identify a modem and select its driver" if _name == "probe" else "Collect canonical modem/radio telemetry"))
        mp.add_argument("--port", help="COMx or /dev/tty... (default config/auto)")
        mp.add_argument("--driver", choices=["auto"] + sorted(MODEM_DRIVERS), help="Force a modem driver")
        mp.add_argument("--scan-all-ports", action="store_true", help="Explicitly allow probing serial ports not identified as modem/WWAN ports")
        mp.add_argument("--json", action="store_true")

    star = sub.add_parser("starlink", help="Read-only Starlink terminal tools")
    starsub = star.add_subparsers(dest="starlink_command", required=True)
    st_status = starsub.add_parser("status", help="Collect current terminal status/obstruction/alerts")
    st_status.add_argument("--json", action="store_true", help="Print canonical telemetry JSON")
    starsub.add_parser("doctor", help="Check Starlink backend and local management reachability")

    hist = sub.add_parser("history", help="List saved diagnostic runs")
    hist.add_argument("--site")
    hist.add_argument("-n", "--limit", type=int, default=20)

    base = sub.add_parser("baseline", help="Show mature baseline metrics for a site/scenario")
    base.add_argument("--site")
    base.add_argument("--scenario", choices=sorted(SCENARIO_OVERRIDES))

    case = sub.add_parser("case", help="Manage confirmed diagnostic cases")
    casesub = case.add_subparsers(dest="case_command", required=True)
    ca = casesub.add_parser("add", help="Turn a saved run into a confirmed case")
    ca.add_argument("--run", required=True, dest="run_id")
    ca.add_argument("--cause", required=True)
    ca.add_argument("--resolution", default="")
    ca.add_argument("--hypothesis")
    ca.add_argument("--tag", action="append", default=[])
    cl = casesub.add_parser("list", help="List confirmed cases")
    cl.add_argument("-n", "--limit", type=int, default=30)

    test = sub.add_parser("test", help="Run a specific bounded active diagnostic")
    testsub = test.add_subparsers(dest="test_command", required=True)
    pmtu = testsub.add_parser("pmtu", help="Estimate IPv4 path MTU using Linux/Windows DF ping")
    pmtu.add_argument("target")
    path = testsub.add_parser("path", help="Run staged path latency/loss checks")
    path.add_argument("--target", action="append", default=[])
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "verify":
        from .evidence import verify_bundle
        result = verify_bundle(args.bundle)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return {"verified": 0, "failed": 1, "unverified": 2}[result["status"]]
    if args.command == "recover":
        from .recovery import recover_runs
        result = recover_runs(load_config(args.config))
        print(json.dumps(result, indent=2))
        return 1 if result["notes"] else 0

    if args.command == "init":
        path = Path(args.path).expanduser() if args.path else default_config_path()
        try:
            save_default_config(path, overwrite=args.force)
        except FileExistsError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(f"Wrote {path}")
        print("Configure cellular.enabled/port/driver for native AT collection (auto is recommended), enable Starlink as needed, and adjust SDR ranges to the mission profile.")
        return 0

    cfg = load_config(args.config)
    if getattr(args, "site", None):
        cfg.site_id = args.site
    if getattr(args, "scenario", None):
        cfg.scenario = args.scenario

    if args.command == "survey":
        from .survey import execute_survey, resume_survey, read_session, export_session, list_sessions
        if args.trend:
            from .survey_trends import saved_trend
            if not args.point or not args.metric:
                raise ValueError("--trend requires --point and --metric")
            print(json.dumps(saved_trend(cfg,args.trend,args.point,args.metric),indent=2))
            return 0
        if args.plan:
            result = execute_survey(cfg, args.name, json.loads(Path(args.plan).read_text(encoding="utf-8")), manual=args.manual)
            print(json.dumps(result, indent=2))
            return 0 if result["survey"]["status"] in ("complete", "paused") else 3
        if args.resume:
            result = resume_survey(cfg, args.resume)
            print(json.dumps(result, indent=2))
            return 0 if result["survey"]["status"] in ("complete", "paused") else 3
        if args.show:
            print(json.dumps(read_session(cfg, args.show), indent=2))
        elif args.export:
            print(export_session(cfg, args.export))
        else:
            print(json.dumps([{ "path": str(path), "name": session["name"], "status": session["status"]} for path, session in list_sessions(cfg)], indent=2))
        return 0
    if args.command == "doctor":
        rc, text = doctor(cfg)
        print(text)
        return rc
    if args.command == "selftest":
        rc, text = selftest()
        print(text)
        return rc
    if args.command == "platform-info":
        metrics: Dict[str, Any] = {}
        notes: List[str] = []
        for collector in (SystemCollector(), make_network_collector(), make_wifi_collector(), GPSDCollector()):
            try:
                part, n = collector.collect()
                metrics.update(part)
                notes.extend(f"{collector.name}: {x}" for x in n)
            except Exception as exc:
                notes.append(f"{collector.name}: {exc}")
        print(json.dumps({"platform": platform.platform(), "metrics": metrics, "notes": notes}, indent=2, default=str))
        return 0

    if args.command == "modem":
        if args.modem_command == "list":
            ports = list_serial_ports(include_unlikely=True)
            payload = [asdict(p) for p in ports]
            if args.json:
                print(json.dumps(payload, indent=2, default=str))
            else:
                print("CELLULAR / SERIAL PORTS")
                print("=" * 92)
                print(f"{'PORT':<18} {'LIKELY':<7} {'SOURCE':<12} {'VID:PID':<11} DESCRIPTION")
                for pinfo in ports:
                    vp = f"{pinfo.vid:04x}:{pinfo.pid:04x}" if pinfo.vid is not None and pinfo.pid is not None else "-"
                    print(f"{pinfo.device:<18} {str(pinfo.likely_modem):<7} {pinfo.source:<12} {vp:<11} {pinfo.description}")
                if not ports:
                    print("No serial ports discovered.")
            return 0
        if args.modem_command == "drivers":
            matrix = CellularModemCollector.compatibility_matrix()
            if args.json:
                print(json.dumps(matrix, indent=2))
            else:
                print("VEILBREAKER MODEM COMPATIBILITY")
                print("=" * 100)
                for row in matrix:
                    print(f"{row['family']:<54} {row['driver']:<16} {row['depth']:<15} {row['transport']}")
            return 0
        # Copy the config so a one-shot CLI override doesn't rewrite persistent configuration.
        mc = CellularConfig(**asdict(cfg.cellular))
        if getattr(args, "port", None): mc.port = args.port
        if getattr(args, "driver", None): mc.driver = args.driver
        if getattr(args, "scan_all_ports", False): mc.scan_all_ports = True
        collector = CellularModemCollector(mc)
        if args.modem_command == "probe":
            info, notes = collector.probe()
            obj = {"modem": info, "notes": notes, "read_only": True}
            if args.json:
                print(json.dumps(obj, indent=2, default=str))
            else:
                print("MODEM PROBE")
                print("=" * 72)
                if info:
                    for k, v in info.items(): print(f"{k:<20} {v}")
                for n in notes: print(f"NOTE: {n}")
            return 0 if info else 1
        if args.modem_command == "status":
            metrics, notes = collector.collect()
            if args.json:
                print(json.dumps({"metrics": metrics, "notes": notes}, indent=2, default=str))
            else:
                print("CELLULAR MODEM STATUS")
                print("=" * 72)
                for k in sorted(metrics):
                    if k != "cellular_raw_at": print(f"{k:<38} {metrics[k]}")
                for n in notes: print(f"NOTE: {n}")
            return 0 if metrics else 1

    if args.command == "starlink":
        collector = StarlinkCollector(cfg.starlink)
        if args.starlink_command == "doctor":
            avail = collector.backend_availability()
            reachable, detail = collector.probe()
            payload = {
                "target": collector.target,
                "configured_backend": cfg.starlink.backend,
                "python_starlink_grpc": avail["python"],
                "grpcurl": avail["grpcurl"],
                "management_reachable": reachable,
                "management_detail": detail,
                "location_collection": bool(cfg.starlink.collect_location),
                "read_only": True,
            }
            print(json.dumps(payload, indent=2))
            return 0 if (reachable and (avail["python"] or avail["grpcurl"])) else 1
        if args.starlink_command == "status":
            metrics, notes = collector.collect()
            if args.json:
                print(json.dumps({"metrics": metrics, "notes": notes}, indent=2, default=str))
            else:
                print("STARLINK STATUS")
                print("=" * 72)
                for key in sorted(metrics):
                    print(f"{key:<42} {metrics[key]}")
                if notes:
                    print("\nNotes:")
                    for note in notes:
                        print(f" - {note}")
            return 0 if metrics.get("starlink_state") or metrics.get("starlink_management_reachable") else 1

    app = VeilbreakerApplication(cfg)
    try:
        if args.command == "compare":
            from .comparison import compare_runs
            before, after = app.store.get_run(args.before), app.store.get_run(args.after)
            if before is None or after is None:
                raise ValueError("Both run IDs must exist in this data directory")
            print(compare_runs(before, after))
            return 0
        if args.command == "run":
            result = app.run(active=args.active or args.guided, sdr=args.sdr, throughput=args.throughput,
                             guided=args.guided, starlink=args.starlink, cellular=args.cellular,
                             metrics_file=args.metrics, note=args.note)
            if args.json:
                print(result.report.to_json())
            else:
                print(render_professional_console(result.report, {
                    "run_id": result.run_id, "site_id": cfg.site_id, "scenario": cfg.scenario, "timestamp": utcnow_iso()
                }))
                print(f"\nEvidence pack: {result.evidence_zip}")
                if result.notes:
                    print(f"Collector notes: {len(result.notes)} (included in evidence pack)")
            return 3 if result.collection.get("status") == "partial" else 0

        if args.command == "analyze":
            result = app.analyze_file(args.input)
            if args.json:
                print(result.report.to_json())
            else:
                print(render_professional_console(result.report, {
                    "run_id": result.run_id, "site_id": cfg.site_id, "scenario": cfg.scenario, "timestamp": utcnow_iso()
                }))
                print(f"\nEvidence pack: {result.evidence_zip}")
            return 0

        if args.command == "sdr":
            hc = HackRFCollector(cfg.sdr, cfg.artifacts_dir / ("sdr-" + _dt.datetime.now().strftime("%Y%m%d-%H%M%S")))
            if args.sdr_command == "info":
                m, notes = hc.info()
                print(json.dumps({"metrics": m, "notes": notes}, indent=2))
                return 0 if m.get("sdr_present") else 1
            if args.sdr_command == "sweep":
                if args.bin_width:
                    cfg.sdr.bin_width_hz = args.bin_width
                    hc.config.bin_width_hz = args.bin_width
                if args.sweeps:
                    cfg.sdr.sweeps = args.sweeps
                    hc.config.sweeps = args.sweeps
                m, notes, summaries = hc.collect(args.ranges)
                obj = {"metrics": m, "summaries": [asdict(x) for x in summaries], "notes": notes}
                if args.json:
                    print(json.dumps(obj, indent=2))
                else:
                    for s in summaries:
                        print(f"{s.label}: median {s.median_db:.1f} dB | p90 {s.p90_db:.1f} dB | peak {s.peak_db:.1f} dB @ {s.peak_freq_mhz:.3f} MHz | occupancy {s.occupancy_pct:.1f}%")
                    for n in notes:
                        print(f"NOTE: {n}")
                return 0 if summaries else 1

        if args.command == "history":
            rows = app.store.list_runs(args.site, args.limit)
            print(f"{'RUN ID':<28} {'UTC':<26} {'SITE':<18} {'SCENARIO':<18} NOTE")
            for r in rows:
                print(f"{r['run_id']:<28} {r['ts_utc']:<26} {r['site_id']:<18} {r['scenario']:<18} {r['note'] or ''}")
            return 0

        if args.command == "baseline":
            site = args.site or cfg.site_id
            scenario = args.scenario or cfg.scenario
            b = app.store.baseline(site, scenario, cfg.baseline_run_count, cfg.baseline_min_samples)
            print(json.dumps({"site": site, "scenario": scenario, "baseline": b}, indent=2))
            return 0

        if args.command == "case":
            if args.case_command == "add":
                cid = app.store.add_case(args.run_id, args.cause, args.resolution, args.hypothesis, args.tag)
                print(f"Created {cid}")
                return 0
            if args.case_command == "list":
                rows = app.store.list_cases(args.limit)
                for r in rows:
                    print(f"{r['case_id']}  {r['created_utc']}  {r['cause']}  source={r['source_run_id']}")
                    if r['resolution']:
                        print(f"  resolution: {r['resolution']}")
                return 0

        if args.command == "test":
            ex = ActiveTestExecutor(cfg)
            if args.test_command == "pmtu":
                m, notes = ex.path_mtu(args.target)
                print(json.dumps({"metrics": m, "notes": notes}, indent=2))
                return 0 if m.get("pmtu_test_success") else 1
            if args.test_command == "path":
                if args.target:
                    cfg.path_targets = args.target
                seed, _ = make_network_collector().collect()
                m, notes = ex.path_stages(seed)
                print(json.dumps({"metrics": m, "notes": notes}, indent=2))
                return 0

        print("Unhandled command", file=sys.stderr)
        return 2
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
