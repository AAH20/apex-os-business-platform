"""Tests for backup system."""
import json
import os
import time
from pathlib import Path

import pytest

from apex_os_bp.backup import (
    BackupManager,
    FullBackup,
    IncrementalBackup,
    DifferentialBackup,
    BackupVerifier,
    BackupRestorer,
)
from apex_os_bp.backup.types import (
    BackupType,
    BackupError,
    BackupVerificationError,
    BackupRestorationError,
    FileEntry,
    BackupManifest,
)


class TestFullBackup:
    """Test full backup functionality."""

    def test_full_backup_creates_manifest(self, tmp_path):
        """Full backup creates a valid manifest."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")
        (source / "file2.txt").write_text("content2")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        manifest = fb.create("test_full")

        assert manifest.backup_id == "test_full"
        assert manifest.backup_type == BackupType.FULL
        assert manifest.total_files == 2
        assert len(manifest.files) == 2

        manifest_path = backup_dir / "test_full" / "manifest.json"
        assert manifest_path.exists()
        assert (backup_dir / "test_full" / "data" / "file1.txt").exists()
        assert (backup_dir / "test_full" / "data" / "file2.txt").exists()

    def test_full_backup_preserves_content(self, tmp_path):
        """Full backup preserves file content."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("hello world")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_full")

        backed_up = backup_dir / "test_full" / "data" / "file.txt"
        assert backed_up.read_text() == "hello world"

    def test_full_backup_with_subdirectories(self, tmp_path):
        """Full backup handles subdirectories."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "subdir").mkdir()
        (source / "subdir" / "file.txt").write_text("nested content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        manifest = fb.create("test_full")

        assert manifest.total_files == 1
        assert "subdir/file.txt" in manifest.files

    def test_full_backup_invalid_source_raises_error(self, tmp_path):
        """Full backup raises error for invalid source."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        with pytest.raises(BackupError):
            FullBackup(tmp_path / "nonexistent", backup_dir)

    def test_full_backup_generates_id(self, tmp_path):
        """Full backup generates ID if not provided."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        manifest = fb.create()

        assert manifest.backup_id.startswith("full_")
        assert len(manifest.backup_id) > 5

    def test_full_backup_computes_correct_hash(self, tmp_path):
        """Full backup computes correct SHA-256 hash."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("test content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        manifest = fb.create("test_full")

        entry = manifest.files["file.txt"]
        assert len(entry.hash) == 64  # SHA-256 hex length
        assert entry.size == len("test content")

    def test_full_backup_empty_directory(self, tmp_path):
        """Full backup of empty directory creates empty manifest."""
        source = tmp_path / "source"
        source.mkdir()

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        manifest = fb.create("test_full")

        assert manifest.total_files == 0
        assert manifest.total_size == 0


