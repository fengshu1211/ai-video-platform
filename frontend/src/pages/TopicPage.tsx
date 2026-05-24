import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Select, Row, Col, Tag, Spin, Empty, message, Button, Modal } from 'antd'
import { FireOutlined, LikeOutlined, CommentOutlined, PlayCircleOutlined, SyncOutlined, RightOutlined, RobotOutlined } from '@ant-design/icons'
import { trackApi, topicApi, contentApi } from '../services/api'
import type { Track, HotTopic } from '../types/topic'

export default function TopicPage() {
  const navigate = useNavigate()
  const [tracks, setTracks] = useState<Track[]>([])
  const [topics, setTopics] = useState<HotTopic[]>([])
  const [trackId, setTrackId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedTopic, setSelectedTopic] = useState<HotTopic | null>(null)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    trackApi.list().then(setTracks).catch(() => message.error('加载赛道失败'))
  }, [])

  const loadTopics = (tid?: number) => {
    setLoading(true)
    topicApi.list(tid).then(setTopics).catch(() => message.error('加载选题失败')).finally(() => setLoading(false))
  }

  useEffect(() => { loadTopics(trackId) }, [trackId])

  const handleRefresh = async () => {
    if (!trackId) return message.warning('请先选择赛道')
    setRefreshing(true)
    try {
      const data = await topicApi.refresh(trackId) as any
      setTopics(data)
      message.success('AI已生成最新选题')
    } catch {
      message.error('刷新失败，请重试')
    } finally {
      setRefreshing(false)
    }
  }

  const safeParseMetrics = (json?: string) => {
    try {
      return JSON.parse(json || '{}')
    } catch {
      return {}
    }
  }

  const openDetail = (topic: HotTopic) => {
    setSelectedTopic(topic)
    setDetailModalOpen(true)
  }

  const handleUseTopic = async () => {
    if (!selectedTopic) return
    setGenerating(true)
    try {
      // 基于选题主题+分析，让AI展开成完整口播文案
      const fullPrompt = `选题：${selectedTopic.title}\nAI分析：${selectedTopic.ai_analysis || '暂无'}\n请将以上选题展开成一篇完整的历史口播文案（200-500字），适合短视频配音。`
      const res: any = await contentApi.rewrite({ original_text: fullPrompt, style: 'original' })
      message.success('文案已生成')
      navigate('/content', { state: { topicText: res.rewritten_text || fullPrompt } })
    } catch {
      navigate('/content', { state: { topicText: `选题：${selectedTopic.title}\n${selectedTopic.ai_analysis || ''}` } })
    } finally {
      setGenerating(false)
      setDetailModalOpen(false)
    }
  }

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>
        <FireOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
        爆款选题
      </h2>

      <div style={{ marginBottom: 24 }}>
        <Select
          placeholder="选择内容赛道"
          allowClear
          style={{ width: 240 }}
          value={trackId}
          onChange={(v) => setTrackId(v)}
          options={tracks.map((t) => ({ label: t.name, value: t.id }))}
        />
        <Button icon={<SyncOutlined />} onClick={handleRefresh} loading={refreshing} style={{ marginLeft: 12 }}>
          AI刷新选题
        </Button>
      </div>

      <Spin spinning={loading}>
        {topics.length === 0 && !loading ? (
          <Empty description={trackId ? '该赛道暂无选题数据' : '请先选择赛道，或先添加赛道'} />
        ) : (
          <Row gutter={[16, 16]}>
            {topics.map((t, i) => {
              const metrics = safeParseMetrics(t.metrics_json)
              return (
                <Col span={8} key={t.id}>
                  <Card
                    hoverable
                    onClick={() => openDetail(t)}
                    bodyStyle={{ padding: 16 }}
                  >
                    <div style={{ marginBottom: 8 }}>
                      <Tag color="red">TOP {i + 1}</Tag>
                      {t.platform && <Tag>{t.platform}</Tag>}
                    </div>
                    <h4 style={{ margin: '0 0 8px', fontSize: 15, lineHeight: 1.5, minHeight: 45 }}>{t.title}</h4>
                    {t.ai_analysis && (
                      <p style={{ color: '#666', fontSize: 12, margin: '0 0 12px', lineHeight: 1.5 }}>
                        <RobotOutlined style={{ color: '#1677ff', marginRight: 4 }} />
                        {t.ai_analysis}
                      </p>
                    )}
                    <div style={{ display: 'flex', gap: 16, color: '#999', fontSize: 12 }}>
                      <span><PlayCircleOutlined /> {metrics.views || '-'}</span>
                      <span><LikeOutlined /> {metrics.likes || '-'}</span>
                      <span><CommentOutlined /> {metrics.comments || '-'}</span>
                    </div>
                  </Card>
                </Col>
              )
            })}
          </Row>
        )}
      </Spin>

      <Modal
        title="选题详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={520}
      >
        {selectedTopic && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Tag color="red">热门</Tag>
              {selectedTopic.platform && <Tag>{selectedTopic.platform}</Tag>}
            </div>
            <h3 style={{ marginBottom: 12 }}>{selectedTopic.title}</h3>
            {selectedTopic.ai_analysis && (
              <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, marginBottom: 16, fontSize: 13, color: '#555', lineHeight: 1.6 }}>
                <RobotOutlined style={{ color: '#1677ff', marginRight: 6 }} />
                {selectedTopic.ai_analysis}
              </div>
            )}
            {(() => {
              const m = safeParseMetrics(selectedTopic.metrics_json)
              return (
                <div style={{ display: 'flex', gap: 24, marginBottom: 24, padding: '12px 0', borderTop: '1px solid #f0f0f0', borderBottom: '1px solid #f0f0f0' }}>
                  <div><div style={{ fontSize: 12, color: '#999' }}>播放量</div><div style={{ fontSize: 16, fontWeight: 600 }}>{m.views || '-'}</div></div>
                  <div><div style={{ fontSize: 12, color: '#999' }}>点赞</div><div style={{ fontSize: 16, fontWeight: 600 }}>{m.likes || '-'}</div></div>
                  <div><div style={{ fontSize: 12, color: '#999' }}>评论</div><div style={{ fontSize: 16, fontWeight: 600 }}>{m.comments || '-'}</div></div>
                </div>
              )
            })()}
            <Button type="primary" block size="large" icon={<RightOutlined />} loading={generating} onClick={handleUseTopic}>
              用这个选题生成文案
            </Button>
          </div>
        )}
      </Modal>
    </div>
  )
}
