import { useState, useEffect } from 'react'
import { Card, Button, Steps, Typography, Spin, Tag, message, Row, Col } from 'antd'
import { useNavigate } from 'react-router-dom'
import { ThunderboltOutlined, CheckCircleOutlined, PlayCircleOutlined } from '@ant-design/icons'

const { Title, Paragraph, Text } = Typography

interface Template {
  id: string; name: string; icon: string; persona: any; script_count: number
}
interface TemplateDetail {
  id: string; name: string; icon: string; persona: any; scripts: { title: string; text: string; duration: string }[]
}

export default function QuickStart() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [templates, setTemplates] = useState<Template[]>([])
  const [selected, setSelected] = useState<TemplateDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)

  useEffect(() => {
    fetch('/api/templates/personas')
      .then(r => r.json()).then(d => { setTemplates(d.templates || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const selectTemplate = async (id: string) => {
    const res = await fetch(`/api/templates/personas/${id}`)
    const d = await res.json()
    setSelected(d.template)
    setStep(1)
  }

  const applyTemplate = async () => {
    if (!selected) return
    setApplying(true)
    // 获取当前用户ID
    const user = JSON.parse(localStorage.getItem('current_user') || '{}')
    if (!user.userId) { message.error('请先登录'); return }

    // 创建人设
    const personaData = { ...selected.persona, persona_id: 0 }
    const res = await fetch(`/api/auth/persona?user_id=${user.userId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(personaData),
    })
    if (res.ok) {
      message.success(`已应用「${selected.name}」人设模板！`)
      setStep(2)
    } else {
      message.error('应用失败，请重试')
    }
    setApplying(false)
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Title level={4} style={{ color: '#e2e8f0' }}><ThunderboltOutlined style={{ color: '#f59e0b', marginRight: 8 }} />快速上手</Title>
      <Paragraph style={{ color: '#94a3b8', marginBottom: 24 }}>
        30秒选一个模板，自动配好人设和示例文案，即刻开始创作
      </Paragraph>

      <Steps current={step} size="small" style={{ marginBottom: 28 }}
        items={[{ title: '选择行业' }, { title: '预览内容' }, { title: '开始创作' }]} />

      {/* Step 0: 选模板 */}
      {step === 0 && (
        <Row gutter={[16, 16]}>
          {templates.map(t => (
            <Col xs={24} sm={12} key={t.id}>
              <Card
                hoverable
                onClick={() => selectTemplate(t.id)}
                style={{ borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)', background: 'rgba(30,41,59,0.4)', textAlign: 'center', cursor: 'pointer' }}
              >
                <div style={{ fontSize: 48, marginBottom: 12 }}>{t.icon}</div>
                <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{t.name}</div>
                <div style={{ fontSize: 13, color: '#94a3b8' }}>
                  {t.persona.industry} · {t.persona.content_style} · {t.script_count}条示例
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* Step 1: 预览 */}
      {step === 1 && selected && (
        <>
          <Card size="small" title="人设配置" style={{ borderRadius: 14, marginBottom: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
              <div><Text style={{ color: '#94a3b8' }}>行业：</Text>{selected.persona.industry}</div>
              <div><Text style={{ color: '#94a3b8' }}>角色：</Text>{selected.persona.role}</div>
              <div><Text style={{ color: '#94a3b8' }}>性格：</Text>{selected.persona.personality}</div>
              <div><Text style={{ color: '#94a3b8' }}>风格：</Text><Tag>{selected.persona.content_style}</Tag></div>
              <div><Text style={{ color: '#94a3b8' }}>受众：</Text>{selected.persona.target_audience}</div>
            </div>
          </Card>

          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>📝 示例文案</div>
          {selected.scripts.map((s, i) => (
            <Card key={i} size="small" style={{ borderRadius: 14, marginBottom: 12, border: '1px solid rgba(148,163,184,0.08)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Text strong>{s.title}</Text>
                <Tag>{s.duration}</Tag>
              </div>
              <Paragraph ellipsis={{ rows: 2 }} style={{ color: '#94a3b8', fontSize: 13, marginBottom: 0 }}>{s.text}</Paragraph>
            </Card>
          ))}

          <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
            <Button onClick={() => setStep(0)}>返回重选</Button>
            <Button type="primary" icon={<CheckCircleOutlined />} loading={applying} onClick={applyTemplate} style={{ borderRadius: 10 }}>
              应用此模板
            </Button>
          </div>
        </>
      )}

      {/* Step 2: 完成 */}
      {step === 2 && (
        <Card style={{ borderRadius: 14, textAlign: 'center', padding: 40, border: '1px solid rgba(16,185,129,0.2)', background: 'rgba(16,185,129,0.05)' }}>
          <div style={{ fontSize: 56, marginBottom: 16 }}>🎉</div>
          <Title level={4} style={{ color: '#10b981' }}>模板应用成功！</Title>
          <Paragraph style={{ color: '#94a3b8', marginBottom: 24 }}>
            人设已配置好。现在去<b>内容改写</b>选择示例文案，或者去<b>视频生成</b>创建你的第一个视频。
          </Paragraph>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <Button size="large" onClick={() => navigate('/content')}>去写文案</Button>
            <Button size="large" type="primary" icon={<PlayCircleOutlined />} onClick={() => navigate('/video')} style={{ borderRadius: 10 }}>
              去生成视频
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
