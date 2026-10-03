import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Accounting from './pages/Accounting'
import CRM from './pages/CRM'
import Analytics from './pages/Analytics'
import AgentReach from './pages/AgentReach'
import BigData from './pages/BigData'
import DataScience from './pages/DataScience'
import ContinuousBI from './pages/ContinuousBI'

function App() {
  return (
    <BrowserRouter>
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
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App