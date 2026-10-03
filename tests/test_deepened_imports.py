"""
Comprehensive import verification for all deepened modules.
Verifies that all 50 deepened modules can be imported and have expected classes/functions.
"""
import importlib
import pytest
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "apex_os_bp")

# All 50 deepened modules with their expected classes
DEEPENED_MODULES = {
    "accounting": ["CurrencyConverter", "RecurringEntry", "FinancialStatement", "BudgetComparator", "TaxEngine"],
    "crm": ["LeadScorer", "PipelineAutomator", "EmailTracker", "SegmentationEngine", "ChurnPredictor"],
    "analytics": ["CohortAnalyzer", "FunnelAnalyzer", "TimeSeriesForecaster", "AnomalyDetector", "CorrelationAnalyzer"],
    "security": ["TokenManager", "OAuth2Provider", "SAMLProvider", "AccessControl", "SecurityHeadersMiddleware"],
    "workflow": ["ParallelTask", "ConditionalBranch", "SubWorkflow", "VersionedWorkflow", "WorkflowAnalytics"],
    "database": ["QueryBuilder", "ConnectionPool", "ReadReplica", "ShardingManager", "FullTextSearch"],
    "api": ["GraphQLHandler", "WebSocketManager", "VersionNegotiator", "RateLimiter", "OpenAPIDoc"],
    "cache": ["MultiLevelCache", "CacheInvalidator", "CacheWarmer", "CacheAnalytics", "RedisCluster"],
    "notifications": ["PushNotifier", "InAppNotifier", "NotificationPreference", "NotificationTemplate", "NotificationAnalytics"],
    "integration": ["WebhookManager", "APIKeyManager", "IntegrationMarketplace", "DataMapper", "IntegrationAnalytics"],
    "ecommerce": ["ShoppingCart", "OrderManager", "PaymentProcessor", "InventoryManager", "ProductCatalog"],
    "marketing": ["CampaignManager", "EmailMarketing", "SocialScheduler", "AttributionEngine", "ROICalculator"],
    "support": ["TicketManager", "KnowledgeBase", "LiveChat", "SatisfactionSurvey", "SupportAnalytics"],
    "supply_chain": ["DemandForecaster", "SupplierManager", "LogisticsOptimizer", "WarehouseManager", "ProcurementManager"],
    "manufacturing": ["MRPPlanner", "QualityController", "MaintenanceScheduler", "BOMManager", "ShopFloorController"],
    "hr": ["RecruitmentPipeline", "PerformanceManager", "LearningManager", "PayrollEngine", "EngagementSurvey"],
    "projects": ["GanttChart", "ResourceAllocator", "TimeTracker", "RiskManager", "PortfolioManager"],
    "blockchain": ["ContractManager", "TokenManager", "ConsensusManager", "CrossChainBridge", "BlockchainAnalytics"],
    "ml": ["ModelTrainer", "ModelEvaluator", "ModelDeployer", "FeatureEngineer", "ModelMonitor"],
    "ai": ["ConversationalAI", "DocumentAI", "VisionAI", "SpeechAI", "RecommendationEngine"],
    "iot": ["DeviceManager", "MQTTClient", "DeviceMonitor", "DeviceShadow", "OTAUpdater"],
    "nlp": ["NERProcessor", "SentimentAnalyzer", "TextClassifier", "Translator", "QuestionAnswerer"],
    "vision": ["YOLODetector", "CNNClassifier", "UNetSegmenter", "FaceRecognizer", "VideoTracker"],
    "speech": ["ASRProcessor", "TTSProcessor", "SpeakerIdentifier", "EmotionRecognizer", "RealtimeTranscriber"],
    "knowledge": ["KnowledgeGraph", "OntologyManager", "ReasoningEngine", "SemanticSearch", "KnowledgeExtractor"],
    "gamification": ["PointsSystem", "BadgeManager", "Leaderboard", "QuestManager", "ChallengeManager"],
    "data_warehouse": ["ETLPipeline", "StarSchema", "DataMart", "SCDManager", "DataQuality"],
    "bi": ["DashboardBuilder", "AdHocReporter", "DataVisualizer", "ReportScheduler", "SelfServiceAnalytics"],
    "event_sourcing": ["EventStore", "EventReplayer", "EventUpcaster", "Projection", "SagaManager"],
    "cqrs": ["CommandHandler", "QueryHandler", "EventBus", "MaterializedView", "CQRSMetrics"],
    "multitenancy": ["TenantIsolation", "TenantProvisioner", "TenantBilling", "TenantCustomizer", "TenantMigration"],
    "audit": ["AuditTrail", "ComplianceReporter", "DataLineage", "AuditAnalytics", "AuditExporter"],
    "reporting": ["ReportBuilder", "ReportTemplate", "ReportScheduler", "ReportExporter", "ReportSharing"],
    "data_exchange": ["DataImporter", "DataExporter", "DataTransformer", "DataValidator", "DataSynchronizer"],
    "tasks": ["SubtaskManager", "TaskDependency", "TaskTemplate", "TaskAutomation", "TaskAnalytics"],
    "documents": ["DocumentManager", "DocumentCollaboration", "DocumentTemplate", "DocumentSearch", "DocumentWorkflow"],
    "billing": ["SubscriptionManager", "InvoiceGenerator", "PaymentProcessor", "DunningManager", "RevenueRecognition"],
    "inventory": ["StockManager", "WarehouseManager", "SerialTracker", "CycleCounter", "InventoryValuation"],
    "contracts": ["ContractLifecycle", "ContractTemplate", "ContractNegotiation", "ContractCompliance", "ContractAnalytics"],
    "compliance": ["PolicyManager", "RiskAssessor", "ControlTester", "ComplianceReporter", "RegulatoryChange"],
    "assets": ["AssetTracker", "AssetMaintenance", "AssetLifecycle", "AssetValuation", "AssetReporting"],
    "feature_flags": ["FlagTargeting", "FlagAnalytics", "FlagLifecycle", "FlagDependency", "FlagAudit"],
    "monitoring": ["HealthChecker", "MetricsCollector", "LogAggregator", "Tracer", "Alerter"],
    "logging": ["StructuredLogger", "LogLevelAdjuster", "LogSampler", "LogCorrelator", "LogRetention"],
    "tracing": ["SpanManager", "TraceSampler", "TraceAnalytics", "TraceCorrelator", "TraceExporter"],
    "metrics": ["CounterMetric", "GaugeMetric", "HistogramMetric", "SummaryMetric", "MetricExporter"],
    "alerting": ["AlertRule", "AlertRouter", "AlertSuppressor", "AlertNotifier", "AlertAnalytics"],
    "backup": ["BackupScheduler", "BackupEncryptor", "BackupVerifier", "BackupRetention", "BackupRestore"],
    "disaster_recovery": ["DRPlanner", "DRTester", "DRFailover", "DRRunbook", "DRMetrics"],
    "capacity_planning": ["ResourceForecaster", "CapacityOptimizer", "CostOptimizer", "PerformanceModel", "ScalabilityTester"],
}


