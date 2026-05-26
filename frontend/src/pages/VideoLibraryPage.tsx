import { useEffect, useState, useMemo } from 'react'
import { Card, Row, Col, Tag, Button, Empty, Spin, message, Popconfirm, Input, Space, Select, Tooltip } from 'antd'
import {
  PlayCircleOutlined, HeartFilled, DeleteOutlined, SearchOutlined,
  ClockCircleOutlined, CopyOutlined, DownloadOutlined, AppstoreOutlined, UnorderedListOutlined,
} from '@ant-design/icons'
import { videoApi } from '../services/api'
import type { VideoProject } from '../types/video'

export default function VideoLibraryPage() {
  const [videos, setVideos] = useState<VideoProject[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'duration' | 'title'>('date')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  const loadLibrary = () => {
    setLoading(true)
    videoApi.library().then((res: any) => setVideos(res || [])).catch(() => message.error('加载失败')).finally(() => setLoading(false))
  }

  useEffect(() => { loadLibrary() }, [])

  const handleUncollect = async (id: number) => {
    await videoApi.collect(id); message.success('已移出成品库'); loadLibrary()
  }

  const handleDelete = async (id: number) => {
    await videoApi.delete(id); message.success('已删除'); loadLibrary()
  }

  const copyShareLink = (id: number) => {
    const url = `${window.location.origin}/api/video/projects/${id}/output`
    navigator.clipboard.writeText(url).then(() => message.success('链接已复制')).catch(() => message.info(url))
  }

  const filtered = useMemo(() => {
    let v = videos.filter(v => v.output_path)
    if (search) v = v.filter(v => v.title.toLowerCase().includes(search.toLowerCase()))
    v.sort((a: any, b: any) => {
      if (sortBy === 'date') return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
      if (sortBy === 'duration') return (b.duration_seconds || 0) - (a.duration_seconds || 0)
      return (a.title || '').localeCompare(b.title || '')
    })
    return v
  }, [videos, search, sortBy])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0 }}><HeartFilled style={{ color: '#eb2f96', marginRight: 8 }} />成品视频库</h2>
        <Space>
          <Input prefix={<SearchOutlined />} placeholder="搜索标题..." value={search} onChange={e => setSearch(e.target.value)}
            style={{ width: 180, borderRadius: 8 }} allowClear size="small" />
          <Select size="small" value={sortBy} onChange={setSortBy} style={{ width: 100 }}
            options={[{ label: '按时间', value: 'date' }, { label: '按时长', value: 'duration' }, { label: '按标题', value: 'title' }]} />
          <Button.Group size="small">
            <Button type={viewMode === 'grid' ? 'primary' : 'default'} icon={<AppstoreOutlined />} onClick={() => setViewMode('grid')} />
            <Button type={viewMode === 'list' ? 'primary' : 'default'} icon={<UnorderedListOutlined />} onClick={() => setViewMode('list')} />
          </Button.Group>
        </Space>
      </div>

      <Spin spinning={loading}>
        {filtered.length === 0 && !loading ? (
          <Empty description={<span>还没有成品视频<br />去 <a href="/video" style={{ color: '#1677ff' }}>视频生成</a> 页面，生成后点击收藏</span>} />
        ) : viewMode === 'grid' ? (
          <Row gutter={[16, 16]}>
            {filtered.map(v => (
              <Col xs={24} sm={12} md={8} lg={6} key={v.id}>
                <Card hoverable size="small" style={{ borderRadius: 12, overflow: 'hidden' }}
                  cover={v.output_path ? (
                    <div style={{ position: 'relative', background: '#000', height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <video src={`/api/video/projects/${v.id}/output`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} preload="metadata" muted />
                      <PlayCircleOutlined style={{ position: 'absolute', fontSize: 36, color: 'white', opacity: 0.7, pointerEvents: 'none' }} />
                    </div>
                  ) : <div style={{ background: '#1a1a2e', height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                    <PlayCircleOutlined style={{ fontSize: 40 }} /></div>}
                  actions={[
                    <Tooltip title="播放" key="play"><Button type="link" size="small" icon={<PlayCircleOutlined />}
                      onClick={() => window.open(`/api/video/projects/${v.id}/output`, '_blank')} /></Tooltip>,
                    <Tooltip title="复制链接" key="copy"><Button type="link" size="small" icon={<CopyOutlined />}
                      onClick={() => copyShareLink(v.id)} /></Tooltip>,
                    <Tooltip title="下载" key="dl"><Button type="link" size="small" icon={<DownloadOutlined />}
                      href={`/api/video/projects/${v.id}/output`} target="_blank" download /></Tooltip>,
                    <Tooltip title="取消收藏" key="uncol"><Button type="link" size="small" icon={<HeartFilled style={{ color: '#eb2f96' }} />}
                      onClick={() => handleUncollect(v.id)} /></Tooltip>,
                    <Popconfirm key="del" title="确定删除？" onConfirm={() => handleDelete(v.id)}>
                      <Button type="link" size="small" danger icon={<DeleteOutlined />} /></Popconfirm>,
                  ]}>
                  <Card.Meta title={<div style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.title}</div>}
                    description={<div style={{ fontSize: 12 }}>
                      <ClockCircleOutlined style={{ marginRight: 4 }} />{new Date(v.created_at).toLocaleDateString('zh-CN')}
                      {v.duration_seconds && <Tag style={{ marginLeft: 8 }}>{Math.floor(v.duration_seconds)}秒</Tag>}
                    </div>} />
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {filtered.map(v => (
              <Card key={v.id} size="small" style={{ borderRadius: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ width: 80, height: 60, borderRadius: 8, overflow: 'hidden', flexShrink: 0, background: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {v.output_path
                      ? <video src={`/api/video/projects/${v.id}/output`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} muted />
                      : <PlayCircleOutlined style={{ fontSize: 24, color: '#999' }} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 600 }}>{v.title}</div>
                    <div style={{ fontSize: 12, color: '#94a3b8' }}>
                      <ClockCircleOutlined /> {new Date(v.created_at).toLocaleDateString('zh-CN')}
                      {v.duration_seconds && <Tag style={{ marginLeft: 8 }}>{Math.floor(v.duration_seconds)}秒</Tag>}
                    </div>
                  </div>
                  <Space>
                    <Button size="small" icon={<PlayCircleOutlined />} onClick={() => window.open(`/api/video/projects/${v.id}/output`, '_blank')}>播放</Button>
                    <Button size="small" icon={<CopyOutlined />} onClick={() => copyShareLink(v.id)}>复制链接</Button>
                    <Button size="small" icon={<DownloadOutlined />} href={`/api/video/projects/${v.id}/output`} target="_blank" download />
                    <Popconfirm title="取消收藏？" onConfirm={() => handleUncollect(v.id)}>
                      <Button size="small" icon={<HeartFilled style={{ color: '#eb2f96' }} />} />
                    </Popconfirm>
                    <Popconfirm title="确定删除？" onConfirm={() => handleDelete(v.id)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Spin>
    </div>
  )
}
