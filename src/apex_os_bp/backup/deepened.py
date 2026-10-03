"""Deepened backup module: scheduling, encryption, verification, retention, restore."""
from __future__ import annotations
import hashlib, json, os, shutil, tarfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

class BackupType(str, Enum):
    FULL = "full"; INCREMENTAL = "incremental"

@dataclass
class Schedule:
    name: str; backup_type: BackupType; hour: int = 2; minute: int = 0
    day_of_month: Optional[int] = None; day_of_week: Optional[int] = None; enabled: bool = True
    def should_run(self, now=None):
        if not self.enabled: return False
        now = now or datetime.now()
        if now.hour != self.hour or now.minute != self.minute: return False
        if self.day_of_month is not None and now.day != self.day_of_month: return False
        if self.day_of_week is not None and now.weekday() != self.day_of_week: return False
        return True

class Scheduler:
    def __init__(self, sf=".backup_schedules.json"):
        self.sf = Path(sf); self.schedules = []; self._load()
    def add(self, s): self.schedules.append(s); self._save()
    def remove(self, name):
        n = len(self.schedules); self.schedules = [s for s in self.schedules if s.name != name]
        if len(self.schedules) < n: self._save(); return True
        return False
    def due(self, now=None): return [s for s in self.schedules if s.should_run(now)]
    def _save(self):
        self.sf.write_text(json.dumps([{"name": s.name, "backup_type": s.backup_type.value,
            "hour": s.hour, "minute": s.minute, "day_of_month": s.day_of_month,
            "day_of_week": s.day_of_week, "enabled": s.enabled} for s in self.schedules], indent=2))
    def _load(self):
        if self.sf.exists():
            self.schedules = [Schedule(name=r["name"], backup_type=BackupType(r["backup_type"]),
                hour=r["hour"], minute=r["minute"], day_of_month=r.get("day_of_month"),
                day_of_week=r.get("day_of_week"), enabled=r.get("enabled", True))
                for r in json.loads(self.sf.read_text())]

class EncryptionError(Exception): pass
class AESEncryptor:
    NONCE_SIZE = 12; KEY_SIZE = 32; TAG_SIZE = 16
    def __init__(self, key):
        if len(key) != self.KEY_SIZE: raise EncryptionError(f"Key must be {self.KEY_SIZE} bytes")
        self.key = key
    @classmethod
    def generate_key(cls): return os.urandom(cls.KEY_SIZE)
    @classmethod
    def derive_key(cls, passphrase, salt=None):
        salt = salt or os.urandom(16)
        return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 100_000, dklen=cls.KEY_SIZE), salt
    def encrypt(self, pt):
        if not _HAS_CRYPTO: raise EncryptionError("cryptography package required")
        nonce = os.urandom(self.NONCE_SIZE)
        c = Cipher(algorithms.AES(self.key), modes.GCM(nonce), backend=default_backend())
        e = c.encryptor(); return nonce + e.tag + e.update(pt) + e.finalize()
    def decrypt(self, data):
        if not _HAS_CRYPTO: raise EncryptionError("cryptography package required")
        if len(data) < self.NONCE_SIZE + self.TAG_SIZE: raise EncryptionError("Ciphertext too short")
        nonce, tag, ct = data[:12], data[12:28], data[28:]
        c = Cipher(algorithms.AES(self.key), modes.GCM(nonce, tag), backend=default_backend())
        d = c.decryptor(); return d.update(ct) + d.finalize()