class TestIncrementalBackup:
    """Test incremental backup functionality."""

    def test_incremental_backup_only_changed_files(self, tmp_path):
        """Incremental backup only includes changed files."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")
        (source / "file2.txt").write_text("content2")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        time.sleep(0.01)
        (source / "file1.txt").write_text("modified content1")

        ib = IncrementalBackup(source, backup_dir)
        inc_manifest = ib.create(full_manifest, "inc_backup")

        assert inc_manifest.backup_type == BackupType.INCREMENTAL
        assert inc_manifest.parent_backup_id == "full_backup"
        assert len(inc_manifest.files) == 1
        assert "file1.txt" in inc_manifest.files
        assert "file2.txt" not in inc_manifest.files

    def test_incremental_backup_new_files(self, tmp_path):
        """Incremental backup includes new files."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        (source / "file2.txt").write_text("content2")

        ib = IncrementalBackup(source, backup_dir)
        inc_manifest = ib.create(full_manifest, "inc_backup")

        assert len(inc_manifest.files) == 1
        assert "file2.txt" in inc_manifest.files

    def test_incremental_backup_no_changes(self, tmp_path):
        """Incremental backup with no changes creates empty backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        ib = IncrementalBackup(source, backup_dir)
        inc_manifest = ib.create(full_manifest, "inc_backup")

        assert len(inc_manifest.files) == 0
        assert inc_manifest.total_files == 0

    def test_incremental_backup_size_change(self, tmp_path):
        """Incremental backup detects size changes."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("short")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        time.sleep(0.01)
        (source / "file.txt").write_text("much longer content here")

        ib = IncrementalBackup(source, backup_dir)
        inc_manifest = ib.create(full_manifest, "inc_backup")

        assert "file.txt" in inc_manifest.files

    def test_incremental_backup_chained(self, tmp_path):
        """Chained incremental backups work correctly."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("v1")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        time.sleep(0.01)
        (source / "file.txt").write_text("v2")
        ib = IncrementalBackup(source, backup_dir)
        inc1 = ib.create(full_manifest, "inc1")

        time.sleep(0.01)
        (source / "file.txt").write_text("v3")
        inc2 = ib.create(inc1, "inc2")

        assert inc2.parent_backup_id == "inc1"
        assert "file.txt" in inc2.files


class TestDifferentialBackup:
    """Test differential backup functionality."""

    def test_differential_backup_since_full(self, tmp_path):
        """Differential backup includes all changes since full backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")
        (source / "file2.txt").write_text("content2")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        time.sleep(0.01)
        (source / "file1.txt").write_text("modified content1")
        (source / "file3.txt").write_text("content3")

        db = DifferentialBackup(source, backup_dir)
        diff_manifest = db.create(full_manifest, "diff_backup")

        assert diff_manifest.backup_type == BackupType.DIFFERENTIAL
        assert diff_manifest.parent_backup_id == "full_backup"
        assert len(diff_manifest.files) == 2
        assert "file1.txt" in diff_manifest.files
        assert "file3.txt" in diff_manifest.files
        assert "file2.txt" not in diff_manifest.files

    def test_differential_backup_cumulative(self, tmp_path):
        """Differential backup is cumulative (includes all changes since full)."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        time.sleep(0.01)
        (source / "file1.txt").write_text("modified1")

        db = DifferentialBackup(source, backup_dir)
        db.create(full_manifest, "diff1")

        time.sleep(0.01)
        (source / "file2.txt").write_text("content2")

        diff2 = db.create(full_manifest, "diff2")

        assert len(diff2.files) == 2
        assert "file1.txt" in diff2.files
        assert "file2.txt" in diff2.files

    def test_differential_backup_no_changes(self, tmp_path):
        """Differential backup with no changes creates empty backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        db = DifferentialBackup(source, backup_dir)
        diff_manifest = db.create(full_manifest, "diff_backup")

        assert len(diff_manifest.files) == 0

    def test_differential_backup_new_full_resets(self, tmp_path):
        """New full backup resets differential baseline."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("v1")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full1 = fb.create("full1")

        time.sleep(0.01)
        (source / "file.txt").write_text("v2")

        db = DifferentialBackup(source, backup_dir)
        diff1 = db.create(full1, "diff1")

        # New full backup
        time.sleep(0.01)
        (source / "file.txt").write_text("v3")
        full2 = fb.create("full2")

        # Modify after new full
        time.sleep(0.01)
        (source / "file.txt").write_text("v4")

        diff2 = db.create(full2, "diff2")

        assert diff2.parent_backup_id == "full2"
        assert "file.txt" in diff2.files


class TestBackupVerifier:
    """Test backup verification functionality."""

    def test_verify_valid_backup(self, tmp_path):
        """Verification passes for valid backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_backup")

        verifier = BackupVerifier(backup_dir)
        is_valid, errors = verifier.verify("test_backup")

        assert is_valid is True
        assert len(errors) == 0

    def test_verify_corrupted_backup(self, tmp_path):
        """Verification fails for corrupted backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_backup")

        (backup_dir / "test_backup" / "data" / "file.txt").write_text("corrupted")

        verifier = BackupVerifier(backup_dir)
        is_valid, errors = verifier.verify("test_backup")

        assert is_valid is False
        assert len(errors) > 0

    def test_verify_missing_file(self, tmp_path):
        """Verification fails when file is missing."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_backup")

        (backup_dir / "test_backup" / "data" / "file.txt").unlink()

        verifier = BackupVerifier(backup_dir)
        is_valid, errors = verifier.verify("test_backup")

        assert is_valid is False
        assert any("Missing file" in e for e in errors)

    def test_verify_all_backups(self, tmp_path):
        """Verify all backups in directory."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("backup1")
        fb.create("backup2")

        verifier = BackupVerifier(backup_dir)
        results = verifier.verify_all()

        assert len(results) == 2
        assert all(is_valid for is_valid, _ in results.values())

    def test_verify_nonexistent_backup_raises_error(self, tmp_path):
        """Verification raises error for nonexistent backup."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        verifier = BackupVerifier(backup_dir)

        with pytest.raises(BackupVerificationError):
            verifier.verify("nonexistent")

    def test_verify_size_mismatch(self, tmp_path):
        """Verification detects size mismatches."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_backup")

        # Truncate file (same content start, different size)
        (backup_dir / "test_backup" / "data" / "file.txt").write_text("con")

        verifier = BackupVerifier(backup_dir)
        is_valid, errors = verifier.verify("test_backup")

        assert is_valid is False
        assert any("Size mismatch" in e or "Hash mismatch" in e for e in errors)


class TestBackupRestorer:
    """Test backup restoration functionality."""

    def test_restore_full_backup(self, tmp_path):
        """Restore from full backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")
        (source / "file2.txt").write_text("content2")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_backup")

        restore_dir = tmp_path / "restored"
        restorer = BackupRestorer(backup_dir)
        restorer.restore("test_backup", restore_dir)

        assert (restore_dir / "file1.txt").read_text() == "content1"
        assert (restore_dir / "file2.txt").read_text() == "content2"

    def test_restore_incremental_chain(self, tmp_path):
        """Restore with incremental chain."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        time.sleep(0.01)
        (source / "file1.txt").write_text("modified1")
        (source / "file2.txt").write_text("content2")

        ib = IncrementalBackup(source, backup_dir)
        ib.create(full_manifest, "inc_backup")

        restore_dir = tmp_path / "restored"
        restorer = BackupRestorer(backup_dir)
        restorer.restore("full_backup", restore_dir, ["full_backup", "inc_backup"])

        assert (restore_dir / "file1.txt").read_text() == "modified1"
        assert (restore_dir / "file2.txt").read_text() == "content2"

    def test_restore_nonexistent_backup_raises_error(self, tmp_path):
        """Restore raises error for nonexistent backup."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        restorer = BackupRestorer(backup_dir)

        with pytest.raises(BackupRestorationError):
            restorer.restore("nonexistent", tmp_path / "restored")

    def test_restore_creates_directories(self, tmp_path):
        """Restore creates necessary directories."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "subdir").mkdir()
        (source / "subdir" / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_backup")

        restore_dir = tmp_path / "restored"
        restorer = BackupRestorer(backup_dir)
        restorer.restore("test_backup", restore_dir)

        assert (restore_dir / "subdir" / "file.txt").read_text() == "content"

    def test_restore_differential(self, tmp_path):
        """Restore from full + differential."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        full_manifest = fb.create("full_backup")

        time.sleep(0.01)
        (source / "file1.txt").write_text("modified1")
        (source / "file2.txt").write_text("content2")

        db = DifferentialBackup(source, backup_dir)
        db.create(full_manifest, "diff_backup")

        restore_dir = tmp_path / "restored"
        restorer = BackupRestorer(backup_dir)
        restorer.restore("full_backup", restore_dir, ["full_backup", "diff_backup"])

        assert (restore_dir / "file1.txt").read_text() == "modified1"
        assert (restore_dir / "file2.txt").read_text() == "content2"

    def test_restore_empty_backup(self, tmp_path):
        """Restore empty backup creates empty directory."""
        source = tmp_path / "source"
        source.mkdir()

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        fb = FullBackup(source, backup_dir)
        fb.create("test_backup")

        restore_dir = tmp_path / "restored"
        restorer = BackupRestorer(backup_dir)
        restorer.restore("test_backup", restore_dir)

        assert restore_dir.exists()
        assert list(restore_dir.iterdir()) == []


