"""Validation for everyday network target settings."""
import ipaddress
import re
from .core import AppConfig


def target(value, name, optional=False):
    value = value.strip()
    if not value and optional:
        return None
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    try:
        ascii_name = value.rstrip(".").encode("idna").decode("ascii")
    except UnicodeError:
        ascii_name = ""
    if not ascii_name or len(ascii_name) > 253 or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", part) for part in ascii_name.split(".")):
        raise ValueError(f"{name}: enter a hostname or IP address, without a URL, port or spaces")
    return ascii_name


def apply_network_settings(raw, ping, dns, server, port):
    cfg = AppConfig.from_dict(raw)
    cfg.public_ping_target = target(ping, "Ping target")
    cfg.dns_test_host = target(dns, "DNS test host")
    cfg.iperf3_server = target(server, "Throughput server", optional=True)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Throughput port must be between 1 and 65535")
    cfg.iperf3_port = port
    return cfg


def apply_hardware_settings(raw, values):
    """Merge only exposed connection fields, preserving acquisition and privacy choices."""
    cfg = AppConfig.from_dict(raw)
    cfg.cellular.port = values["cellular.port"].strip() or "auto"
    if any(ord(char) < 32 for char in cfg.cellular.port):
        raise ValueError("Serial port must not contain control characters")
    for section, name, choices in (
        ("cellular", "driver", {"auto", "generic_3gpp", "sierra_em9", "quectel_rm5xx"}),
        ("cellular", "backend", {"auto", "serial", "json"}),
        ("starlink", "backend", {"auto", "python", "grpcurl"}),
    ):
        value = values[f"{section}.{name}"]
        original = getattr(getattr(cfg, section), name)
        if value not in choices and value != original:
            raise ValueError(f"Unknown {section} {name}")
        setattr(getattr(cfg, section), name, value)
    if cfg.cellular.backend == "json" and not cfg.cellular.json_command:
        raise ValueError("Configure the cellular JSON adapter command in Advanced JSON before selecting that backend")
    cfg.starlink.host = target(values["starlink.host"], "Starlink host")
    port = values["starlink.port"]
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Starlink port must be between 1 and 65535")
    cfg.starlink.port = port
    for name in ("tools_dir", "serial"):
        value = values[f"sdr.{name}"].strip()
        if any(ord(char) < 32 for char in value):
            raise ValueError(f"SDR {name} must not contain control characters")
        setattr(cfg.sdr, name, value or None)
    return cfg