def get_module_path(module_name: str) -> str:
    """Get the full module path for a deepened module."""
    return f"apex_os_bp.{module_name}.deepened"


@pytest.mark.parametrize("module_name", sorted(DEEPENED_MODULES.keys()))
def test_deepened_module_importable(module_name: str):
    """Test that each deepened module can be imported."""
    module_path = get_module_path(module_name)
    try:
        mod = importlib.import_module(module_path)
        assert mod is not None
    except ImportError as e:
        pytest.fail(f"Cannot import {module_path}: {e}")


@pytest.mark.parametrize("module_name", sorted(DEEPENED_MODULES.keys()))
def test_deepened_module_has_classes(module_name: str):
    """Test that each deepened module has the expected classes."""
    module_path = get_module_path(module_name)
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        pytest.skip(f"Module {module_path} not importable")
    
    expected_classes = DEEPENED_MODULES[module_name]
    for class_name in expected_classes:
        assert hasattr(mod, class_name), f"{module_path} missing class {class_name}"


def test_all_50_deepened_modules_exist():
    """Test that all 50 deepened module files exist."""
    for module_name in DEEPENED_MODULES:
        fp = os.path.join(BASE_DIR, module_name, "deepened.py")
        assert os.path.exists(fp), f"Missing deepened module: {fp}"


def test_deepened_modules_have_functions():
    """Test that deepened modules have callable functions."""
    for module_name in DEEPENED_MODULES:
        module_path = get_module_path(module_name)
        try:
            mod = importlib.import_module(module_path)
        except ImportError:
            continue
        
        # Check that module has at least some callable attributes
        callables = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith("_")]
        assert len(callables) > 0, f"{module_path} has no callable attributes"
