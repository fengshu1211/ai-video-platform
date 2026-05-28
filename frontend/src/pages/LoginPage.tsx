import { useState } from 'react'
import { Card, Form, Input, Button, Tabs, message, Typography } from 'antd'
import { PhoneOutlined, LockOutlined, UserOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

interface Props { onLogin: (userId: number, name: string) => void }

export default function LoginPage({ onLogin }: Props) {
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState('login')

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      const res = await fetch('/api/auth/' + (tab === 'register' ? 'register' : 'login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      })
      const data = await res.json()
      if (res.ok && data.code === 0) {
        message.success(tab === 'register' ? '注册成功' : '登录成功')
        onLogin(data.user_id, data.display_name || '')
      } else {
        message.error(data.detail || data.message || '操作失败')
      }
    } catch {
      message.error('网络错误')
    }
    setLoading(false)
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a' }}>
      <Card style={{ width: 380, borderRadius: 16, border: '1px solid rgba(148,163,184,0.1)' }}>
        <Title level={3} style={{ textAlign: 'center', color: '#e2e8f0', marginBottom: 4 }}>圣栎美家</Title>
        <Text style={{ display: 'block', textAlign: 'center', color: '#94a3b8', marginBottom: 24, fontSize: 13 }}>
          全屋定制短视频助手
        </Text>
        <Tabs activeKey={tab} onChange={setTab} centered items={[
          { key: 'login', label: '登录' },
          { key: 'register', label: '注册' },
        ]} />
        <Form onFinish={handleSubmit} size="large">
          <Form.Item name="phone" rules={[{ required: true, message: '请输入手机号' }, { pattern: /^1\d{10}$/, message: '请输入正确的11位手机号' }]}>
            <Input prefix={<PhoneOutlined />} placeholder="手机号" maxLength={11} style={{ borderRadius: 8 }} />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }, { min: 4, message: '至少4位' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" style={{ borderRadius: 8 }} />
          </Form.Item>
          {tab === 'register' && (
            <Form.Item name="display_name">
              <Input prefix={<UserOutlined />} placeholder="昵称（选填）" style={{ borderRadius: 8 }} />
            </Form.Item>
          )}
          <Button type="primary" htmlType="submit" loading={loading} block style={{ borderRadius: 10, height: 44 }}>
            {tab === 'register' ? '注册' : '登录'}
          </Button>
        </Form>
      </Card>
    </div>
  )
}
