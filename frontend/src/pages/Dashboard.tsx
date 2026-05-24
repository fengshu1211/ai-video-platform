import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Statistic, Progress, Button, Tag, Spin } from 'antd'
import {
  FireOutlined, EditOutlined, SoundOutlined, VideoCameraOutlined,
  PlusOutlined, ThunderboltOutlined, ClockCircleOutlined, CheckCircleOutlined,
  PlayCircleOutlined, FileTextOutlined, ArrowRightOutlined,
} from '@ant-design/icons'
import { videoApi, contentApi, voiceApi, taskApi } from '../services/api'
import type { VideoProject } from '../types/video'

const quickActions = [
  { title: '新建视频项目', desc: '选择文案 + 语音，一键生成口播视频', icon: <VideoCameraOutlined style={{ fontSize: 28 }} />, path: '/video', color: '#8b5cf6' },
  { title: 'AI改写文案', desc: '粘贴原文，AI去重优化生成新文案', icon: <EditOutlined style={{ fontSize: 28 }} />, path: '/content', color: '#3b82f6' },
  { title: '浏览爆款选题', desc: '查看今日热门话题，找创作灵感', icon: <FireOutlined style={{ fontSize: 28 }} />, path: '/topics', color: '#f59e0b' },
  { title: '上传自定义语音', desc: '10秒音频样本，AI复刻你的声音', icon: <SoundOutlined style={{ fontSize: 28 }} />, path: '/voice', color: '#10b981' },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [projects, setProjects] = useState<VideoProject[]>([])
  const [scripts, setScripts] = useState<any[]>([])
  const [voices, setVoices] = useState<any[]>([])

  const loadData = async () => {
    try {
      const [p, s, v] = await Promise.all([
        videoApi.list() as Promise<VideoProject[]>,
        contentApi.scripts() as Promise<any[]>,
        voiceApi.profiles() as Promise<any[]>,
      ])
      setProjects(p || [])
      setScripts(s || [])
      setVoices(v || [])
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { loadData() }, [])
  useEffect(() => {
    const t = setInterval(loadData, 8000)
    return () => clearInterval(t)
  }, [])

  const completed = projects.filter(p => p.status === 'completed').length
  const processing = projects.filter(p => p.status === 'processing').length
  const drafts = projects.filter(p => p.status === 'draft').length

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>

  return (
    <div>
      {/* 问候 + 统计 */}
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>
        {new Date().getHours() < 12 ? '上午好' : new Date().getHours() < 18 ? '下午好' : '晚上好'} 👋
      </h1>
      <p style={{ color: '#64748b', fontSize: 13, marginBottom: 24 }}>
        共 {projects.length} 个项目，{scripts.length} 条文案，{voices.length} 个语音
      </p>

      <Row gutter={[16, 16]} style={{ marginBottom: 28 }}>
        <Col xs={12} sm={6}><Card size="small" style={{ borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)' }}><Statistic title="全部项目" value={projects.length} valueStyle={{ color: '#3b82f6', fontWeight: 700 }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)' }}><Statistic title="已完成" value={completed} valueStyle={{ color: '#10b981', fontWeight: 700 }} prefix={<CheckCircleOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)' }}><Statistic title="处理中" value={processing} valueStyle={{ color: '#f59e0b', fontWeight: 700 }} prefix={<ThunderboltOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)' }}><Statistic title="草稿" value={drafts} valueStyle={{ fontWeight: 700 }} prefix={<FileTextOutlined />} /></Card></Col>
      </Row>

      {/* 快捷操作 */}
      <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>⚡ 快捷操作</div>
      <Row gutter={[12, 12]} style={{ marginBottom: 28 }}>
        {quickActions.map(a => (
          <Col xs={24} sm={12} key={a.title}>
            <Card
              hoverable
              size="small"
              onClick={() => navigate(a.path)}
              style={{ borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)', background: 'rgba(30,41,59,0.4)' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ width: 48, height: 48, borderRadius: 14, background: `${a.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: a.color }}>
                  {a.icon}
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{a.title}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>{a.desc}</div>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 最近项目 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span style={{ fontSize: 16, fontWeight: 600 }}>📼 最近项目</span>
        <Button type="link" size="small" onClick={() => navigate('/video')}>查看全部 <ArrowRightOutlined /></Button>
      </div>
      <Row gutter={[16, 16]}>
        {projects.slice(0, 6).map(p => (
          <Col xs={24} sm={12} md={8} key={p.id}>
            <Card
              hoverable
              size="small"
              onClick={() => navigate('/video')}
              style={{ borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)', background: 'rgba(30,41,59,0.4)' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 8 }}>
                <span style={{ fontSize: 15, fontWeight: 600 }}>{p.title}</span>
                <Tag color={p.status === 'completed' ? 'green' : p.status === 'processing' ? 'gold' : 'default'}>
                  {p.status === 'completed' ? '已完成' : p.status === 'processing' ? '处理中' : '草稿'}
                </Tag>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
                {p.duration_seconds ? `${Math.round(p.duration_seconds)}秒` : '未生成'} · {p.aspect_ratio || '9:16'}
              </div>
              {p.status === 'processing' && <Progress percent={65} size="small" showInfo={false} strokeColor="#3b82f6" trailColor="rgba(59,130,246,0.15)" />}
              {p.status === 'completed' && <div style={{ height: 6, borderRadius: 3, background: 'rgba(16,185,129,0.2)', overflow: 'hidden' }}><div style={{ width: '100%', height: '100%', background: '#10b981', borderRadius: 3 }} /></div>}
              {p.status === 'draft' && <div style={{ height: 6, borderRadius: 3, background: 'rgba(148,163,184,0.1)', overflow: 'hidden' }}><div style={{ width: '20%', height: '100%', background: '#64748b', borderRadius: 3 }} /></div>}
            </Card>
          </Col>
        ))}
      </Row>
      {projects.length === 0 && (
        <Card style={{ textAlign: 'center', padding: 40, borderRadius: 14, border: '1px solid rgba(148,163,184,0.08)' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🎬</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>还没有视频项目</div>
          <div style={{ color: '#94a3b8', marginBottom: 20 }}>点击上方「新建视频项目」开始创作第一个视频</div>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/video')}>去创建</Button>
        </Card>
      )}
    </div>
  )
}
