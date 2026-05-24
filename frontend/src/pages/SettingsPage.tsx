import { useState, useEffect } from 'react'
import { Card, Input, Button, message, Typography, Divider, Tag, Modal, Space } from 'antd'
import { KeyOutlined, LinkOutlined, CheckCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

const KEYS_CONFIG = [
  {
    key: 'dashscope_key',
    label: '通义千问 API Key',
    desc: 'AI改写文案、导演分镜、标题生成',
    registerUrl: 'https://dashscope.console.aliyun.com/apiKey',
    registerText: '打开阿里云DashScope → 创建API Key → 复制',
    free: '新用户送100万Token',
  },
  {
    key: 'pexels_key',
    label: 'Pexels API Key',
    desc: '搜图素材（免费图库）',
    registerUrl: 'https://www.pexels.com/api/',
    registerText: '打开Pexels → 注册 → 获取API Key → 复制',
    free: '免费，200次/小时',
  },
  {
    key: 'pixabay_key',
    label: 'Pixabay API Key',
    desc: '搜图素材（补充图库）',
    registerUrl: 'https://pixabay.com/api/docs/',
    registerText: '打开Pixabay → 注册 → API文档页找Key → 复制',
    free: '免费，100次/分钟',
  },
  {
    key: 'siliconflow_key',
    label: '硅基流动 API Key',
    desc: 'AI语音复刻（CosyVoice）',
    registerUrl: 'https://cloud.siliconflow.cn/account/ak',
    registerText: '打开硅基流动 → 登录 → API密钥 → 新建 → 复制',
    free: '新用户送额度',
  },
]

export default function SettingsPage() {
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)
  const [helpOpen, setHelpOpen] = useState('')

  useEffect(() => {
    const stored = localStorage.getItem('user_api_keys')
    if (stored) {
      try { setKeys(JSON.parse(stored)) } catch {}
    }
  }, [])

  const save = () => {
    localStorage.setItem('user_api_keys', JSON.stringify(keys))
    setSaved(true)
    message.success('已保存，刷新后生效')
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div style={{ maxWidth: 700 }}>
      <Title level={4} style={{ color: '#e2e8f0', marginBottom: 4 }}>系统设置</Title>
      <Paragraph style={{ color: '#94a3b8', marginBottom: 16, fontSize: 13 }}>
        默认已配好共享Key，<b>开箱即用</b>。遇到额度不足时再填自己的Key，数据只存本地浏览器。
      </Paragraph>

      {KEYS_CONFIG.map(c => (
        <Card
          key={c.key}
          size="small"
          style={{ marginBottom: 12, borderRadius: 12, border: '1px solid rgba(148,163,184,0.08)' }}
          title={
            <Space>
              <KeyOutlined style={{ color: '#3b82f6' }} />
              <span>{c.label}</span>
              <Tag color="green" style={{ fontSize: 10 }}>{c.free}</Tag>
            </Space>
          }
          extra={
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              onClick={() => window.open(c.registerUrl, '_blank')}
            >
              获取Key
            </Button>
          }
        >
          <Input.Password
            placeholder={c.desc + ' — 粘贴到这里'}
            value={keys[c.key] || ''}
            onChange={e => setKeys({ ...keys, [c.key]: e.target.value })}
            style={{ borderRadius: 8 }}
            addonAfter={<Button type="link" size="small" icon={<InfoCircleOutlined />} onClick={() => setHelpOpen(c.key)} style={{ padding: 0 }} />}
          />
        </Card>
      ))}

      <Button
        type="primary"
        size="large"
        icon={saved ? <CheckCircleOutlined /> : <KeyOutlined />}
        onClick={save}
        style={{ borderRadius: 10, marginTop: 8 }}
        block
      >
        {saved ? '已保存' : '保存设置'}
      </Button>

      <Divider style={{ borderColor: 'rgba(148,163,184,0.1)', margin: '20px 0' }} />
      <Text style={{ color: '#64748b', fontSize: 12 }}>
        不填Key也能用：语音（Edge-TTS免费）、搜图（Pexels/Pixabay免费）、AI改写和语音复刻需填Key。
      </Text>

      <Modal title="获取步骤" open={!!helpOpen} onCancel={() => setHelpOpen('')} footer={null} width={500}>
        {KEYS_CONFIG.find(c => c.key === helpOpen) && (
          <>
            <Paragraph>{KEYS_CONFIG.find(c => c.key === helpOpen)!.registerText}</Paragraph>
            <Button type="primary" onClick={() => window.open(KEYS_CONFIG.find(c => c.key === helpOpen)!.registerUrl, '_blank')} icon={<LinkOutlined />}>
              打开注册页
            </Button>
          </>
        )}
      </Modal>
    </div>
  )
}
