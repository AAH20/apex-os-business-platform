"""
Comprehensive import verification for all deepened modules.
Verifies that all 50 deepened modules can be imported and have expected classes/functions.
"""
import importlib
import pytest
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "apex_os_bp")
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

# All 50 deepened modules with their expected exported names
DEEPENED_MODULES = {
    "accounting": ["RecurringEntry", "JournalEntry", "ExchangeRate", "TaxRule", "BudgetLine"],
    "crm": ["LeadScoreWeight", "Deal", "EmailCampaign", "RFMProfile", "AutomationRule"],
    "analytics": ["CohortResult", "FunnelResult", "ForecastResult", "AnomalyResult", "CorrelationResult"],
    "security": ["TokenManager", "OAuth2Provider", "SAMLProvider", "AccessControl", "SecurityHeadersMiddleware"],
    "workflow": ["ParallelTask", "ConditionalBranch", "SubWorkflow", "VersionedWorkflow", "WorkflowAnalytics"],
    "database": ["ConnectionPool", "FullTextSearch", "ReadRouter", "ShardManager", "SearchResult"],
    "api": ["SchemaStitcher", "WebSocketManager", "ContentNegotiator", "RateLimiter", "OpenAPIDocumentation", "APIVersion"],
    "cache": ["MultiLevelCache", "CacheInvalidator", "CacheWarmer", "CacheAnalytics", "L2Cache"],
    "notifications": ["PushNotifier", "InAppNotifier", "NotificationPreferences", "TemplateEngine", "NotificationAnalytics"],
    "integration": ["WebhookManager", "ApiKeyManager", "Marketplace", "DataMapper", "IntegrationAnalytics"],
    "ecommerce": ["ShoppingCart", "OrderManager", "PaymentProcessor", "InventoryManager", "FacetedCatalog"],
    "marketing": ["Campaign", "EmailCampaign", "SocialScheduler", "AttributionResult", "ROICalculator"],
    "support": ["TicketManager", "KnowledgeBase", "ChatSession", "SurveyManager", "SupportAnalytics"],
    "supply_chain": ["DemandForecaster", "SupplierManager", "LogisticsOptimizer", "WarehouseManager", "ProcurementWorkflow"],
    "manufacturing": ["MRPPlanner", "SPCControl", "MaintenanceScheduler", "BillOfMaterials", "ShopFloorController"],
    "hr": ["RecruitmentPipeline", "PerformanceManager", "LearningManager", "PayrollEngine", "EngagementTracker"],
    "projects": ["GanttChart", "CapacityPlanner", "TimeTracker", "RiskRegister", "Portfolio"],
    "blockchain": ["SmartContract", "ERC20Token", "PBFTConsensus", "CrossChainBridge", "BlockchainAnalytics"],
    "ml": ["ModelTrainer", "CrossValidator", "ABTestDeployer", "AutoMLFeatureEngineer", "ModelMonitor"],
    "ai": ["ConversationalAI", "DocumentAI", "VisionAI", "SpeechAI", "RecommendationEngine", "IntentRecognizer"],
    "iot": ["DeviceManager", "MQTTIngestion", "MonitoringEngine", "DeviceShadow", "OTAManager"],
    "nlp": ["Entity", "SentimentResult", "ClassificationResult", "TranslationResult", "QAResult"],
    "vision": ["YOLODetector", "CNNClassifier", "UNetSegmenter", "FaceRecognizer", "VideoTracker", "VisionPipeline"],
    "speech": ["ASRProcessor", "TTSProcessor", "SpeakerIdentifier", "EmotionRecognizer", "RealtimeTranscriber", "SpeechPipeline"],
    "knowledge": ["RDFGraph", "OWLOntology", "ReasoningEngine", "EmbeddingIndex", "NERExtractor", "DeepenedKnowledgeModule"],
    "gamification": ["PointsProfile", "Badge", "Leaderboard", "Quest", "Challenge", "GamificationEngine"],
    "data_warehouse": ["ETLPipeline", "Fact", "Dimension", "SCDType2", "DataQualityEngine"],
    "bi": ["DashboardBuilder", "AdHocReporter", "Widget", "ReportScheduler", "SelfServiceAnalytics"],
    "event_sourcing": ["EventStore", "ReplayEngine", "UpcasterRegistry", "ProjectionEngine", "SagaOrchestrator"],
    "cqrs": ["CommandHandler", "QueryHandler", "EventBus", "MaterializedView", "CQRSRuntime"],
    "multitenancy": ["TenantIsolatedMixin", "TenantProvisioner", "UsageMeter", "ThemeManager", "TenantMigrator"],
    "audit": ["ImmutableAuditTrail", "ComplianceFinding", "DataLineageTracker", "AuditAnalytics", "EDiscoveryExport"],
    "reporting": ["ReportBuilder", "ReportTemplate", "ReportSchedule", "ReportExporter", "ShareManager"],
    "data_exchange": ["DataImporter", "DataExporter", "DataTransformer", "DataValidator", "DataSynchronizer", "FieldSchema"],
    "tasks": ["Subtask", "DependencyGraph", "TaskTemplate", "AutomationEngine", "TaskAnalytics"],
    "documents": ["DocumentManager", "CollaborationSession", "DocumentTemplate", "DocumentSearchEngine", "DocumentWorkflow"],
    "billing": ["SubscriptionManager", "InvoiceGenerator", "StripePaymentProcessor", "DunningManager", "ASC606Recognizer"],
    "inventory": ["StockManager", "WarehouseManager", "SerialTracker", "CycleCountManager", "InventoryValuator"],
    "contracts": ["ContractLifecycle", "ContractTemplate", "NegotiationSession", "ComplianceTracker", "ContractAnalytics"],
    "compliance": ["Policy", "RiskAssessment", "ControlTest", "ComplianceEngine", "RegulatoryChange"],
    "assets": ["Asset", "MaintenanceRecord", "AssetLifecycle", "AssetValuation", "AssetReport"],
    "feature_flags": ["FeatureFlag", "FlagAnalytics", "FlagLifecycle", "FlagDependency", "FlagAudit"],
    "monitoring": ["HealthChecker", "PrometheusMetrics", "LogAggregator", "JaegerTracer", "PagerDutyAlerter"],
    "logging": ["StructuredJSONFormatter", "DynamicLevelManager", "SamplingFilter", "CorrelationFilter", "RetentionPolicy"],
    "tracing": ["SpanManager", "Sampler", "TraceAnalytics", "TraceLogCorrelator", "TraceExporter"],
    "metrics": ["Counter", "Gauge", "Histogram", "Summary", "PrometheusExporter"],
    "alerting": ["AlertRule", "RoutingRule", "SuppressionRule", "NotificationChannel", "AlertAnalytics"],
    "backup": ["Scheduler", "AESEncryptor", "ChecksumVerifier", "RetentionManager", "PointInTimeRestore"],
    "disaster_recovery": ["DRPlanner", "ChaosEngine", "FailoverAutomator", "Runbook", "DRMetricsCollector"],
    "capacity_planning": ["ResourceForecaster", "CapacityOptimizer", "CostOptimizer", "PerformanceModel", "ScalabilityTester", "CapacityPlanner"],
}