class TestBackupManager:
    """Test backup manager functionality."""

    def test_manager_create_full_backup(self, tmp_path):
        """Manager creates full backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manifest = manager.create_full_backup("test_full")

        assert manifest.backup_type == BackupType.FULL
        assert manifest.backup_id == "test_full"

    def test_manager_create_incremental_backup(self, tmp_path):
        """Manager creates incremental backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("full_backup")

        time.sleep(0.01)
        (source / "file.txt").write_text("modified")

        manifest = manager.create_incremental_backup()

        assert manifest.backup_type == BackupType.INCREMENTAL
        assert manifest.parent_backup_id == "full_backup"

    def test_manager_create_differential_backup(self, tmp_path):
        """Manager creates differential backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("full_backup")

        time.sleep(0.01)
        (source / "file.txt").write_text("modified")

        manifest = manager.create_differential_backup()

        assert manifest.backup_type == BackupType.DIFFERENTIAL

    def test_manager_list_backups(self, tmp_path):
        """Manager lists all backups."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("backup1")
        manager.create_full_backup("backup2")

        backups = manager.list_backups()

        assert len(backups) == 2
        assert backups[0]["backup_id"] == "backup1"
        assert backups[1]["backup_id"] == "backup2"

    def test_manager_verify_backup(self, tmp_path):
        """Manager verifies backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("test_backup")

        is_valid, errors = manager.verify_backup("test_backup")

        assert is_valid is True
        assert len(errors) == 0

    def test_manager_restore_backup(self, tmp_path):
        """Manager restores backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("test_backup")

        restore_dir = tmp_path / "restored"
        manager.restore_backup("test_backup", restore_dir)

        assert (restore_dir / "file.txt").read_text() == "content"

    def test_manager_incremental_without_parent_raises_error(self, tmp_path):
        """Manager raises error for incremental without parent."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)

        with pytest.raises(BackupError):
            manager.create_incremental_backup()

    def test_manager_differential_without_full_raises_error(self, tmp_path):
        """Manager raises error for differential without full backup."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)

        with pytest.raises(BackupError):
            manager.create_differential_backup()

    def test_manager_verify_all_backups(self, tmp_path):
        """Manager verifies all backups."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("backup1")
        manager.create_full_backup("backup2")

        results = manager.verify_all_backups()

        assert len(results) == 2
        assert all(is_valid for is_valid, _ in results.values())

    def test_manager_restore_with_chain(self, tmp_path):
        """Manager restores with incremental chain."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("v1")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("full_backup")

        time.sleep(0.01)
        (source / "file.txt").write_text("v2")
        manager.create_incremental_backup("full_backup", "inc1")

        time.sleep(0.01)
        (source / "file.txt").write_text("v3")
        manager.create_incremental_backup("inc1", "inc2")

        restore_dir = tmp_path / "restored"
        manager.restore_backup("full_backup", restore_dir, ["full_backup", "inc1", "inc2"])

        assert (restore_dir / "file.txt").read_text() == "v3"


