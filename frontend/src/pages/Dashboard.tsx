import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Button, Tag, Spin, Steps } from 'antd'
import {
  ThunderboltOutlined, VideoCameraOutlined, EditOutlined,
  UploadOutlined, PlayCircleOutlined,
} from '@ant-design/icons'
import { videoApi, contentApi, voiceApi } from '../services/api'
import type { VideoProject } from '../types/video'

export default function Dashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [projects, setProjects] = useState<VideoProject[]>([])

  useEffect(() => {
    Promise.all([
      videoApi.list().then(setProjects).catch(() => {}),
    ]).finally(() => setLoading(false))
    const t = setInterval(() => videoApi.list().then(setProjects).catch(() => {}), 8000)
    return () => clearInterval(t)
  }, [])

  const completed = projects.filter(p => p.status === 'completed').length
  const processing = projects.filter(p => p.status === 'processing').length

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* 品牌头 */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: '#e2e8f0', marginBottom: 4 }}>
          圣栎美家 · 短视频助手
        </h1>
        <p style={{ color: '#94a3b8', fontSize: 14, margin: 0 }}>
          江山欧派旗下 | 花木匠健康板材四川+山东总代理
        </p>
      </div>

      {/* 快速开始 */}
      <Card style={{ borderRadius: 16, marginBottom: 24, borderColor: 'rgba(59,130,246,0.2)', background: 'rgba(30,41,59,0.6)' }}>
        <Steps
          direction="horizontal"
          size="small"
          current={-1}
          responsive
          items={[
            { title: '选模板', description: '6套行业模板' },
            { title: '填信息', description: '产品/工艺/价格' },
            { title: '传素材', description: '照片或视频' },
            { title: '生成视频', description: '自动配音+字幕' },
          ]}
          style={{ marginBottom: 24 }}
        />
        <div style={{ textAlign: 'center' }}>
          <Button type="primary" size="large" icon={<ThunderboltOutlined />}
            onClick={() => navigate('/template')}
            style={{ borderRadius: 10, height: 48, paddingInline: 40, fontSize: 16 }}>
            开始制作视频
          </Button>
        </div>
      </Card>

      {/* 快捷入口 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" onClick={() => navigate('/template')}
            style={{ textAlign: 'center', borderRadius: 12, borderColor: 'rgba(148,163,184,0.1)' }}>
            <EditOutlined style={{ fontSize: 24, color: '#3b82f6', marginBottom: 8 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>文案模板</div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>填空生成口播</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" onClick={() => navigate('/video')}
            style={{ textAlign: 'center', borderRadius: 12, borderColor: 'rgba(148,163,184,0.1)' }}>
            <VideoCameraOutlined style={{ fontSize: 24, color: '#8b5cf6', marginBottom: 8 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>视频制作</div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>上传素材+生成</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" onClick={() => navigate('/voice')}
            style={{ textAlign: 'center', borderRadius: 12, borderColor: 'rgba(148,163,184,0.1)' }}>
            <PlayCircleOutlined style={{ fontSize: 24, color: '#10b981', marginBottom: 8 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>语音选择</div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>选配音风格</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" onClick={() => navigate('/video')}
            style={{ textAlign: 'center', borderRadius: 12, borderColor: 'rgba(148,163,184,0.1)' }}>
            <UploadOutlined style={{ fontSize: 24, color: '#f59e0b', marginBottom: 8 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>上传素材</div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>手机照片视频</div>
          </Card>
        </Col>
      </Row>

      {/* 最近项目 */}
      <div style={{ fontSize: 16, fontWeight: 600, color: '#e2e8f0', marginBottom: 12 }}>
        最近视频 {processing > 0 && <Tag color="processing">{processing} 生成中</Tag>}
        {completed > 0 && <Tag color="success">{completed} 已完成</Tag>}
      </div>
      {projects.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 48, borderRadius: 14, borderColor: 'rgba(148,163,184,0.08)' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🎬</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#e2e8f0' }}>还没有视频</div>
          <div style={{ color: '#94a3b8', marginBottom: 20 }}>选模板填信息，几分钟出第一条</div>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => navigate('/template')}>开始制作</Button>
        </Card>
      ) : (
        <Row gutter={[12, 12]}>
          {projects.slice(0, 6).map(p => (
            <Col xs={12} sm={8} key={p.id}>
              <Card hoverable size="small" onClick={() => navigate('/video')}
                style={{ borderRadius: 12, borderColor: 'rgba(148,163,184,0.08)' }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: '#e2e8f0', marginBottom: 4 }}>{p.title}</div>
                <Tag color={p.status === 'completed' ? 'success' : p.status === 'processing' ? 'processing' : 'default'}>
                  {p.status === 'completed' ? '已完成' : p.status === 'processing' ? '生成中' : '草稿'}
                </Tag>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}