class VerificationError(Exception): pass
class ChecksumVerifier:
    @staticmethod
    def checksum(fp, algo="sha256"):
        h = hashlib.new(algo)
        with open(fp, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
        return h.hexdigest()
    @staticmethod
    def verify(fp, expected, algo="sha256"): return ChecksumVerifier.checksum(fp, algo).lower() == expected.lower()
    @staticmethod
    def write_manifest(bdir, files, algo="sha256"):
        mp = bdir / "checksums.json"
        mp.write_text(json.dumps({"algorithm": algo, "files": {
            str(f.relative_to(bdir)): ChecksumVerifier.checksum(f, algo) for f in files}}, indent=2))
        return mp
    @staticmethod
    def verify_manifest(bdir, mp=None):
        mp = mp or bdir / "checksums.json"
        if not mp.exists(): raise VerificationError(f"Manifest not found: {mp}")
        data = json.loads(mp.read_text()); algo = data.get("algorithm", "sha256")
        return {rel: (bdir / rel).exists() and ChecksumVerifier.verify(bdir / rel, exp, algo)
                for rel, exp in data["files"].items()}

@dataclass
class RetentionPolicy:
    daily: int = 7; weekly: int = 4; monthly: int = 12; yearly: int = 3
    def classify(self, bt, now=None):
        now = now or datetime.now(); age = (now - bt).days
        if age >= 365 and bt.month == 1 and bt.day == 1: return "yearly"
        if age >= 30 and bt.day == 1: return "monthly"
        if age >= 7 and bt.weekday() == 0: return "weekly"
        return "daily"
    def should_retain(self, bt, all_bts, now=None):
        now = now or datetime.now(); cat = self.classify(bt, now); limit = getattr(self, cat)
        same = sorted([b for b in all_bts if self.classify(b, now) == cat], reverse=True)
        return bt in same[:limit]

class RetentionManager:
    def __init__(self, policy=None): self.policy = policy or RetentionPolicy()
    def apply(self, root, now=None):
        now = now or datetime.now(); entries = []
        for e in root.iterdir():
            if not e.is_dir(): continue
            try: ts = datetime.fromisoformat(e.name.replace("backup_", "").replace("_", ""))
            except (ValueError, AttributeError): continue
            entries.append((e, ts))
        all_ts = [ts for _, ts in entries]
        return [p for p, ts in entries if not self.policy.should_retain(ts, all_ts, now)]
    def prune(self, root, now=None, dry_run=False):
        to_del = self.apply(root, now)
        if not dry_run:
            for p in to_del: shutil.rmtree(p, ignore_errors=True)
        return to_del

class RestoreError(Exception): pass
class PointInTimeRestore:
    def __init__(self, root): self.root = Path(root)
    def list_snapshots(self):
        snaps = []
        for e in sorted(self.root.iterdir()):
            if not e.is_dir(): continue
            mf = e / "metadata.json"
            if mf.exists():
                m = json.loads(mf.read_text())
                snaps.append((e, datetime.fromisoformat(m["timestamp"]), BackupType(m.get("type", "full"))))
        return snaps
    def find_snapshot(self, target):
        cands = [(p, t, b) for p, t, b in self.list_snapshots() if t <= target]
        return max(cands, key=lambda x: x[1]) if cands else None
    def restore(self, target, dest, passphrase=None):
        snap = self.find_snapshot(target)
        if not snap: raise RestoreError(f"No snapshot at or before {target.isoformat()}")
        dest = Path(dest); dest.mkdir(parents=True, exist_ok=True)
        all_snaps = self.list_snapshots()
        fulls = [(p, t, b) for p, t, b in all_snaps if b == BackupType.FULL and t <= target]
        if not fulls: raise RestoreError("No full backup for point-in-time restore")
        base_path, base_time, _ = max(fulls, key=lambda x: x[1])
        self._extract(base_path, dest, passphrase)
        incs = sorted([(p, t, b) for p, t, b in all_snaps
                       if b == BackupType.INCREMENTAL and base_time < t <= target], key=lambda x: x[1])
        for ip, _, _ in incs: self._extract(ip, dest, passphrase)
        (dest / ".restore_info.json").write_text(json.dumps({
            "restored_to": target.isoformat(), "base_backup": base_time.isoformat(),
            "incrementals_applied": len(incs)}, indent=2))
        return dest
    def _extract(self, snap, dest, passphrase=None):
        ap = snap / "backup.tar.gz.enc" if passphrase else snap / "backup.tar.gz"
        if not ap.exists(): raise RestoreError(f"Archive not found: {ap}")
        if passphrase:
            data = ap.read_bytes()
            key, _ = AESEncryptor.derive_key(passphrase, salt=data[:16])
            pt = AESEncryptor(key).decrypt(data[16:])
            tmp = dest / ".tmp_restore.tar.gz"; tmp.write_bytes(pt); ap = tmp
        with tarfile.open(ap, "r:gz") as tar: tar.extractall(dest, filter="data")
        if ap.name.startswith(".tmp_"): ap.unlink(missing_ok=True)

@dataclass
class BackupEngine:
    backup_root: Path; passphrase: Optional[str] = None
    scheduler: Scheduler = field(default_factory=Scheduler)
    retention: RetentionManager = field(default_factory=RetentionManager)
    encryptor: Optional[AESEncryptor] = None
    def __post_init__(self):
        self.backup_root = Path(self.backup_root); self.backup_root.mkdir(parents=True, exist_ok=True)
        if self.passphrase and _HAS_CRYPTO:
            key, _ = AESEncryptor.derive_key(self.passphrase); self.encryptor = AESEncryptor(key)
    def create_backup(self, source, btype=BackupType.FULL, name=None):
        source = Path(source); ts = datetime.now()
        name = name or f"backup_{ts.strftime('%Y%m%d_%H%M%S')}"
        dest = self.backup_root / name; dest.mkdir(parents=True, exist_ok=True)
        ap = dest / "backup.tar.gz"
        with tarfile.open(ap, "w:gz") as tar: tar.add(source, arcname=source.name)
        if self.encryptor:
            (dest / "backup.tar.gz.enc").write_bytes(self.encryptor.encrypt(ap.read_bytes())); ap.unlink()
        (dest / "metadata.json").write_text(json.dumps({
            "timestamp": ts.isoformat(), "type": btype.value,
            "source": str(source), "encrypted": self.encryptor is not None}, indent=2))
        files = [f for f in dest.iterdir() if f.is_file() and f.name != "checksums.json"]
        ChecksumVerifier.write_manifest(dest, files)
        return dest
    def verify_backup(self, bp): return ChecksumVerifier.verify_manifest(bp)
    def restore(self, target, dest): return PointInTimeRestore(self.backup_root).restore(target, dest, self.passphrase)
    def prune(self, dry_run=False): return self.retention.prune(self.backup_root, dry_run=dry_run)
