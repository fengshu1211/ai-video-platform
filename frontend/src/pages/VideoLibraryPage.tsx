import { useEffect, useState } from 'react'
import { Card, Row, Col, Tag, Button, Empty, Spin, message, Popconfirm } from 'antd'
import {
  PlayCircleOutlined, HeartOutlined, HeartFilled, DeleteOutlined,
  FolderOpenOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import { videoApi } from '../services/api'
import type { VideoProject } from '../types/video'

export default function VideoLibraryPage() {
  const [videos, setVideos] = useState<VideoProject[]>([])
  const [loading, setLoading] = useState(true)

  const loadLibrary = () => {
    setLoading(true)
    videoApi.library().then((res: any) => setVideos(res || [])).catch(() => message.error('加载失败')).finally(() => setLoading(false))
  }

  useEffect(() => { loadLibrary() }, [])

  const handleUncollect = async (id: number) => {
    await videoApi.collect(id)
    message.success('已移出成品库')
    loadLibrary()
  }

  const handleDelete = async (id: number) => {
    await videoApi.delete(id)
    message.success('已删除')
    loadLibrary()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>
        <HeartFilled style={{ color: '#eb2f96', marginRight: 8 }} />
        成品视频库
      </h2>

      <Spin spinning={loading}>
        {videos.length === 0 && !loading ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                还没有成品视频<br />
                去 <a href="/video" style={{ color: '#1677ff' }}>视频生成</a> 页面，生成视频后点击收藏即可
              </span>
            }
          />
        ) : (
          <Row gutter={[16, 16]}>
            {videos.map((v) => (
              <Col span={6} key={v.id}>
                <Card
                  hoverable
                  cover={
                    v.output_path ? (
                      <div style={{ position: 'relative', background: '#000', height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <video
                          src={`/api/video/projects/${v.id}/output`}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          preload="metadata"
                          muted
                        />
                        <PlayCircleOutlined
                          style={{ position: 'absolute', fontSize: 40, color: 'white', opacity: 0.8, pointerEvents: 'none' }}
                        />
                      </div>
                    ) : (
                      <div style={{ background: '#1a1a2e', height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                        <FolderOpenOutlined style={{ fontSize: 40 }} />
                      </div>
                    )
                  }
                  actions={[
                    <Button type="link" icon={<PlayCircleOutlined />} key="play"
                      onClick={() => v.output_path && window.open(`/api/video/projects/${v.id}/output`, '_blank')}>
                      播放
                    </Button>,
                    <Button type="link" icon={<HeartFilled style={{ color: '#eb2f96' }} />} key="uncollect"
                      onClick={() => handleUncollect(v.id)}>
                      取消收藏
                    </Button>,
                    <Popconfirm key="del" title="确定删除？" onConfirm={() => handleDelete(v.id)}>
                      <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>,
                  ]}
                >
                  <Card.Meta
                    title={v.title}
                    description={
                      <div>
                        <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
                          <ClockCircleOutlined style={{ marginRight: 4 }} />
                          {new Date(v.created_at).toLocaleString('zh-CN')}
                        </div>
                        {v.duration_seconds && (
                          <Tag>{Math.floor(v.duration_seconds)}秒</Tag>
                        )}
                        <Tag color="success">已完成</Tag>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </div>
  )
}
