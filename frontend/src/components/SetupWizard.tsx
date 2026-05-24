import { useState } from 'react'
import { Modal, Button, Input, Steps, Typography, Space, message } from 'antd'
import { LinkOutlined, KeyOutlined, CheckCircleOutlined, RocketOutlined } from '@ant-design/icons'

const { Text, Paragraph } = Typography

const STEPS = [
  {
    title: '通义千问',
    desc: 'AI改写文案、智能导演分镜',
    key: 'dashscope_key',
    url: 'https://dashscope.console.aliyun.com/apiKey',
    help: '打开阿里云DashScope → 创建API Key → 复制粘贴到下方',
  },
  {
    title: '硅基流动',
    desc: 'AI语音复刻（CosyVoice）',
    key: 'siliconflow_key',
    url: 'https://cloud.siliconflow.cn/account/ak',
    help: '打开硅基流动 → 登录 → API密钥 → 新建 → 复制粘贴到下方',
  },
]

interface Props {
  open: boolean
  onDone: () => void
}

export default function SetupWizard({ open, onDone }: Props) {
  const [step, setStep] = useState(0)
  const [keys, setKeys] = useState<Record<string, string>>({})

  const saveAndNext = () => {
    const currentKey = STEPS[step].key
    if (!keys[currentKey]?.trim()) {
      message.warning('请粘贴API Key，或点跳过')
    }
    // 保存当前配置
    const existing = JSON.parse(localStorage.getItem('user_api_keys') || '{}')
    localStorage.setItem('user_api_keys', JSON.stringify({ ...existing, ...keys }))

    if (step < STEPS.length - 1) {
      setStep(step + 1)
    } else {
      message.success('设置完成！')
      onDone()
    }
  }

  const skip = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1)
    } else {
      onDone()
    }
  }

  const current = STEPS[step]

  return (
    <Modal
      title={<Space><RocketOutlined style={{ color: '#3b82f6' }} />快速设置（30秒）</Space>}
      open={open}
      closable={false}
      maskClosable={false}
      footer={[
        <Button key="skip" type="link" onClick={skip} style={{ color: '#94a3b8' }}>
          {step < STEPS.length - 1 ? '跳过' : '以后再说'}
        </Button>,
        <Button key="next" type="primary" icon={step < STEPS.length - 1 ? <KeyOutlined /> : <CheckCircleOutlined />}
          onClick={saveAndNext}>
          {step < STEPS.length - 1 ? '保存并继续' : '完成'}
        </Button>,
      ]}
      width={440}
    >
      <Steps current={step} size="small" style={{ marginBottom: 24 }}
        items={STEPS.map(s => ({ title: s.title }))} />

      <Paragraph style={{ color: '#94a3b8', fontSize: 13, marginBottom: 8 }}>
        {current.desc}
      </Paragraph>

      <Button type="link" icon={<LinkOutlined />} onClick={() => window.open(current.url, '_blank')}
        style={{ padding: 0, marginBottom: 12, fontSize: 13 }}>
        点此打开注册页获取Key（新用户免费）
      </Button>

      <Input.Password
        placeholder="粘贴API Key到这里"
        value={keys[current.key] || ''}
        onChange={e => setKeys({ ...keys, [current.key]: e.target.value })}
        style={{ borderRadius: 8 }}
        size="large"
      />

      <Text style={{ color: '#64748b', fontSize: 12, display: 'block', marginTop: 8 }}>
        {current.help}
      </Text>
    </Modal>
  )
}
