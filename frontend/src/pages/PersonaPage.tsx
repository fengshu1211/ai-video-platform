import { useState, useEffect } from 'react'
import { Card, Form, Input, Select, Button, message, Typography, Spin, Tag, Descriptions } from 'antd'
import { UserOutlined, BulbOutlined, ThunderboltOutlined } from '@ant-design/icons'

const { Title, Paragraph, Text } = Typography

interface Props { userId: number }

export default function PersonaPage({ userId }: Props) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [persona, setPersona] = useState<any>(null)
  const [styleTemplate, setStyleTemplate] = useState<any>(null)

  useEffect(() => {
    fetch(`/api/auth/persona?user_id=${userId}`)
      .then(r => r.json())
      .then(d => {
        if (d.persona) {
          setPersona(d.persona)
          form.setFieldsValue(d.persona)
          if (d.persona.style_template && Object.keys(d.persona.style_template).length > 0) {
            setStyleTemplate(d.persona.style_template)
          }
        }
      }).catch(() => {})
  }, [userId])

  const handleSave = async (values: any) => {
    setAnalyzing(true)
    try {
      const res = await fetch(`/api/auth/persona?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      })
      const data = await res.json()
      if (res.ok) {
        message.success('人设分析完成')
        setPersona(values)
        setStyleTemplate(data.persona?.style_template || null)
      } else {
        message.error(data.detail || '保存失败')
      }
    } catch {
      message.error('网络错误')
    }
    setAnalyzing(false)
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <Title level={4} style={{ color: '#e2e8f0' }}>
        <UserOutlined style={{ marginRight: 8, color: '#3b82f6' }} />我的创作人设
      </Title>
      <Paragraph style={{ color: '#94a3b8', fontSize: 13, marginBottom: 24 }}>
        填写你的行业、性格等特征，AI会分析并生成你的专属文案风格模板。之后改写文案时会自动参考。
      </Paragraph>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card size="small" title="基本信息" style={{ borderRadius: 12 }}>
          <Form form={form} layout="vertical" onFinish={handleSave} size="large">
            <Form.Item name="industry" label="行业"><Input placeholder="如：历史科普、家居装修、美食探店" /></Form.Item>
            <Form.Item name="role" label="角色/职位"><Input placeholder="如：历史博主、设计师、厨师" /></Form.Item>
            <Form.Item name="personality" label="性格特征"><Input placeholder="如：幽默风趣、严肃认真、亲和力强" /></Form.Item>
            <Form.Item name="hobbies" label="兴趣爱好"><Input placeholder="如：读书、旅行、摄影" /></Form.Item>
            <Form.Item name="content_style" label="内容风格偏好">
              <Select placeholder="选择偏好风格" options={[
                { label: '幽默口语化', value: '幽默口语化' }, { label: '沉稳专业风', value: '沉稳专业风' },
                { label: '激情澎湃风', value: '激情澎湃风' }, { label: '娓娓道来', value: '娓娓道来' },
                { label: '快节奏干货', value: '快节奏干货' }, { label: '故事叙事风', value: '故事叙事风' },
              ]} />
            </Form.Item>
            <Form.Item name="target_audience" label="目标受众"><Input placeholder="如：25-40岁男性、装修业主、美食爱好者" /></Form.Item>
            <Button type="primary" htmlType="submit" loading={analyzing} icon={<ThunderboltOutlined />} block style={{ borderRadius: 10 }}>
              {analyzing ? 'AI分析中...' : '保存并AI分析'}
            </Button>
          </Form>
        </Card>

        <Card size="small" title={<span><BulbOutlined style={{ color: '#f59e0b' }} /> AI风格分析结果</span>} style={{ borderRadius: 12 }}>
          {analyzing ? (
            <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /><div style={{ color: '#94a3b8', marginTop: 12 }}>AI正在分析你的人设...</div></div>
          ) : styleTemplate && Object.keys(styleTemplate).length > 0 ? (
            <div style={{ fontSize: 13 }}>
              <div style={{ marginBottom: 12 }}><Tag color="blue">{styleTemplate.style_name}</Tag></div>
              <Descriptions column={1} size="small" colon={false} labelStyle={{ color: '#94a3b8' }} contentStyle={{ color: '#e2e8f0' }}>
                <Descriptions.Item label="语气">{styleTemplate.tone}</Descriptions.Item>
                <Descriptions.Item label="句长">{styleTemplate.sentence_length}</Descriptions.Item>
                <Descriptions.Item label="视频时长">{styleTemplate.ideal_video_duration}</Descriptions.Item>
              </Descriptions>
              <div style={{ marginTop: 8, color: '#94a3b8' }}>💡 创作建议</div>
              <div style={{ padding: '8px 0', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{styleTemplate.writing_tips}</div>
              {styleTemplate.keywords && (
                <div style={{ marginTop: 8 }}>{styleTemplate.keywords.map((k: string) => <Tag key={k} style={{ marginBottom: 4 }}>{k}</Tag>)}</div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#64748b' }}>填写左侧信息后<br />点击"保存并AI分析"<br />查看你的专属风格模板</div>
          )}
        </Card>
      </div>
    </div>
  )
}
