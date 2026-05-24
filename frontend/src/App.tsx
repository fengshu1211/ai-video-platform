import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider, App as AntApp, theme, Spin } from 'antd'
import zhCN from 'antd/es/locale/zh_CN'
import MainLayout from './components/Layout/MainLayout'
import Dashboard from './pages/Dashboard'
import TopicPage from './pages/TopicPage'
import ContentPage from './pages/ContentPage'
import VoicePage from './pages/VoicePage'
import VideoPage from './pages/VideoPage'
import MaterialLibraryPage from './pages/MaterialLibraryPage'
import VideoLibraryPage from './pages/VideoLibraryPage'
import SettingsPage from './pages/SettingsPage'
import PersonaPage from './pages/PersonaPage'
import SetupWizard from './components/SetupWizard'
import LoginPage from './pages/LoginPage'

function AppContent() {
  const [showWizard, setShowWizard] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const saved = localStorage.getItem('current_user')
    if (saved) {
      try { setUser(JSON.parse(saved)) } catch {}
    }
    setChecking(false)
  }, [])

  useEffect(() => {
    if (!user) return
    const keys = localStorage.getItem('user_api_keys')
    const seen = localStorage.getItem('setup_wizard_seen')
    if (!keys && !seen) setShowWizard(true)
  }, [user])

  const handleLogin = (userId: number, name: string) => {
    const u = { userId, displayName: name }
    setUser(u)
    localStorage.setItem('current_user', JSON.stringify(u))
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('current_user')
  }

  if (checking) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a' }}><Spin size="large" /></div>
  if (!user) return <LoginPage onLogin={handleLogin} />

  return (
    <>
      <SetupWizard open={showWizard} onDone={() => { setShowWizard(false); localStorage.setItem('setup_wizard_seen', '1') }} />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout user={user} onLogout={handleLogout} />}>
            <Route index element={<Dashboard />} />
            <Route path="topics" element={<TopicPage />} />
            <Route path="content" element={<ContentPage />} />
            <Route path="voice" element={<VoicePage />} />
            <Route path="video" element={<VideoPage />} />
            <Route path="materials" element={<MaterialLibraryPage />} />
            <Route path="library" element={<VideoLibraryPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="persona" element={<PersonaPage userId={user.userId} />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </>
  )
}

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#3b82f6',
          colorInfo: '#3b82f6',
          colorSuccess: '#10b981',
          colorWarning: '#f59e0b',
          colorError: '#ef4444',
          borderRadius: 10,
          borderRadiusLG: 14,
          wireframe: false,
          colorBgBase: '#0f172a',
          colorBgContainer: '#1e293b',
          colorBgElevated: '#1e293b',
          colorBgLayout: '#0f172a',
          colorTextBase: '#e2e8f0',
          colorText: '#e2e8f0',
          colorTextSecondary: '#94a3b8',
          colorBorder: 'rgba(148,163,184,0.1)',
          colorBorderSecondary: 'rgba(148,163,184,0.06)',
          controlItemBgHover: 'rgba(59,130,246,0.1)',
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif",
        },
      }}
    >
      <AntApp>
        <AppContent />
      </AntApp>
    </ConfigProvider>
  )
}

export default App