class TestBackupTypes:
    """Test backup types and data structures."""

    def test_backup_type_enum(self):
        """Backup type enum has correct values."""
        assert BackupType.FULL.value == "full"
        assert BackupType.INCREMENTAL.value == "incremental"
        assert BackupType.DIFFERENTIAL.value == "differential"

    def test_file_entry_creation(self):
        """FileEntry can be created."""
        entry = FileEntry(
            path="test/file.txt",
            hash="abc123",
            size=100,
            mtime=1234567890.0,
        )

        assert entry.path == "test/file.txt"
        assert entry.hash == "abc123"
        assert entry.size == 100
        assert entry.mtime == 1234567890.0

    def test_backup_manifest_creation(self):
        """BackupManifest can be created."""
        manifest = BackupManifest(
            backup_id="test",
            backup_type=BackupType.FULL,
            timestamp="2023-01-01T00:00:00",
            source_path="/test",
            files={},
            total_files=0,
            total_size=0,
        )

        assert manifest.backup_id == "test"
        assert manifest.backup_type == BackupType.FULL
        assert manifest.total_files == 0


class TestBackupIntegration:
    """Integration tests for backup system."""

    def test_full_backup_restore_cycle(self, tmp_path):
        """Full backup and restore cycle preserves data."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")
        (source / "subdir").mkdir()
        (source / "subdir" / "file2.txt").write_text("content2")

        backup_dir = tmp_path / "backups"
        restore_dir = tmp_path / "restored"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("test_backup")
        manager.restore_backup("test_backup", restore_dir)

        assert (restore_dir / "file1.txt").read_text() == "content1"
        assert (restore_dir / "subdir" / "file2.txt").read_text() == "content2"

    def test_incremental_backup_restore_cycle(self, tmp_path):
        """Incremental backup and restore cycle preserves data."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")

        backup_dir = tmp_path / "backups"
        restore_dir = tmp_path / "restored"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("full_backup")

        time.sleep(0.01)
        (source / "file1.txt").write_text("modified1")
        (source / "file2.txt").write_text("content2")

        manager.create_incremental_backup("full_backup", "inc_backup")
        manager.restore_backup("full_backup", restore_dir, ["full_backup", "inc_backup"])

        assert (restore_dir / "file1.txt").read_text() == "modified1"
        assert (restore_dir / "file2.txt").read_text() == "content2"

    def test_differential_backup_restore_cycle(self, tmp_path):
        """Differential backup and restore cycle preserves data."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").write_text("content1")

        backup_dir = tmp_path / "backups"
        restore_dir = tmp_path / "restored"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("full_backup")

        time.sleep(0.01)
        (source / "file1.txt").write_text("modified1")
        (source / "file2.txt").write_text("content2")

        manager.create_differential_backup("diff_backup")
        manager.restore_backup("full_backup", restore_dir, ["full_backup", "diff_backup"])

        assert (restore_dir / "file1.txt").read_text() == "modified1"
        assert (restore_dir / "file2.txt").read_text() == "content2"

    def test_verify_after_restore(self, tmp_path):
        """Verification passes after restore."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        restore_dir = tmp_path / "restored"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("test_backup")
        manager.restore_backup("test_backup", restore_dir)

        is_valid, errors = manager.verify_backup("test_backup")
        assert is_valid is True

    def test_multiple_incremental_backups(self, tmp_path):
        """Multiple incremental backups work correctly."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").write_text("content1")

        backup_dir = tmp_path / "backups"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("full_backup")

        time.sleep(0.01)
        (source / "file.txt").write_text("content2")
        manager.create_incremental_backup("full_backup", "inc1")

        time.sleep(0.01)
        (source / "file.txt").write_text("content3")
        manager.create_incremental_backup("inc1", "inc2")

        restore_dir = tmp_path / "restored"
        manager.restore_backup("full_backup", restore_dir, ["full_backup", "inc1", "inc2"])

        assert (restore_dir / "file.txt").read_text() == "content3"

    def test_backup_with_binary_files(self, tmp_path):
        """Backup handles binary files correctly."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "binary.bin").write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        backup_dir = tmp_path / "backups"
        restore_dir = tmp_path / "restored"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("test_backup")
        manager.restore_backup("test_backup", restore_dir)

        assert (restore_dir / "binary.bin").read_bytes() == b"\x00\x01\x02\x03\xff\xfe"

    def test_backup_with_special_characters_in_filename(self, tmp_path):
        """Backup handles special characters in filenames."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file with spaces.txt").write_text("content")
        (source / "file-with-dashes.txt").write_text("content")

        backup_dir = tmp_path / "backups"
        restore_dir = tmp_path / "restored"

        manager = BackupManager(source, backup_dir)
        manager.create_full_backup("test_backup")
        manager.restore_backup("test_backup", restore_dir)

        assert (restore_dir / "file with spaces.txt").read_text() == "content"
        assert (restore_dir / "file-with-dashes.txt").read_text() == "content"
