"""Comprehensive tests for the multi-tenancy system."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from apex_os_bp.multitenancy import (
    Alert,
    AuditLog,
    TenantAuditLogger,
    BillingCycle,
    BillingEngine,
    HealthStatus,
    Invoice,
    MetricsCollector,
    ProvisioningResult,
    SecurityPolicy,
    Tenant,
    TenantAPIKeyManager,
    TenantAwareRepository,
    TenantContext,
    TenantEncryption,
    TenantIsolationError,
    TenantMonitor,
    TenantPermission,
    TenantPlan,
    TenantProvisioner,
    TenantRBAC,
    TenantRole,
    TenantStatus,
    TenantUser,
    UsageMeter,
    UsageRecord,
    clear_current_tenant,
    get_current_tenant,
    require_tenant,
    set_current_tenant,
    tenant_scoped_query,
)


# ============================================================================
# Tenant Isolation Tests
# ============================================================================


class TestTenantContext:
    def test_set_and_get_tenant(self):
        set_current_tenant("tenant-1")
        assert get_current_tenant() == "tenant-1"
        clear_current_tenant()
        assert get_current_tenant() is None

    def test_tenant_context_manager(self):
        with TenantContext("tenant-ctx-1"):
            assert get_current_tenant() == "tenant-ctx-1"
        assert get_current_tenant() is None

    def test_tenant_context_nested(self):
        with TenantContext("outer"):
            assert get_current_tenant() == "outer"
            with TenantContext("inner"):
                assert get_current_tenant() == "inner"
            assert get_current_tenant() == "outer"
        assert get_current_tenant() is None

    def test_tenant_context_empty_id_raises(self):
        with pytest.raises(TenantIsolationError):
            with TenantContext(""):
                pass

    def test_tenant_context_isolation_between_contexts(self):
        with TenantContext("tenant-a"):
            assert get_current_tenant() == "tenant-a"
        with TenantContext("tenant-b"):
            assert get_current_tenant() == "tenant-b"


class TestRequireTenantDecorator:
    def test_requires_tenant_raises_without_context(self):
        @require_tenant
        def my_func():
            return "ok"

        with pytest.raises(TenantIsolationError):
            my_func()

    def test_requires_tenant_passes_with_context(self):
        @require_tenant
        def my_func():
            return "ok"

        with TenantContext("tenant-req"):
            assert my_func() == "ok"


class TestTenantScopedQuery:
    def test_filters_by_current_tenant(self):
        records = [
            Tenant(id="1", name="A", tenant_id="t1"),
            Tenant(id="2", name="B", tenant_id="t2"),
            Tenant(id="3", name="C", tenant_id="t1"),
        ]
        with TenantContext("t1"):
            result = tenant_scoped_query(records)
        assert len(result) == 2
        assert all(r.tenant_id == "t1" for r in result)

    def test_filters_by_explicit_tenant(self):
        records = [
            Tenant(id="1", name="A", tenant_id="t1"),
            Tenant(id="2", name="B", tenant_id="t2"),
        ]
        result = tenant_scoped_query(records, tenant_id="t2")
        assert len(result) == 1
        assert result[0].tenant_id == "t2"

    def test_raises_without_tenant_context(self):
        records = [Tenant(id="1", name="A", tenant_id="t1")]
        with pytest.raises(TenantIsolationError):
            tenant_scoped_query(records)

    def test_empty_records(self):
        with TenantContext("t1"):
            result = tenant_scoped_query([])
        assert result == []


class TestTenantAwareRepository:
    def test_repository_requires_tenant(self):
        with pytest.raises(TenantIsolationError):
            TenantAwareRepository()

    def test_repository_filters_correctly(self):
        with TenantContext("t-repo"):
            repo = TenantAwareRepository()
            records = [
                Tenant(id="1", tenant_id="t-repo"),
                Tenant(id="2", tenant_id="other"),
            ]
            result = repo.filter_by_tenant(records)
            assert len(result) == 1
            assert result[0].tenant_id == "t-repo"

    def test_assert_tenant_passes(self):
        with TenantContext("t-assert"):
            repo = TenantAwareRepository()
            record = Tenant(id="1", tenant_id="t-assert")
            repo.assert_tenant(record)  # Should not raise

    def test_assert_tenant_raises_on_mismatch(self):
        with TenantContext("t-assert"):
            repo = TenantAwareRepository()
            record = Tenant(id="1", tenant_id="other")
            with pytest.raises(TenantIsolationError):
                repo.assert_tenant(record)


class TestTenantBoundary:
    def test_validate_same_tenant_passes(self):
        from apex_os_bp.multitenancy.isolation import TenantBoundary

        TenantBoundary.validate_same_tenant("t1", "t1", "test")

    def test_validate_same_tenant_raises(self):
        from apex_os_bp.multitenancy.isolation import TenantBoundary

        with pytest.raises(TenantIsolationError):
            TenantBoundary.validate_same_tenant("t1", "t2", "test")

    def test_validate_tenant_access_passes(self):
        from apex_os_bp.multitenancy.isolation import TenantBoundary

        TenantBoundary.validate_tenant_access("t1", "t1")

    def test_validate_tenant_access_raises(self):
        from apex_os_bp.multitenancy.isolation import TenantBoundary

        with pytest.raises(TenantIsolationError):
            TenantBoundary.validate_tenant_access("t1", "t2")


# ============================================================================
# Tenant Provisioning Tests
# ============================================================================


class TestTenantProvisioner:
    def test_provision_creates_tenant(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Acme Corp",
            slug="acme",
            plan=TenantPlan.PROFESSIONAL,
            admin_email="admin@acme.com",
        )
        assert result.success is True
        assert result.tenant is not None
        assert result.tenant.name == "Acme Corp"
        assert result.tenant.slug == "acme"
        assert result.tenant.status == TenantStatus.ACTIVE
        assert result.admin_user is not None
        assert result.admin_user.email == "admin@acme.com"
        assert result.admin_user.role == TenantRole.OWNER

    def test_provision_generates_encryption_key(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="test", admin_email="t@test.com"
        )
        assert result.tenant.encryption_key_id is not None
        assert len(result.tenant.encryption_key_id) == 32

    def test_provision_sets_plan_limits(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Enterprise", slug="ent", plan=TenantPlan.ENTERPRISE,
            admin_email="e@ent.com",
        )
        assert result.tenant.max_users == 10_000
        assert result.tenant.max_storage_bytes == 1_099_511_627_776
        assert result.tenant.max_api_calls_per_month == 100_000_000

    def test_provision_duplicate_slug_fails(self):
        provisioner = TenantProvisioner()
        provisioner.provision(name="First", slug="dup", admin_email="a@b.com")
        result = provisioner.provision(name="Second", slug="dup", admin_email="c@d.com")
        assert result.success is False
        assert any("already taken" in e for e in result.errors)

    def test_provision_invalid_email_fails(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(name="Test", slug="test", admin_email="notanemail")
        assert result.success is False
        assert any("email" in e.lower() for e in result.errors)

    def test_provision_empty_name_fails(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(name="", slug="test", admin_email="a@b.com")
        assert result.success is False

    def test_suspend_tenant(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="suspend-test", admin_email="a@b.com"
        )
        tenant_id = result.tenant.id
        assert provisioner.suspend(tenant_id, "non-payment") is True
        tenant = provisioner.get_tenant(tenant_id)
        assert tenant.status == TenantStatus.SUSPENDED
        assert tenant.suspended_at is not None

    def test_resume_tenant(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="resume-test", admin_email="a@b.com"
        )
        tenant_id = result.tenant.id
        provisioner.suspend(tenant_id)
        assert provisioner.resume(tenant_id) is True
        tenant = provisioner.get_tenant(tenant_id)
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.suspended_at is None

    def test_delete_tenant_soft(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="delete-test", admin_email="a@b.com"
        )
        tenant_id = result.tenant.id
        assert provisioner.delete(tenant_id, hard_delete=False) is True
        tenant = provisioner.get_tenant(tenant_id)
        assert tenant.status == TenantStatus.DELETED
        assert tenant.deleted_at is not None

    def test_delete_tenant_hard(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="hard-delete", admin_email="a@b.com"
        )
        tenant_id = result.tenant.id
        assert provisioner.delete(tenant_id, hard_delete=True) is True
        assert provisioner.get_tenant(tenant_id) is None

    def test_get_tenant_by_slug(self):
        provisioner = TenantProvisioner()
        provisioner.provision(name="Acme", slug="find-me", admin_email="a@b.com")
        tenant = provisioner.get_tenant_by_slug("find-me")
        assert tenant is not None
        assert tenant.name == "Acme"

    def test_list_tenants(self):
        provisioner = TenantProvisioner()
        provisioner.provision(name="T1", slug="t1", admin_email="a@b.com")
        provisioner.provision(name="T2", slug="t2", admin_email="c@d.com")
        tenants = provisioner.list_tenants()
        assert len(tenants) == 2

    def test_list_tenants_filtered_by_status(self):
        provisioner = TenantProvisioner()
        r1 = provisioner.provision(name="T1", slug="t1", admin_email="a@b.com")
        provisioner.provision(name="T2", slug="t2", admin_email="c@d.com")
        provisioner.suspend(r1.tenant.id)
        active = provisioner.list_tenants(status=TenantStatus.ACTIVE)
        suspended = provisioner.list_tenants(status=TenantStatus.SUSPENDED)
        assert len(active) == 1
        assert len(suspended) == 1

    def test_add_user_to_tenant(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="add-user", admin_email="a@b.com"
        )
        user = provisioner.add_user(result.tenant.id, "new@user.com", TenantRole.MEMBER)
        assert user is not None
        assert user.email == "new@user.com"
        assert user.role == TenantRole.MEMBER

    def test_add_user_enforces_max_users(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="max-users", plan=TenantPlan.FREE,
            admin_email="a@b.com",
        )
        tenant_id = result.tenant.id
        # FREE plan allows 5 users, 1 already exists (admin)
        for i in range(4):
            provisioner.add_user(tenant_id, f"user{i}@test.com")
        # This should fail — at max
        extra = provisioner.add_user(tenant_id, "extra@test.com")
        assert extra is None

    def test_remove_user(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="remove-user", admin_email="a@b.com"
        )
        user = provisioner.add_user(result.tenant.id, "remove@me.com")
        assert provisioner.remove_user(result.tenant.id, user.id) is True
        assert provisioner.remove_user(result.tenant.id, user.id) is False

    def test_audit_log_created_on_provisioning(self):
        provisioner = TenantProvisioner()
        result = provisioner.provision(
            name="Test", slug="audit-test", admin_email="a@b.com"
        )
        logs = provisioner.get_audit_logs(result.tenant.id)
        assert len(logs) > 0
        assert any(l.action == "tenant.provisioned" for l in logs)


# ============================================================================
# Tenant Billing Tests
# ============================================================================


class TestUsageMeter:
    def test_record_usage(self):
        meter = UsageMeter(tenant_id="t1")
        record = meter.record("api_calls", 100, "count")
        assert record.tenant_id == "t1"
        assert record.metric == "api_calls"
        assert record.quantity == 100

    def test_get_usage_total(self):
        meter = UsageMeter(tenant_id="t1")
        meter.record("api_calls", 100)
        meter.record("api_calls", 200)
        meter.record("storage", 500)
        assert meter.get_usage("api_calls") == 300
        assert meter.get_usage("storage") == 500

    def test_get_usage_with_time_range(self):
        meter = UsageMeter(tenant_id="t1")
        now = datetime.utcnow()
        old = now - timedelta(hours=2)
        recent = now - timedelta(minutes=5)

        meter.record("api_calls", 100)
        meter.records[-1].recorded_at = old
        meter.record("api_calls", 200)
        meter.records[-1].recorded_at = recent

        total = meter.get_usage("api_calls", start=now - timedelta(hours=1))
        assert total == 200

    def test_get_usage_by_metric(self):
        meter = UsageMeter(tenant_id="t1")
        meter.record("api_calls", 100)
        meter.record("api_calls", 200)
        meter.record("storage_bytes", 1024)
        usage = meter.get_usage_by_metric()
        assert usage["api_calls"] == 300
        assert usage["storage_bytes"] == 1024

    def test_clear(self):
        meter = UsageMeter(tenant_id="t1")
        meter.record("api_calls", 100)
        meter.clear()
        assert meter.records == []


class TestBillingEngine:
    def test_record_usage(self):
        engine = BillingEngine()
        record = engine.record_usage("t1", "api_calls", 500)
        assert record.tenant_id == "t1"
        assert record.metric == "api_calls"

    def test_generate_invoice_free_plan(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.FREE)
        invoice = engine.generate_invoice(tenant)
        assert invoice.tenant_id == "t1"
        assert invoice.amount_cents == 0
        assert invoice.status == "open"

    def test_generate_invoice_paid_plan(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.STARTER)
        invoice = engine.generate_invoice(tenant)
        assert invoice.amount_cents == 2_900  # Starter monthly
        assert len(invoice.line_items) == 1

    def test_generate_invoice_with_overage(self):
        engine = BillingEngine()
        tenant = Tenant(
            id="t1",
            plan=TenantPlan.STARTER,
            max_api_calls_per_month=100_000,
            max_storage_bytes=10_737_418_240,
        )
        # Record overage usage
        engine.record_usage("t1", "api_calls", 150_000)  # 50k over
        engine.record_usage("t1", "storage_bytes", 21_474_836_480)  # 10 GB over
        invoice = engine.generate_invoice(tenant)
        assert invoice.amount_cents > 2_900  # Base + overage
        assert len(invoice.line_items) >= 3  # Base + API overage + storage overage

    def test_get_invoices(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.PROFESSIONAL)
        engine.generate_invoice(tenant)
        engine.generate_invoice(tenant)
        invoices = engine.get_invoices("t1")
        assert len(invoices) == 2

    def test_mark_paid(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.STARTER)
        invoice = engine.generate_invoice(tenant)
        assert engine.mark_paid(invoice.id, "t1") is True
        assert invoice.status == "paid"
        assert invoice.paid_at is not None

    def test_void_invoice(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.STARTER)
        invoice = engine.generate_invoice(tenant)
        assert engine.void_invoice(invoice.id, "t1") is True
        assert invoice.status == "void"

    def test_outstanding_balance(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.STARTER)
        engine.generate_invoice(tenant)
        engine.generate_invoice(tenant)
        balance = engine.get_outstanding_balance_cents("t1")
        assert balance == 5_800  # 2 * $29

    def test_change_plan(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.FREE)
        engine.change_plan(tenant, TenantPlan.PROFESSIONAL)
        assert tenant.plan == TenantPlan.PROFESSIONAL
        assert tenant.max_users == 100

    def test_change_plan_same_plan_returns_none(self):
        engine = BillingEngine()
        tenant = Tenant(id="t1", plan=TenantPlan.FREE)
        result = engine.change_plan(tenant, TenantPlan.FREE)
        assert result is None


# ============================================================================
# Tenant Monitoring Tests
# ============================================================================


class TestMetricsCollector:
    def test_record_metric(self):
        collector = MetricsCollector()
        sample = collector.record("t1", "cpu_usage", 75.5)
        assert sample.tenant_id if hasattr(sample, "tenant_id") else True
        assert sample.name == "cpu_usage"
        assert sample.value == 75.5

    def test_get_samples(self):
        collector = MetricsCollector()
        collector.record("t1", "cpu", 50)
        collector.record("t1", "cpu", 75)
        collector.record("t1", "memory", 80)
        samples = collector.get_samples("t1", "cpu")
        assert len(samples) == 2

    def test_get_aggregate_avg(self):
        collector = MetricsCollector()
        collector.record("t1", "latency", 100)
        collector.record("t1", "latency", 200)
        collector.record("t1", "latency", 300)
        avg = collector.get_aggregate("t1", "latency", "avg")
        assert avg == 200

    def test_get_aggregate_sum(self):
        collector = MetricsCollector()
        collector.record("t1", "requests", 10)
        collector.record("t1", "requests", 20)
        total = collector.get_aggregate("t1", "requests", "sum")
        assert total == 30

    def test_get_aggregate_min_max(self):
        collector = MetricsCollector()
        collector.record("t1", "latency", 50)
        collector.record("t1", "latency", 150)
        collector.record("t1", "latency", 100)
        assert collector.get_aggregate("t1", "latency", "min") == 50
        assert collector.get_aggregate("t1", "latency", "max") == 150

    def test_get_aggregate_count(self):
        collector = MetricsCollector()
        collector.record("t1", "events", 1)
        collector.record("t1", "events", 1)
        collector.record("t1", "events", 1)
        assert collector.get_aggregate("t1", "events", "count") == 3

    def test_clear(self):
        collector = MetricsCollector()
        collector.record("t1", "metric", 1)
        collector.clear("t1")
        assert collector.get_samples("t1", "metric") == []

    def test_max_samples_trims(self):
        collector = MetricsCollector(max_samples_per_metric=5)
        for i in range(10):
            collector.record("t1", "metric", i)
        samples = collector.get_samples("t1", "metric")
        assert len(samples) == 5


class TestTenantMonitor:
    def test_register_and_run_health_check(self):
        monitor = TenantMonitor()

        def dummy_check(tenant_id):
            from apex_os_bp.multitenancy.monitoring import HealthCheckResult

            return HealthCheckResult(
                name="dummy",
                status=HealthStatus.HEALTHY,
                latency_ms=10,
            )

        monitor.register_health_check("dummy", dummy_check)
        results = monitor.run_health_checks("t1")
        assert len(results) == 1
        assert results[0].status == HealthStatus.HEALTHY

    def test_overall_health_healthy(self):
        monitor = TenantMonitor()

        def healthy_check(tenant_id):
            from apex_os_bp.multitenancy.monitoring import HealthCheckResult

            return HealthCheckResult(
                name="check", status=HealthStatus.HEALTHY, latency_ms=5
            )

        monitor.register_health_check("check", healthy_check)
        assert monitor.get_overall_health("t1") == HealthStatus.HEALTHY

    def test_overall_health_unhealthy(self):
        monitor = TenantMonitor()

        def unhealthy_check(tenant_id):
            from apex_os_bp.multitenancy.monitoring import HealthCheckResult

            return HealthCheckResult(
                name="check", status=HealthStatus.UNHEALTHY, latency_ms=500
            )

        monitor.register_health_check("check", unhealthy_check)
        assert monitor.get_overall_health("t1") == HealthStatus.UNHEALTHY

    def test_overall_health_degraded(self):
        monitor = TenantMonitor()

        def healthy_check(tenant_id):
            from apex_os_bp.multitenancy.monitoring import HealthCheckResult

            return HealthCheckResult(
                name="h", status=HealthStatus.HEALTHY, latency_ms=5
            )

        def degraded_check(tenant_id):
            from apex_os_bp.multitenancy.monitoring import HealthCheckResult

            return HealthCheckResult(
                name="d", status=HealthStatus.DEGRADED, latency_ms=200
            )

        monitor.register_health_check("h", healthy_check)
        monitor.register_health_check("d", degraded_check)
        assert monitor.get_overall_health("t1") == HealthStatus.DEGRADED

    def test_alert_rule_triggers(self):
        monitor = TenantMonitor()
        monitor.register_alert_rule(
            name="high_cpu",
            metric="cpu_usage",
            condition="gt",
            threshold=90,
            severity="critical",
            window_minutes=5,
        )
        monitor.record_metric("t1", "cpu_usage", 95)
        alerts = monitor.check_alerts("t1")
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].is_resolved is False

    def test_alert_rule_no_trigger(self):
        monitor = TenantMonitor()
        monitor.register_alert_rule(
            name="high_cpu",
            metric="cpu_usage",
            condition="gt",
            threshold=90,
            window_minutes=5,
        )
        monitor.record_metric("t1", "cpu_usage", 50)
        alerts = monitor.check_alerts("t1")
        assert len(alerts) == 0

    def test_alert_deduplication(self):
        monitor = TenantMonitor()
        monitor.register_alert_rule(
            name="high_cpu",
            metric="cpu_usage",
            condition="gt",
            threshold=90,
            window_minutes=5,
        )
        monitor.record_metric("t1", "cpu_usage", 95)
        alerts1 = monitor.check_alerts("t1")
        alerts2 = monitor.check_alerts("t1")
        assert len(alerts1) == 1
        assert len(alerts2) == 0  # Already alerted

    def test_resolve_alert(self):
        monitor = TenantMonitor()
        monitor.register_alert_rule(
            name="high_cpu",
            metric="cpu_usage",
            condition="gt",
            threshold=90,
            window_minutes=5,
        )
        monitor.record_metric("t1", "cpu_usage", 95)
        alerts = monitor.check_alerts("t1")
        assert monitor.resolve_alert("t1", alerts[0].id) is True
        assert alerts[0].is_resolved is True
        assert alerts[0].resolved_at is not None

    def test_get_alerts_filter_by_severity(self):
        monitor = TenantMonitor()
        monitor.register_alert_rule(
            name="critical_alert",
            metric="cpu_usage",
            condition="gt",
            threshold=90,
            severity="critical",
            window_minutes=5,
        )
        monitor.register_alert_rule(
            name="warning_alert",
            metric="memory_usage",
            condition="gt",
            threshold=80,
            severity="warning",
            window_minutes=5,
        )
        monitor.record_metric("t1", "cpu_usage", 95)
        monitor.record_metric("t1", "memory_usage", 85)
        monitor.check_alerts("t1")

        critical = monitor.get_alerts("t1", severity="critical")
        warning = monitor.get_alerts("t1", severity="warning")
        assert len(critical) == 1
        assert len(warning) == 1

    def test_get_alerts_excludes_resolved(self):
        monitor = TenantMonitor()
        monitor.register_alert_rule(
            name="test_alert",
            metric="cpu_usage",
            condition="gt",
            threshold=90,
            window_minutes=5,
        )
        monitor.record_metric("t1", "cpu_usage", 95)
        alerts = monitor.check_alerts("t1")
        monitor.resolve_alert("t1", alerts[0].id)

        open_alerts = monitor.get_alerts("t1", include_resolved=False)
        all_alerts = monitor.get_alerts("t1", include_resolved=True)
        assert len(open_alerts) == 0
        assert len(all_alerts) == 1

    def test_tenant_dashboard(self):
        monitor = TenantMonitor()

        def healthy_check(tenant_id):
            from apex_os_bp.multitenancy.monitoring import HealthCheckResult

            return HealthCheckResult(
                name="check", status=HealthStatus.HEALTHY, latency_ms=5
            )

        monitor.register_health_check("check", healthy_check)
        monitor.record_metric("t1", "cpu_usage", 45)
        dashboard = monitor.get_tenant_dashboard("t1")
        assert dashboard["tenant_id"] == "t1"
        assert dashboard["health"] == "healthy"
        assert "recent_metrics" in dashboard
        assert dashboard["timestamp"] is not None

    def test_record_metric(self):
        monitor = TenantMonitor()
        sample = monitor.record_metric("t1", "requests", 100)
        assert sample.name == "requests"
        assert sample.value == 100


# ============================================================================
# Tenant Security Tests
# ============================================================================


class TestTenantRBAC:
    def test_assign_and_get_role(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "u1", TenantRole.ADMIN)
        assert rbac.get_role("t1", "u1") == TenantRole.ADMIN

    def test_owner_has_all_permissions(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "owner", TenantRole.OWNER)
        perms = rbac.get_permissions("t1", "owner")
        assert perms == set(TenantPermission)

    def test_admin_permissions(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "admin", TenantRole.ADMIN)
        perms = rbac.get_permissions("t1", "admin")
        assert TenantPermission.READ in perms
        assert TenantPermission.WRITE in perms
        assert TenantPermission.MANAGE_USERS in perms
        assert TenantPermission.MANAGE_BILLING not in perms

    def test_member_permissions(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "member", TenantRole.MEMBER)
        perms = rbac.get_permissions("t1", "member")
        assert perms == {TenantPermission.READ, TenantPermission.WRITE}

    def test_viewer_permissions(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "viewer", TenantRole.VIEWER)
        perms = rbac.get_permissions("t1", "viewer")
        assert perms == {TenantPermission.READ}

    def test_has_permission(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "admin", TenantRole.ADMIN)
        assert rbac.has_permission("t1", "admin", TenantPermission.READ) is True
        assert rbac.has_permission("t1", "admin", TenantPermission.MANAGE_BILLING) is False

    def test_has_any_permission(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "member", TenantRole.MEMBER)
        assert rbac.has_any_permission(
            "t1", "member", {TenantPermission.READ, TenantPermission.DELETE}
        ) is True
        assert rbac.has_any_permission(
            "t1", "member", {TenantPermission.DELETE, TenantPermission.MANAGE_USERS}
        ) is False

    def test_has_all_permissions(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "admin", TenantRole.ADMIN)
        assert rbac.has_all_permissions(
            "t1", "admin", {TenantPermission.READ, TenantPermission.WRITE}
        ) is True
        assert rbac.has_all_permissions(
            "t1", "admin", {TenantPermission.READ, TenantPermission.MANAGE_BILLING}
        ) is False

    def test_grant_custom_permission(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "member", TenantRole.MEMBER)
        rbac.grant_permission("t1", "member", TenantPermission.MANAGE_SETTINGS)
        assert rbac.has_permission("t1", "member", TenantPermission.MANAGE_SETTINGS) is True

    def test_revoke_custom_permission(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "member", TenantRole.MEMBER)
        rbac.grant_permission("t1", "member", TenantPermission.MANAGE_SETTINGS)
        rbac.revoke_permission("t1", "member", TenantPermission.MANAGE_SETTINGS)
        assert rbac.has_permission("t1", "member", TenantPermission.MANAGE_SETTINGS) is False

    def test_remove_user(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "u1", TenantRole.MEMBER)
        assert rbac.remove_user("t1", "u1") is True
        assert rbac.get_role("t1", "u1") is None

    def test_list_users(self):
        rbac = TenantRBAC()
        rbac.assign_role("t1", "u1", TenantRole.ADMIN)
        rbac.assign_role("t1", "u2", TenantRole.MEMBER)
        users = rbac.list_users("t1")
        assert len(users) == 2
        assert users["u1"] == TenantRole.ADMIN
        assert users["u2"] == TenantRole.MEMBER

    def test_no_role_returns_empty_permissions(self):
        rbac = TenantRBAC()
        perms = rbac.get_permissions("t1", "unknown")
        assert perms == set()


class TestTenantEncryption:
    def test_generate_key(self):
        enc = TenantEncryption()
        key_id = enc.generate_key("t1")
        assert key_id is not None
        assert len(key_id) > 0

    def test_get_key(self):
        enc = TenantEncryption()
        key_id = enc.generate_key("t1")
        key_data = enc.get_key("t1")
        assert key_data is not None
        assert key_data["key_id"] == key_id

    def test_get_key_material(self):
        enc = TenantEncryption()
        enc.generate_key("t1")
        material = enc.get_key_material("t1")
        assert material is not None
        assert len(material) == 32

    def test_encrypt_decrypt_roundtrip(self):
        enc = TenantEncryption()
        enc.generate_key("t1")
        plaintext = b"Hello, tenant world!"
        ciphertext = enc.encrypt("t1", plaintext)
        assert ciphertext is not None
        assert ciphertext != plaintext
        decrypted = enc.decrypt("t1", ciphertext)
        assert decrypted == plaintext

    def test_encrypt_without_key_returns_none(self):
        enc = TenantEncryption()
        result = enc.encrypt("no-key-tenant", b"data")
        assert result is None

    def test_rotate_key(self):
        enc = TenantEncryption()
        old_key_id = enc.generate_key("t1")
        new_key_id = enc.rotate_key("t1")
        assert new_key_id is not None
        assert new_key_id != old_key_id

    def test_needs_rotation(self):
        enc = TenantEncryption()
        enc.generate_key("t1")
        assert enc.needs_rotation("t1") is False

    def test_needs_rotation_no_key(self):
        enc = TenantEncryption()
        assert enc.needs_rotation("no-key") is True

    def test_different_tenants_different_keys(self):
        enc = TenantEncryption()
        enc.generate_key("t1")
        enc.generate_key("t2")
        plaintext = b"secret"
        ct1 = enc.encrypt("t1", plaintext)
        ct2 = enc.encrypt("t2", plaintext)
        assert ct1 != ct2


class TestTenantAPIKeyManager:
    def test_create_key(self):
        mgr = TenantAPIKeyManager()
        plain_key, api_key = mgr.create_key("t1", name="Test Key")
        assert plain_key.startswith("apk_")
        assert api_key.tenant_id == "t1"
        assert api_key.name == "Test Key"
        assert api_key.is_active is True

    def test_validate_key(self):
        mgr = TenantAPIKeyManager()
        plain_key, _ = mgr.create_key("t1")
        validated = mgr.validate_key(plain_key)
        assert validated is not None
        assert validated.tenant_id == "t1"

    def test_validate_invalid_key(self):
        mgr = TenantAPIKeyManager()
        result = mgr.validate_key("apk_invalid_key_12345")
        assert result is None

    def test_revoke_key(self):
        mgr = TenantAPIKeyManager()
        plain_key, api_key = mgr.create_key("t1")
        assert mgr.revoke_key("t1", api_key.id) is True
        assert mgr.validate_key(plain_key) is None

    def test_list_keys(self):
        mgr = TenantAPIKeyManager()
        mgr.create_key("t1", name="Key 1")
        mgr.create_key("t1", name="Key 2")
        keys = mgr.list_keys("t1")
        assert len(keys) == 2

    def test_delete_key(self):
        mgr = TenantAPIKeyManager()
        _, api_key = mgr.create_key("t1")
        assert mgr.delete_key("t1", api_key.id) is True
        assert len(mgr.list_keys("t1")) == 0

    def test_key_with_expiry(self):
        mgr = TenantAPIKeyManager()
        plain_key, api_key = mgr.create_key("t1", expires_in_days=1)
        assert api_key.expires_at is not None
        assert mgr.validate_key(plain_key) is not None

    def test_expired_key_rejected(self):
        mgr = TenantAPIKeyManager()
        plain_key, api_key = mgr.create_key("t1", expires_in_days=1)
        # Manually expire
        api_key.expires_at = datetime.utcnow() - timedelta(days=1)
        assert mgr.validate_key(plain_key) is None

    def test_key_scopes(self):
        mgr = TenantAPIKeyManager()
        _, api_key = mgr.create_key("t1", scopes=["read", "write"])
        assert api_key.scopes == ["read", "write"]


class TestSecurityPolicy:
    def test_validate_password_valid(self):
        policy = SecurityPolicy(tenant_id="t1")
        valid, errors = policy.validate_password("MyStr0ng!Pass")
        assert valid is True
        assert errors == []

    def test_validate_password_too_short(self):
        policy = SecurityPolicy(tenant_id="t1", password_min_length=12)
        valid, errors = policy.validate_password("Sh0rt!")
        assert valid is False
        assert any("at least" in e for e in errors)

    def test_validate_password_no_uppercase(self):
        policy = SecurityPolicy(tenant_id="t1")
        valid, errors = policy.validate_password("alllowercase1!")
        assert valid is False
        assert any("uppercase" in e for e in errors)

    def test_validate_password_no_lowercase(self):
        policy = SecurityPolicy(tenant_id="t1")
        valid, errors = policy.validate_password("ALLUPPERCASE1!")
        assert valid is False
        assert any("lowercase" in e for e in errors)

    def test_validate_password_no_number(self):
        policy = SecurityPolicy(tenant_id="t1")
        valid, errors = policy.validate_password("NoNumbersHere!")
        assert valid is False
        assert any("number" in e for e in errors)

    def test_validate_password_no_special(self):
        policy = SecurityPolicy(tenant_id="t1")
        valid, errors = policy.validate_password("NoSpecial123")
        assert valid is False
        assert any("special" in e for e in errors)

    def test_ip_allowed_no_whitelist(self):
        policy = SecurityPolicy(tenant_id="t1", enforce_ip_whitelist=False)
        assert policy.is_ip_allowed("192.168.1.1") is True

    def test_ip_allowed_with_whitelist(self):
        policy = SecurityPolicy(
            tenant_id="t1",
            enforce_ip_whitelist=True,
            allowed_ip_ranges=["10.0.0.0/8"],
        )
        assert policy.is_ip_allowed("10.0.0.1") is True
        assert policy.is_ip_allowed("192.168.1.1") is False

    def test_to_dict(self):
        policy = SecurityPolicy(tenant_id="t1")
        d = policy.to_dict()
        assert d["tenant_id"] == "t1"
        assert d["password_min_length"] == 12
        assert d["encryption_at_rest"] is True


class TestTenantAuditLogger:
    def test_log_creates_entry(self):
        logger = TenantAuditLogger()
        entry = logger.log(
            tenant_id="t1",
            action="user.login",
            user_id="u1",
            resource_type="session",
        )
        assert entry.tenant_id == "t1"
        assert entry.action == "user.login"
        assert entry.user_id == "u1"

    def test_get_logs(self):
        logger = TenantAuditLogger()
        logger.log("t1", "action1", user_id="u1")
        logger.log("t1", "action2", user_id="u2")
        logger.log("t2", "action3", user_id="u1")
        logs = logger.get_logs("t1")
        assert len(logs) == 2

    def test_get_logs_filter_by_user(self):
        logger = TenantAuditLogger()
        logger.log("t1", "action1", user_id="u1")
        logger.log("t1", "action2", user_id="u2")
        logs = logger.get_logs("t1", user_id="u1")
        assert len(logs) == 1
        assert logs[0].user_id == "u1"

    def test_get_logs_filter_by_action(self):
        logger = TenantAuditLogger()
        logger.log("t1", "user.login")
        logger.log("t1", "user.logout")
        logs = logger.get_logs("t1", action="user.login")
        assert len(logs) == 1

    def test_get_logs_filter_by_resource_type(self):
        logger = TenantAuditLogger()
        logger.log("t1", "create", resource_type="document")
        logger.log("t1", "delete", resource_type="user")
        logs = logger.get_logs("t1", resource_type="document")
        assert len(logs) == 1

    def test_get_logs_with_since(self):
        logger = TenantAuditLogger()
        logger.log("t1", "old_action")
        logger._logs["t1"][-1].timestamp = datetime.utcnow() - timedelta(hours=2)
        logger.log("t1", "recent_action")
        logs = logger.get_logs("t1", since=datetime.utcnow() - timedelta(hours=1))
        assert len(logs) == 1
        assert logs[0].action == "recent_action"

    def test_get_logs_limit(self):
        logger = TenantAuditLogger()
        for i in range(20):
            logger.log("t1", f"action_{i}")
        logs = logger.get_logs("t1", limit=5)
        assert len(logs) == 5

    def test_clear(self):
        logger = TenantAuditLogger()
        logger.log("t1", "action")
        logger.clear("t1")
        assert logger.get_logs("t1") == []


# ============================================================================
# Integration Tests
# ============================================================================


class TestMultiTenancyIntegration:
    def test_full_tenant_lifecycle(self):
        """Test the complete lifecycle: provision → use → monitor → suspend → delete."""
        provisioner = TenantProvisioner()
        monitor = TenantMonitor()
        billing = BillingEngine()

        # Provision
        result = provisioner.provision(
            name="Integration Test",
            slug="integration-test",
            plan=TenantPlan.PROFESSIONAL,
            admin_email="admin@integration.com",
        )
        assert result.success is True
        tenant = result.tenant

        # Use tenant context
        with TenantContext(tenant.id):
            assert get_current_tenant() == tenant.id

            # Record usage
            billing.record_usage(tenant.id, "api_calls", 50_000)

            # Monitor
            monitor.record_metric(tenant.id, "cpu_usage", 65)

            # Check alerts
            monitor.register_alert_rule(
                name="high_cpu",
                metric="cpu_usage",
                condition="gt",
                threshold=90,
                window_minutes=5,
            )
            alerts = monitor.check_alerts(tenant.id)
            assert len(alerts) == 0  # 65 < 90

        # Generate invoice
        invoice = billing.generate_invoice(tenant)
        assert invoice.amount_cents == 9_900  # Professional plan

        # Suspend
        assert provisioner.suspend(tenant.id, "test suspension") is True
        assert tenant.status == TenantStatus.SUSPENDED

        # Resume
        assert provisioner.resume(tenant.id) is True
        assert tenant.status == TenantStatus.ACTIVE

        # Delete
        assert provisioner.delete(tenant.id) is True
        assert tenant.status == TenantStatus.DELETED

    def test_tenant_isolation_end_to_end(self):
        """Verify data isolation between two tenants."""
        provisioner = TenantProvisioner()

        r1 = provisioner.provision(
            name="Tenant A", slug="tenant-a", admin_email="a@a.com"
        )
        r2 = provisioner.provision(
            name="Tenant B", slug="tenant-b", admin_email="b@b.com"
        )

        # Add users to each tenant
        provisioner.add_user(r1.tenant.id, "user1@a.com")
        provisioner.add_user(r2.tenant.id, "user2@b.com")

        # Verify isolation
        users_a = provisioner.get_tenant_users(r1.tenant.id)
        users_b = provisioner.get_tenant_users(r2.tenant.id)
        assert len(users_a) == 2  # admin + user1
        assert len(users_b) == 2  # admin + user2
        assert all(u.tenant_id == r1.tenant.id for u in users_a)
        assert all(u.tenant_id == r2.tenant.id for u in users_b)

    def test_security_rbac_integration(self):
        """Test RBAC with provisioning."""
        provisioner = TenantProvisioner()
        rbac = TenantRBAC()

        result = provisioner.provision(
            name="RBAC Test", slug="rbac-test", admin_email="admin@rbac.com"
        )
        tenant_id = result.tenant.id
        admin_id = result.admin_user.id

        # Assign admin role
        rbac.assign_role(tenant_id, admin_id, TenantRole.OWNER)

        # Verify permissions
        assert rbac.has_permission(tenant_id, admin_id, TenantPermission.MANAGE_USERS)
        assert rbac.has_permission(tenant_id, admin_id, TenantPermission.MANAGE_BILLING)
        assert rbac.has_permission(tenant_id, admin_id, TenantPermission.VIEW_AUDIT_LOG)

    def test_monitoring_with_billing_integration(self):
        """Test that monitoring metrics feed into billing."""
        provisioner = TenantProvisioner()
        monitor = TenantMonitor()
        billing = BillingEngine()

        result = provisioner.provision(
            name="Monitor Billing", slug="mon-bill",
            plan=TenantPlan.STARTER, admin_email="a@b.com",
        )
        tenant = result.tenant

        # Record usage through monitor
        monitor.record_metric(tenant.id, "api_calls", 120_000)

        # Transfer monitor metrics to billing
        collector = monitor.get_metrics_collector()
        api_usage = collector.get_aggregate(tenant.id, "api_calls", "sum")
        if api_usage:
            billing.record_usage(tenant.id, "api_calls", api_usage)

        # Generate invoice — should include overage
        invoice = billing.generate_invoice(tenant)
        assert invoice.amount_cents > 2_900  # Base + overage
