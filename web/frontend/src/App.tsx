import { Routes, Route } from 'react-router-dom'
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

function App() {
  return (
    <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
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
        </Route>
      </Routes>
  )
}

export default App