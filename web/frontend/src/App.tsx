import { Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Accounting from './pages/Accounting'
import CRM from './pages/CRM'
import Analytics from './pages/Analytics'
import AgentReach from './pages/AgentReach'
import BigData from './pages/BigData'
import DataScience from './pages/DataScience'
import ContinuousBI from './pages/ContinuousBI'
import ContinuousBICRUD from './pages/ContinuousBICRUD'
import CRMCRUD from './pages/CRMCRUD'
import AccountingCRUD from './pages/AccountingCRUD'
import DashboardCRUD from './pages/DashboardCRUD'
import AnalyticsCRUD from './pages/AnalyticsCRUD'
import AgentReachCRUD from './pages/AgentReachCRUD'
import BigDataCRUD from './pages/BigDataCRUD'
import DataScienceCRUD from './pages/DataScienceCRUD'
import UserCRUD from './pages/UserCRUD'
import JournalEntryCRUD from './pages/JournalEntryCRUD'
import InvoiceCRUD from './pages/InvoiceCRUD'
import UserManagement from './pages/UserManagement'
import LeadManagement from './pages/LeadManagement'
import ReportManagement from './pages/ReportManagement'
import DatabaseAdmin from './pages/DatabaseAdmin'
import ProductManagement from './pages/ProductManagement'
import OrderManagement from './pages/OrderManagement'
import CustomerManagement from './pages/CustomerManagement'
import EmployeeManagement from './pages/EmployeeManagement'
import ProjectManagement from './pages/ProjectManagement'
import TaskManagement from './pages/TaskManagement'
import InventoryManagement from './pages/InventoryManagement'
import PaymentManagement from './pages/PaymentManagement'
import InvoiceManagement from './pages/InvoiceManagement'
import OnboardingWizard from './pages/OnboardingWizard'
import SizingCalculator from './pages/SizingCalculator'
import RolesCRUD from './pages/RolesCRUD'
import PermissionsCRUD from './pages/PermissionsCRUD'
import OpportunitiesCRUD from './pages/OpportunitiesCRUD'
import CampaignsCRUD from './pages/CampaignsCRUD'
import AlertsCRUD from './pages/AlertsCRUD'
import ComplianceManagement from './pages/ComplianceManagement'
import SupplyChainManagement from './pages/SupplyChainManagement'
import IoTManagement from './pages/IoTManagement'
import ProjectMgmtManagement from './pages/ProjectMgmtManagement'
import BudgetingManagement from './pages/BudgetingManagement'
import HRManagement from './pages/HRManagement'
import ReportingManagement from './pages/ReportingManagement'
import ExportTemplateManagement from './pages/ExportTemplateManagement'
import AssetManagement from './pages/AssetManagement'
import ManufacturingManagement from './pages/ManufacturingManagement'
import NotificationCenter from './pages/NotificationCenter'
import MonitoringManagement from './pages/MonitoringManagement'
import DisasterRecoveryManagement from './pages/DisasterRecoveryManagement'
import CapacityPlanningManagement from './pages/CapacityPlanningManagement'
import DataWarehouseManagement from './pages/DataWarehouseManagement'
import CostManagement from './pages/CostManagement'
import KnowledgeBaseManagement from './pages/KnowledgeBaseManagement'
import WorkflowManagement from './pages/WorkflowManagement'
import IntegrationManagement from './pages/IntegrationManagement'

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="accounting" element={<Accounting />} />
          <Route path="crm" element={<CRM />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="agent-reach" element={<AgentReach />} />
          <Route path="bigdata" element={<BigData />} />
          <Route path="datascience" element={<DataScience />} />
          <Route path="continuous-bi" element={<ContinuousBI />} />
          <Route path="continuous-bi-crud" element={<ContinuousBICRUD />} />
          <Route path="crm-crud" element={<CRMCRUD />} />
          <Route path="accounting-crud" element={<AccountingCRUD />} />
          <Route path="dashboard-crud" element={<DashboardCRUD />} />
          <Route path="analytics-crud" element={<AnalyticsCRUD />} />
          <Route path="agent-reach-crud" element={<AgentReachCRUD />} />
          <Route path="bigdata-crud" element={<BigDataCRUD />} />
          <Route path="datascience-crud" element={<DataScienceCRUD />} />
          <Route path="users-crud" element={<UserCRUD />} />
          <Route path="journal-entries-crud" element={<JournalEntryCRUD />} />
          <Route path="invoices-crud" element={<InvoiceCRUD />} />
          <Route path="user-management" element={<UserManagement />} />
          <Route path="lead-management" element={<LeadManagement />} />
          <Route path="report-management" element={<ReportManagement />} />
          <Route path="database-admin" element={<DatabaseAdmin />} />
          <Route path="product-management" element={<ProductManagement />} />
          <Route path="order-management" element={<OrderManagement />} />
          <Route path="customer-management" element={<CustomerManagement />} />
          <Route path="employee-management" element={<EmployeeManagement />} />
          <Route path="project-management" element={<ProjectManagement />} />
          <Route path="task-management" element={<TaskManagement />} />
          <Route path="inventory-management" element={<InventoryManagement />} />
          <Route path="payment-management" element={<PaymentManagement />} />
          <Route path="invoice-management" element={<InvoiceManagement />} />
          <Route path="onboarding" element={<OnboardingWizard />} />
          <Route path="sizing" element={<SizingCalculator />} />
          <Route path="roles-crud" element={<RolesCRUD />} />
          <Route path="permissions-crud" element={<PermissionsCRUD />} />
          <Route path="opportunities-crud" element={<OpportunitiesCRUD />} />
          <Route path="campaigns-crud" element={<CampaignsCRUD />} />
          <Route path="alerts-crud" element={<AlertsCRUD />} />
          <Route path="compliance" element={<ComplianceManagement />} />
          <Route path="supply-chain" element={<SupplyChainManagement />} />
          <Route path="iot" element={<IoTManagement />} />
          <Route path="budgeting" element={<BudgetingManagement />} />
          <Route path="hr-management" element={<HRManagement />} />
          <Route path="reporting" element={<ReportingManagement />} />
          <Route path="export-templates" element={<ExportTemplateManagement />} />
          <Route path="asset-management" element={<AssetManagement />} />
          <Route path="manufacturing" element={<ManufacturingManagement />} />
          <Route path="notifications" element={<NotificationCenter />} />
          <Route path="monitoring" element={<MonitoringManagement />} />
          <Route path="disaster-recovery" element={<DisasterRecoveryManagement />} />
          <Route path="capacity-planning" element={<CapacityPlanningManagement />} />
          <Route path="data-warehouse" element={<DataWarehouseManagement />} />
          <Route path="knowledge-base" element={<KnowledgeBaseManagement />} />
          <Route path="project-mgmt" element={<ProjectMgmtManagement />} />
          <Route path="cost-management" element={<CostManagement />} />
          <Route path="workflows" element={<WorkflowManagement />} />
          <Route path="integrations" element={<IntegrationManagement />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}

export default App