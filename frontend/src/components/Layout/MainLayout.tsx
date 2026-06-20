import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button } from 'antd'
import {
  DashboardOutlined,
  FireOutlined,
  EditOutlined,
  SoundOutlined,
  VideoCameraOutlined,
  FolderOpenOutlined,
  HeartOutlined,
  SettingOutlined,
  LogoutOutlined,
  IdcardOutlined,
  QuestionCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'

const { Sider, Content, Header } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/quick-video', icon: <ThunderboltOutlined />, label: '快速出片' },
  { key: '/template', icon: <ThunderboltOutlined />, label: '文案模板' },
  { key: '/video', icon: <VideoCameraOutlined />, label: '视频制作' },
  { key: '/voice', icon: <SoundOutlined />, label: '语音选择' },
  { key: '/library', icon: <HeartOutlined />, label: '成品视频库' },
]

export default function MainLayout({ user, onLogout }: { user?: any; onLogout?: () => void }) {
  const [collapsed, setCollapsed] = useState(window.innerWidth < 768)
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Layout style={{ minHeight: '100vh', background: '#0f172a' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        collapsedWidth={window.innerWidth < 768 ? 0 : 80}
        width={200}
        style={{
          background: 'rgba(30,41,59,0.85)',
          backdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(148,163,184,0.08)',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#e2e8f0',
            fontSize: collapsed ? 14 : 18,
            fontWeight: 700,
            letterSpacing: 2,
            borderBottom: '1px solid rgba(148,163,184,0.08)',
          }}
        >
          {collapsed ? '圣栎' : '圣栎美家'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent', borderInlineEnd: 'none' }}
        />
        <div style={{ padding: '10px 12px', borderTop: '1px solid rgba(148,163,184,0.08)' }}>
{}
          <Button type="text" size="small" icon={<SettingOutlined />}
            onClick={() => navigate('/settings')}
            style={{ color: '#64748b', fontSize: 12, width: '100%', justifyContent: 'flex-start' }}>
            {collapsed ? '' : '系统设置'}
          </Button>
          {onLogout && (
            <Button type="text" size="small" icon={<LogoutOutlined />}
              onClick={onLogout}
              style={{ color: '#64748b', fontSize: 12, width: '100%', justifyContent: 'flex-start' }}>
              {collapsed ? '' : '退出登录'}
            </Button>
          )}
        </div>
      </Sider>
      <Layout style={{ background: 'transparent' }}>
        <Header
          style={{
            background: 'rgba(30,41,59,0.6)',
            backdropFilter: 'blur(12px)',
            padding: '0 24px',
            fontSize: 15,
            fontWeight: 500,
            color: '#e2e8f0',
            borderBottom: '1px solid rgba(148,163,184,0.08)',
            height: 56,
            lineHeight: '56px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{menuItems.find(m => m.key === location.pathname)?.label || '工作台'}</span>
          <Button type="link" icon={<QuestionCircleOutlined />} href="/manual.html" target="_blank"
            style={{ color: '#60a5fa', fontSize: 13 }}>
            使用说明
          </Button>
        </Header>
        <Content style={{ margin: 20 }}>
          <div
            style={{
              padding: 24,
              minHeight: 360,
              background: 'rgba(30,41,59,0.5)',
              backdropFilter: 'blur(10px)',
              borderRadius: 16,
              border: '1px solid rgba(148,163,184,0.06)',
            }}
          >
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