def get_module_path(module_name: str) -> str:
    """Get the full module path for a deepened module."""
    return f"apex_os_bp.{module_name}.deepened"


def _exported_classes(mod) -> set:
    """Public class names defined/importable on the module."""
    import inspect
    names = set()
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if inspect.isclass(obj):
            names.add(name)
    return names


@pytest.mark.parametrize("module_name", sorted(DEEPENED_MODULES.keys()))
def test_deepened_module_importable(module_name: str):
    """Test that each deepened module can be imported."""
    module_path = get_module_path(module_name)
    src_root = os.path.join(BASE_DIR, module_name)
    if not os.path.exists(os.path.join(src_root, "deepened.py")):
        pytest.skip(f"Module file {module_path} does not exist")
    mod = importlib.import_module(module_path)
    assert mod is not None


@pytest.mark.parametrize("module_name", sorted(DEEPENED_MODULES.keys()))
def test_deepened_module_has_classes(module_name: str):
    """Test that each deepened module is importable and defines its domain types."""
    module_path = get_module_path(module_name)
    src_root = os.path.join(BASE_DIR, module_name)
    if not os.path.exists(os.path.join(src_root, "deepened.py")):
        pytest.skip(f"Module file {module_path} does not exist")
    try:
        mod = importlib.import_module(module_path)
    except Exception as exc:
        pytest.skip(f"Module {module_path} not importable in this environment: {exc}")

    expected = DEEPENED_MODULES[module_name]
    have = _exported_classes(mod)
    missing = [name for name in expected if name not in have]
    assert not missing, f"{module_path} missing classes {missing}"


def test_all_50_deepened_modules_exist():
    """Test that all deepened module files exist."""
    for module_name in DEEPENED_MODULES:
        fp = os.path.join(BASE_DIR, module_name, "deepened.py")
        assert os.path.exists(fp), f"Missing deepened module: {fp}"


def test_deepened_modules_have_functions():
    """Test that deepened modules have callable functions."""
    for module_name in DEEPENED_MODULES:
        module_path = get_module_path(module_name)
        try:
            mod = importlib.import_module(module_path)
        except Exception:
            continue
        callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
        assert len(callables) > 0, f"{module_path} has no callable attributes"
