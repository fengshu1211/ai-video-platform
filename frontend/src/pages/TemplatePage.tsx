import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Input, Button, message, Row, Col, Typography, Form, Tag } from 'antd'
import { ThunderboltOutlined, VideoCameraOutlined, GoldOutlined, BulbOutlined, WarningOutlined, StarOutlined, CameraOutlined, SafetyOutlined } from '@ant-design/icons'
import { templateApi } from '../services/api'

const { Title, Paragraph } = Typography

const ICON_MAP: Record<string, any> = {
  gold: <GoldOutlined />,
  bulb: <BulbOutlined />,
  warning: <WarningOutlined />,
  star: <StarOutlined />,
  camera: <CameraOutlined />,
  shield: <SafetyOutlined />,
}

export default function TemplatePage() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    templateApi.list().then((r: any) => setTemplates(r.data || [])).catch(() => message.error('加载模板失败'))
  }, [])

  const handleGenerate = async () => {
    try {
      const fields = await form.validateFields()
      setGenerating(true)
      const r: any = await templateApi.generate({ template_id: selected.id, fields })
      if (r.code === 0) {
        setResult(r.data)
        message.success('文案生成成功')
      } else {
        message.error(r.message || '生成失败')
      }
    } catch (e: any) {
      if (e?.errorFields) message.warning('请完善所有字段')
      else message.error('生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleReset = () => {
    setSelected(null)
    setResult(null)
    form.resetFields()
  }

  // 模板选择
  if (!selected) {
    return (
      <div>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 8, color: '#e2e8f0' }}>
          选择文案模板
        </Title>
        <Paragraph style={{ textAlign: 'center', color: '#94a3b8', marginBottom: 24 }}>
          选一个模板，填几个空，AI 自动帮你写好口播文案
        </Paragraph>
        <Row gutter={[16, 16]}>
          {templates.map((t: any) => (
            <Col xs={24} sm={12} md={8} key={t.id}>
              <Card
                hoverable
                onClick={() => setSelected(t)}
                style={{ borderRadius: 12, height: '100%', borderColor: 'rgba(148,163,184,0.12)' }}
              >
                <div style={{ fontSize: 32, marginBottom: 8, color: '#3b82f6' }}>
                  {ICON_MAP[t.icon] || <ThunderboltOutlined />}
                </div>
                <Title level={5} style={{ marginBottom: 4, color: '#e2e8f0' }}>{t.name}</Title>
                <Paragraph style={{ color: '#94a3b8', marginBottom: 0, fontSize: 13 }}>{t.desc}</Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </div>
    )
  }

  // 填空表单
  if (!result) {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto' }}>
        <Card
          title={<span>{ICON_MAP[selected.icon]} {selected.name} — 填写信息</span>}
          extra={<Button onClick={handleReset}>返回</Button>}
          style={{ borderRadius: 12 }}
        >
          <Form form={form} layout="vertical">
            {selected.fields.map((f: any) => (
              <Form.Item
                key={f.key}
                name={f.key}
                label={f.label}
                rules={[{ required: true, message: '请填写' + f.label }]}
              >
                <Input placeholder={f.placeholder} size="large" />
              </Form.Item>
            ))}
          </Form>
          <Button type="primary" size="large" block loading={generating}
            icon={<ThunderboltOutlined />} onClick={handleGenerate}
            style={{ borderRadius: 10, marginTop: 8 }}>
            AI 生成文案
          </Button>
        </Card>
      </div>
    )
  }

  // 结果展示
  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <Card
        title={<span><Tag color="blue">{selected.name}</Tag> 生成结果</span>}
        extra={<Button onClick={handleReset}>重新选择</Button>}
        style={{ borderRadius: 12, marginBottom: 16 }}
      >
        <div style={{
          background: 'rgba(15,23,42,0.5)', padding: 20, borderRadius: 8,
          whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 15, color: '#e2e8f0',
          minHeight: 120, marginBottom: 16
        }}>
          {result.text}
        </div>
        <Button type="primary" size="large" block icon={<VideoCameraOutlined />}
          onClick={() => navigate('/video', { state: { scriptId: result.script_id } })}
          style={{ borderRadius: 10 }}>
          用这条文案生成视频
        </Button>
      </Card>
    </div>
  )
}
