import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import DashboardPage  from '@/pages/DashboardPage'
import DocumentsPage  from '@/pages/DocumentsPage'
import InvestigatePage from '@/pages/InvestigatePage'
import ConflictsPage  from '@/pages/ConflictsPage'
import EvidencePage   from '@/pages/EvidencePage'
import SettingsPage   from '@/pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"   element={<DashboardPage />} />
          <Route path="documents"   element={<DocumentsPage />} />
          <Route path="investigate" element={<InvestigatePage />} />
          <Route path="conflicts"   element={<ConflictsPage />} />
          <Route path="evidence"    element={<EvidencePage />} />
          <Route path="settings"    element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
