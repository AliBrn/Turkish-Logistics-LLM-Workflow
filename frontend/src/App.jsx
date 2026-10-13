import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import DashboardPage from './pages/Dashboard/DashboardPage'
import ExtractionPage from './pages/Extraction/ExtractionPage'
import OrdersPage from './pages/Orders/OrdersPage'
import RawMessagesPage from './pages/RawMessages/RawMessagesPage'
import ValidationPage from './pages/Validation/ValidationPage'
import WorkflowPage from './pages/Workflow/WorkflowPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/raw-messages" element={<RawMessagesPage />} />
        <Route path="/extraction" element={<ExtractionPage />} />
        <Route path="/validation" element={<ValidationPage />} />
        <Route path="/workflow" element={<WorkflowPage />} />
      </Route>
    </Routes>
  )
}
