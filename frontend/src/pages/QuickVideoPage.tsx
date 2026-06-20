import { useState, useEffect, useRef } from 'react'
import { Card, Input, Button, Select, message, Progress, Typography, Space, Row, Col } from 'antd'
import { ThunderboltOutlined, PlayCircleOutlined, DownloadOutlined } from '@ant-design/icons'
import axios from 'axios'

const { TextArea } = Input
const { Title, Text } = Typography

const TEMPLATES: Record<string, string> = {
  'product-showcase': '全屏产品图轮播',
  'talking-head': '全屏人物口播',
  'split-screen': '上半人物 + 下半产品',
  'pip': '画中画（产品全屏+右下角人物）',
}

const STYLES = ['', '现代简约', '轻奢', '新中式', '北欧', '意式', '日式']

export default function QuickVideoPage() {
  const [script, setScript] = useState('')
  const [template, setTemplate] = useState('product-showcase')
  const [bgm, setBgm] = useState('emotional-piano')
  const [style, setStyle] = useState('')
  const [bgms, setBgms] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [taskId, setTaskId] = useState<number | null>(null)
  const [progress, setProgress] = useState(0)
  const [projectId, setProjectId] = useState<number | null>(null)
  const [videoUrl, setVideoUrl] = useState('')
  const pollRef = useRef<any>(null)

  useEffect(() => {
    axios.get('/api/video/bgms').then(r => setBgms(r.data)).catch(() => {})
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleGenerate = async () => {
    if (!script.trim()) {
      message.warning('请先输入脚本')
      return
    }
    setLoading(true)
    setProgress(0)
    setVideoUrl('')
    try {
      const res = await axios.post('/api/video/hyperframes-generate', {
        script: script.trim(),
        template,
        bgm,
        style,
      })
      const tid = res.data.task_id
      const pid = res.data.project_id
      setTaskId(tid)
      setProjectId(pid)
      setProgress(5)

      pollRef.current = setInterval(async () => {
        try {
          const r = await axios.get(`/api/tasks/${tid}`)
          const task = r.data
          setProgress(task.progress || 50)
          if (task.status === 'completed') {
            setProgress(100)
            setVideoUrl(`/api/video/projects/${pid}/output`)
            clearInterval(pollRef.current)
            setLoading(false)
            message.success('出片完成！')
          } else if (task.status === 'failed') {
            clearInterval(pollRef.current)
            setLoading(false)
            message.error(task.progress_message || '出片失败')
          }
        } catch { }
      }, 3000)
    } catch (e: any) {
      message.error(e.response?.data?.message || '提交失败')
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Title level={4}>
        <ThunderboltOutlined style={{ color: '#e94560', marginRight: 8 }} />
        快速出片
      </Title>
      <Text type="secondary">输入脚本 → 选模板/配乐 → 一键生成带字幕的竖屏视频</Text>

      <Card style={{ marginTop: 16, borderRadius: 12 }}>
        <Text strong>脚本文案</Text>
        <TextArea
          rows={5}
          placeholder="在此输入你的口播文案..."
          value={script}
          onChange={e => setScript(e.target.value)}
          style={{ marginTop: 8 }}
        />

        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={8}>
            <Text style={{ fontSize: 13 }}>视频模板</Text>
            <Select value={template} onChange={setTemplate} style={{ width: '100%', marginTop: 4 }}>
              {Object.entries(TEMPLATES).map(([k, v]) => (
                <Select.Option key={k} value={k}>{v}</Select.Option>
              ))}
            </Select>
          </Col>
          <Col span={8}>
            <Text style={{ fontSize: 13 }}>背景音乐</Text>
            <Select value={bgm} onChange={setBgm} style={{ width: '100%', marginTop: 4 }}>
              {Object.entries(bgms).map(([k, v]: any) => (
                <Select.Option key={k} value={k}>{k} — {v.mood}</Select.Option>
              ))}
            </Select>
          </Col>
          <Col span={8}>
            <Text style={{ fontSize: 13 }}>产品图风格</Text>
            <Select value={style} onChange={setStyle} style={{ width: '100%', marginTop: 4 }}>
              <Select.Option value="">自动匹配</Select.Option>
              {STYLES.filter(Boolean).map(s => (
                <Select.Option key={s} value={s}>{s}</Select.Option>
              ))}
            </Select>
          </Col>
        </Row>

        <Button
          type="primary"
          size="large"
          icon={<ThunderboltOutlined />}
          onClick={handleGenerate}
          loading={loading}
          style={{ marginTop: 16, borderRadius: 10, width: '100%', height: 48 }}
        >
          {loading ? '生成中...' : '一键出片'}
        </Button>
      </Card>

      {loading && (
        <Card style={{ marginTop: 16, borderRadius: 12 }}>
          <Progress percent={progress} status="active" />
          <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginTop: 8 }}>
            正在渲染视频，约需2-5分钟...
          </Text>
        </Card>
      )}

      {videoUrl && (
        <Card style={{ marginTop: 16, borderRadius: 12 }}>
          <video
            src={videoUrl}
            controls
            style={{ width: '100%', borderRadius: 8 }}
          />
          <Space style={{ marginTop: 12, width: '100%', justifyContent: 'center' }}>
            <Button icon={<PlayCircleOutlined />} type="primary" onClick={() => window.open(videoUrl, '_blank')}>
              播放
            </Button>
            <Button icon={<DownloadOutlined />} onClick={() => window.open(videoUrl + '?download=1', '_blank')}>
              下载
            </Button>
          </Space>
        </Card>
      )}
    </div>
  )
}
