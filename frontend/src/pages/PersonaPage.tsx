import { useState, useEffect } from 'react'
import { Card, Form, Input, Select, Button, message, Typography, Spin, Tag, Tabs, Popconfirm, Empty } from 'antd'
import { UserOutlined, BulbOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

interface Persona { id: number; name: string; industry: string; role: string; personality: string; hobbies: string; content_style: string; target_audience: string; style_template: any; keywords: string[] }

interface Props { userId: number }

export default function PersonaPage({ userId }: Props) {
  const [form] = Form.useForm()
  const [personas, setPersonas] = useState<Persona[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [activeId, setActiveId] = useState<number | 'new'>('new')

  const loadPersonas = () => {
    fetch(`/api/auth/persona?user_id=${userId}`)
      .then(r => r.json())
      .then(d => {
        setPersonas(d.personas || [])
        if ((d.personas || []).length > 0 && activeId === 'new') setActiveId(d.personas[0].id)
      }).catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadPersonas() }, [userId])

  const activePersona = personas.find(p => p.id === activeId)

  const handleSave = async (values: any) => {
    setAnalyzing(true)
    const isNew = activeId === 'new'
    try {
      const res = await fetch(`/api/auth/persona?user_id=${userId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, persona_id: isNew ? 0 : activeId }),
      })
      const data = await res.json()
      if (res.ok) {
        message.success(isNew ? '人设创建成功' : '保存成功')
        loadPersonas()
        if (isNew && data.persona_id) setActiveId(data.persona_id)
      } else {
        message.error(data.detail || '保存失败，最多3个人设')
      }
    } catch { message.error('网络错误') }
    setAnalyzing(false)
  }

  const handleDelete = async (id: number) => {
    await fetch(`/api/auth/persona/${id}?user_id=${userId}`, { method: 'DELETE' })
    message.success('已删除')
    loadPersonas()
    setActiveId('new')
  }

  const handleTabChange = (key: string) => {
    if (key === 'new') { setActiveId('new'); form.resetFields() }
    else {
      const p = personas.find(p => p.id === Number(key))
      if (p) { setActiveId(p.id); form.setFieldsValue(p) }
    }
  }

  if (loading) return <Spin size="large" />

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ color: '#e2e8f0', margin: 0 }}><UserOutlined style={{ marginRight: 8, color: '#3b82f6' }} />我的创作人设</Title>
        {personas.length < 3 && activeId !== 'new' && (
          <Button icon={<PlusOutlined />} onClick={() => { setActiveId('new'); form.resetFields() }}>新建人设</Button>
        )}
      </div>

      {personas.length === 0 && activeId === 'new' ? (
        <Card style={{ borderRadius: 14 }}>
          <Empty description="还没有创作人设，请填写下方信息创建第一个" />
        </Card>
      ) : null}

      {personas.length > 0 && (
        <Tabs
          activeKey={String(activeId)}
          onChange={handleTabChange}
          type="card"
          style={{ marginBottom: 16 }}
          items={[
            ...personas.map(p => ({
              key: String(p.id),
              label: (
                <span>
                  {p.name || '未命名'}
                  <Popconfirm title="确定删除？" onConfirm={() => handleDelete(p.id)}>
                    <DeleteOutlined style={{ marginLeft: 8, fontSize: 11, color: '#94a3b8', cursor: 'pointer' }} />
                  </Popconfirm>
                </span>
              ),
            })),
            ...(personas.length < 3 ? [{ key: 'new', label: <PlusOutlined /> }] : []),
          ]}
        />
      )}

      <Card size="small" title={activeId === 'new' ? '新建人设' : `编辑：${activePersona?.name || '未命名'}`} style={{ borderRadius: 14 }}>
        <Form form={form} layout="vertical" onFinish={handleSave} size="large">
          <Form.Item name="name" label="标签名" tooltip="只给自己看，区分主业副业" initialValue="">
            <Input placeholder="如：主业、副业" />
          </Form.Item>
          <Form.Item name="industry" label="行业"><Input placeholder="如：历史科普、家居装修、美食探店" /></Form.Item>
          <Form.Item name="specialization" label="细分领域"><Input placeholder="如：实木地板、汉朝专题、川菜探店" /></Form.Item>
          <Form.Item name="author_name" label="署名名称" tooltip="会出现在生成的文案中"><Input placeholder="如：丰哥、丰述、XX工作室" /></Form.Item>
          <Form.Item name="role" label="角色/职位"><Input placeholder="如：历史博主、设计师、厨师" /></Form.Item>
          <Form.Item name="personality" label="性格特征"><Input placeholder="如：幽默风趣、严肃认真、亲和力强" /></Form.Item>
          <Form.Item name="features" label="核心特色" tooltip="知识博主填擅长领域，商家填产品卖点"><Input.TextArea rows={2} placeholder="知识博主：擅长讲小人物故事、冷知识挖掘&#10;商家：只做实木、30年老店、产地直供" /></Form.Item>
          <Form.Item name="content_style" label="内容风格偏好">
            <Select placeholder="选择偏好风格" options={[
              { label: '幽默口语化', value: '幽默口语化' }, { label: '沉稳专业风', value: '沉稳专业风' },
              { label: '激情澎湃风', value: '激情澎湃风' }, { label: '娓娓道来', value: '娓娓道来' },
              { label: '快节奏干货', value: '快节奏干货' }, { label: '故事叙事风', value: '故事叙事风' },
            ]} />
          </Form.Item>
          <Form.Item name="target_audience" label="目标受众"><Input placeholder="如：25-40岁男性、装修业主、美食爱好者" /></Form.Item>
          <Button type="primary" htmlType="submit" loading={analyzing} icon={<BulbOutlined />} block style={{ borderRadius: 10 }}>
            {analyzing ? 'AI分析中...' : '保存并AI分析'}
          </Button>
        </Form>
      </Card>

      {activePersona?.style_template && Object.keys(activePersona.style_template).length > 0 && (
        <Card size="small" title={<span><BulbOutlined style={{ color: '#f59e0b' }} /> AI风格分析：{activePersona.style_template.style_name}</span>} style={{ borderRadius: 14, marginTop: 16 }}>
          <div style={{ fontSize: 13, lineHeight: 2 }}>
            <Tag color="blue">{activePersona.style_template.tone}</Tag>
            <Tag>{activePersona.style_template.sentence_length}</Tag>
            <Tag color="purple">{activePersona.style_template.ideal_video_duration}</Tag>
            <div style={{ marginTop: 8, color: '#94a3b8' }}>💡 {activePersona.style_template.writing_tips}</div>
            <div style={{ marginTop: 4 }}>{activePersona.keywords?.map((k: string) => <Tag key={k}>{k}</Tag>)}</div>
          </div>
        </Card>
      )}
    </div>
  )
}
