"""Self-signed TLS for the service: SAN parsing, certificate generation and reuse.

`SABER_TLS=1` turns HTTPS on. Without `SABER_TLS_CERT` and `SABER_TLS_KEY` a self-signed
EC P-256 pair is generated once into `<DATA_DIR>/tls` and reused until its names change or it
expires within `RENEW_DAYS`. A user-supplied pair is never written.
"""

import datetime as dt
import ipaddress
import os
import re
import ssl
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

VALID_DAYS = 825
RENEW_DAYS = 30
DEFAULT_HOSTS = ("localhost", "127.0.0.1", "::1")
_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
_TRUE = {"1", "true", "yes", "on"}


def tls_enabled(env: Mapping[str, str]) -> bool:
    return env.get("SABER_TLS", "").strip().lower() in _TRUE


def verify_enabled(env: Mapping[str, str] | None = None) -> bool:
    """False only when `SABER_TLS_VERIFY` is 0, false, no or off (clients of a self-signed cert)."""
    raw = (os.environ if env is None else env).get("SABER_TLS_VERIFY", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def client_verify(api: str, env: Mapping[str, str] | None = None) -> bool:
    """`verify_enabled`, warning on stderr when it is off for a non-loopback API host."""
    if verify_enabled(env):
        return True
    host = urlparse(api).hostname or ""
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = host.lower() == "localhost"
    if not loopback:
        print(f"warning: TLS verification is off for {host or api}", file=sys.stderr)
    return False


def parse_host(raw: str) -> str:
    """One hostname or IP address, normalised; ValueError for anything else."""
    text = raw.strip()
    if "%" in text:
        raise ValueError(f"not a hostname or IP address: {raw!r}")
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        pass
    name = text.lower().rstrip(".")
    if not name or len(name) > 253 or not all(_LABEL.match(p) for p in name.split(".")):
        raise ValueError(f"not a hostname or IP address: {raw!r}")
    return name


def parse_hosts(raw: str | None) -> list[str]:
    """Defaults plus the comma-separated extras, normalised and de-duplicated in order."""
    out = list(DEFAULT_HOSTS)
    for part in (raw or "").split(","):
        if part.strip():
            host = parse_host(part)
            if host not in out:
                out.append(host)
    return out


def _general_names(hosts: list[str]) -> list[x509.GeneralName]:
    names: list[x509.GeneralName] = []
    for host in hosts:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            names.append(x509.DNSName(host))
    return names


def _cert_names(cert: x509.Certificate) -> set[str]:
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    return {str(ip) for ip in san.get_values_for_type(x509.IPAddress)} | set(
        san.get_values_for_type(x509.DNSName)
    )


def _public_der(public_key) -> bytes:
    return public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def _current(cert_path: Path, key_path: Path, hosts: list[str], now: dt.datetime) -> bool:
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        if not (key_path.is_file() and os.access(key_path, os.R_OK)):
            return False
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if _public_der(key.public_key()) != _public_der(cert.public_key()):
            return False
        if cert.not_valid_after_utc - now < dt.timedelta(days=RENEW_DAYS):
            return False
        return _cert_names(cert) == set(hosts)
    except (OSError, ValueError, TypeError, x509.ExtensionNotFound):
        return False


def _write_atomic(path: Path, data: bytes, mode: int) -> None:
    """Write `data` to a fresh exclusive temp file beside `path`, fsync, then replace."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.unlink(missing_ok=True)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def generate(cert_path: Path, key_path: Path, hosts: list[str], now: dt.datetime) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "saber-tooth")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=VALID_DAYS))
        .add_extension(x509.SubjectAlternativeName(_general_names(hosts)), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    cert_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _write_atomic(cert_path, cert.public_bytes(serialization.Encoding.PEM), 0o644)
    _write_atomic(
        key_path,
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        0o600,
    )


def ensure_cert(
    data_dir: Path, hosts_raw: str | None = None, now: dt.datetime | None = None
) -> tuple[Path, Path]:
    """The (cert, key) pair under `data_dir/tls`, generated when absent, stale or renamed."""
    now = now or dt.datetime.now(dt.UTC)
    hosts = parse_hosts(hosts_raw)
    cert_path, key_path = data_dir / "tls" / "cert.pem", data_dir / "tls" / "key.pem"
    if not _current(cert_path, key_path, hosts, now):
        generate(cert_path, key_path, hosts, now)
    return cert_path, key_path


def resolve(env: Mapping[str, str]) -> tuple[Path, Path] | None:
    """(cert, key) for uvicorn, or None when TLS is off; ValueError on bad configuration."""
    if not tls_enabled(env):
        return None
    cert, key = env.get("SABER_TLS_CERT", "").strip(), env.get("SABER_TLS_KEY", "").strip()
    if cert or key:
        if not (cert and key):
            raise ValueError("SABER_TLS_CERT and SABER_TLS_KEY must be set together")
        if not (Path(cert).is_file() and Path(key).is_file()):
            raise ValueError("SABER_TLS_CERT or SABER_TLS_KEY does not name a file")
        try:
            ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(cert, key)
        except (ssl.SSLError, OSError) as exc:
            raise ValueError(
                f"SABER_TLS_CERT and SABER_TLS_KEY do not form a usable pair: {exc}"
            ) from exc
        return Path(cert), Path(key)
    return ensure_cert(Path(env.get("DATA_DIR") or "/data"), env.get("SABER_TLS_HOSTS"))
