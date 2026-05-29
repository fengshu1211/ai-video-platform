import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Card, Input, Button, message, Row, Col, Typography, Form, Tag, Tabs, Select } from 'antd'
import { ThunderboltOutlined, VideoCameraOutlined, GoldOutlined, BulbOutlined, WarningOutlined, StarOutlined, CameraOutlined, SafetyOutlined, ShopOutlined, BuildOutlined } from '@ant-design/icons'
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

const BRANDS = [
  { key: '圣栎美家', label: '圣栎美家·全屋定制', icon: <ShopOutlined />, desc: '全屋定制柜类/木门/墙板，面向经销商招商' },
  { key: '纬臻木业', label: '纬臻木业·板材销售', icon: <BuildOutlined />, desc: '花木匠健康板材，ENF认证，面向全国定制工厂' },
]

export default function TemplatePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const topicText = (location.state as any)?.topicText || ''
  const [templates, setTemplates] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    templateApi.list().then((r: any) => setTemplates(r.data || [])).catch(() => message.error('加载模板失败'))
  }, [])

  // 从选题页过来的，预填第一个字段
  useEffect(() => {
    if (selected && topicText && selected.fields?.length > 0) {
      form.setFieldValue(selected.fields[0].key, topicText)
    }
  }, [selected?.id])

  const handleGenerate = async () => {
    try {
      const fields = await form.validateFields()
      setGenerating(true)
      const style = form.getFieldValue('style') || '随机'
      const r: any = await templateApi.generate({ template_id: selected.id, fields, style })
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
        {topicText && (
          <Card size="small" style={{ marginBottom: 16, borderRadius: 10, background: 'rgba(245,158,11,0.08)', borderColor: 'rgba(245,158,11,0.2)' }}>
            <span style={{ color: '#fbbf24', fontSize: 13 }}>选题：{topicText}</span>
          </Card>
        )}
        <Tabs
          defaultActiveKey="圣栎美家"
          centered
          items={BRANDS.map(b => ({
            key: b.key,
            label: <span>{b.icon} {b.label}</span>,
            children: (
              <div>
                <Paragraph style={{ color: '#94a3b8', fontSize: 13, marginBottom: 16 }}>{b.desc}</Paragraph>
                <Row gutter={[16, 16]}>
                  {templates.filter((t: any) => t.brand === b.key).map((t: any) => (
                    <Col xs={24} sm={12} md={8} key={t.id}>
                      <Card hoverable onClick={() => setSelected(t)}
                        style={{ borderRadius: 12, height: '100%', borderColor: 'rgba(148,163,184,0.12)' }}>
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
            ),
          }))}
        />
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
            <Form.Item name="style" label="文案风格" initialValue="随机">
              <Select defaultValue="随机" options={[
                { label: '随机风格', value: '随机' },
                { label: '活泼热情', value: '活泼' },
                { label: '专业严谨', value: '专业' },
                { label: '幽默轻松', value: '幽默' },
              ]} />
            </Form.Item>
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
