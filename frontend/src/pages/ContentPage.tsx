import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Card, Input, Select, Button, Row, Col, List, Tag, message, Popconfirm, Modal, Tabs, Collapse, Slider, InputNumber } from 'antd'
import { EditOutlined, DeleteOutlined, CopyOutlined, VideoCameraOutlined, SendOutlined } from '@ant-design/icons'
import { contentApi } from '../services/api'
import type { RewrittenScript } from '../types/content'

const { TextArea } = Input

const styleOptions = [
  { label: '相似改写（保留原意）', value: 'similar' },
  { label: '原创风格（大幅改动）', value: 'original' },
  { label: '激进改写（仅保留核心）', value: 'aggressive' },
  { label: '原文使用（不调用AI）', value: 'keep' },
]

export default function ContentPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const topicText = (location.state as any)?.topicText || ''
  const [originalText, setOriginalText] = useState(topicText)
  const [style, setStyle] = useState('similar')
  const [marketingStyle, setMarketingStyle] = useState('')
  const [targetWordCount, setTargetWordCount] = useState<number>(0)
  const [scrapeUrl, setScrapeUrl] = useState('')
  const [scraping, setScraping] = useState(false)
  const [rewriting, setRewriting] = useState(false)
  const [scripts, setScripts] = useState<RewrittenScript[]>([])
  const [currentResult, setCurrentResult] = useState<RewrittenScript | null>(null)
  const [publishModal, setPublishModal] = useState(false)
  const [publishData, setPublishData] = useState<any>(null)
  const [titles, setTitles] = useState<string[]>([])
  const [generatingTitles, setGeneratingTitles] = useState(false)
  const [publishing, setPublishing] = useState(false)

  const loadScripts = () => {
    contentApi.scripts().then((res: any) => setScripts(res)).catch(() => message.error('加载历史记录失败'))
  }

  useEffect(() => { loadScripts() }, [])
  useEffect(() => {
    if (topicText) setOriginalText(topicText)
  }, [topicText])

  const handleRewrite = async () => {
    if (!originalText.trim()) return message.warning('请输入原文内容')
    setRewriting(true)
    try {
      const payload: any = { original_text: originalText, style }
      if (targetWordCount > 0) payload.target_word_count = targetWordCount
      if (marketingStyle) payload.marketing_style = marketingStyle
      const data = await contentApi.rewrite(payload) as any
      setCurrentResult(data)
      loadScripts()
      message.success(style === 'keep' ? '原文已保存' : '改写完成')
    } catch {
      message.error('操作失败，请重试')
    } finally {
      setRewriting(false)
    }
  }

  const handleKeepOriginal = async () => {
    if (!originalText.trim()) return message.warning('请输入原文内容')
    setRewriting(true)
    try {
      const data = await contentApi.rewrite({ original_text: originalText, style: 'keep' }) as any
      setCurrentResult(data)
      loadScripts()
      message.success('原文已保存')
    } catch {
      message.error('保存失败')
    } finally {
      setRewriting(false)
    }
  }

  const handleDelete = async (id: number) => {
    await contentApi.deleteScript(id)
    message.success('已删除')
    if (currentResult?.id === id) setCurrentResult(null)
    loadScripts()
  }

  const handleGeneratePublish = async (id: number) => {
    setPublishing(true)
    try {
      const res: any = await contentApi.generatePublish(id)
      setPublishData(res.data || res)
      setPublishModal(true)
    } catch {
      message.error('生成失败')
    } finally {
      setPublishing(false)
    }
  }

  const handleGenerateTitles = async () => {
    if (!originalText.trim()) return message.warning('请先输入原文')
    setGeneratingTitles(true)
    try {
      const res: any = await contentApi.generateTitles(originalText)
      if (res.code === 0 && res.data) {
        setTitles(res.data)
        message.success(`生成了 ${res.data.length} 个标题`)
      } else {
        message.error(res.message || '生成失败')
      }
    } catch {
      message.error('生成失败')
    } finally {
      setGeneratingTitles(false)
    }
  }

  const handleScrape = async () => {
    if (!scrapeUrl.trim()) return message.warning('请输入链接地址')
    setScraping(true)
    try {
      const res: any = await contentApi.scrape(scrapeUrl, 'douyin')
      if (res.code === 0 && res.data?.text) {
        setOriginalText(res.data.text)
        message.success(`已提取 ${res.data.text.length} 字`)
      } else {
        message.warning(res.message || '提取失败，请手动粘贴')
      }
    } catch {
      message.error('抓取失败，请检查链接或手动粘贴')
    } finally {
      setScraping(false)
    }
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  }

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}><EditOutlined style={{ color: '#1677ff', marginRight: 8 }} />内容改写</h2>

      <Row gutter={24}>
        {/* 左侧：输入区 */}
        <Col span={10}>
          <Card title="原文输入" size="small">
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <Input
                placeholder="粘贴链接自动提取正文（公众号/知乎/B站...）"
                value={scrapeUrl}
                onChange={(e) => setScrapeUrl(e.target.value)}
                onPressEnter={handleScrape}
                style={{ flex: 1 }}
              />
              <Button loading={scraping} onClick={handleScrape}>提取</Button>
            </div>
            <TextArea
              rows={10}
              placeholder="在此粘贴需要改写的文案内容..."
              value={originalText}
              onChange={(e) => setOriginalText(e.target.value)}
            />
            <div style={{ marginTop: 12, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
              <Select value={style} onChange={setStyle} options={styleOptions} style={{ width: 200 }} />
              <Select value={marketingStyle} onChange={setMarketingStyle} allowClear
                placeholder="营销风格（可选）" style={{ width: 180 }}
                options={[
                  { label: '研究驱动', value: 'ogilvy' }, { label: '直复营销', value: 'halbert' },
                  { label: '欲望引导', value: 'schwartz' }, { label: 'AIDA经典', value: 'aida' },
                  { label: '痛点解决', value: 'pas' },
                ]} />
              <Button type="primary" loading={rewriting} onClick={handleRewrite} icon={<EditOutlined />}>
                AI 改写
              </Button>
              <Button loading={rewriting} onClick={handleKeepOriginal}>
                原文使用
              </Button>
              <Button loading={generatingTitles} onClick={handleGenerateTitles}>
                生成标题
              </Button>
            </div>
            {titles.length > 0 && (
              <div style={{ marginTop: 8, padding: 8, background: '#fffbe6', borderRadius: 4 }}>
                <div style={{ fontSize: 12, color: '#d48806', marginBottom: 4 }}>AI生成标题（点击复制）：</div>
                {titles.map((t, i) => (
                  <div key={i} style={{ fontSize: 13, padding: '2px 0', cursor: 'pointer' }}
                    onClick={() => { navigator.clipboard.writeText(t); message.success('标题已复制') }}>
                    {i+1}. {t}
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 12, color: '#666', whiteSpace: 'nowrap' }}>目标字数（0=不限制）：</span>
              <Slider
                min={0} max={2000} step={50}
                value={targetWordCount}
                onChange={setTargetWordCount}
                style={{ flex: 1 }}
              />
              <InputNumber min={0} max={2000} step={50} value={targetWordCount} onChange={(v) => setTargetWordCount(v || 0)} style={{ width: 70 }} />
            </div>
          </Card>
        </Col>

        {/* 右侧：结果区 */}
        <Col span={14}>
          <Card
            title="改写结果"
            size="small"
            extra={currentResult && (
              <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(currentResult.rewritten_text)}>
                复制
              </Button>
            )}
          >
            {currentResult ? (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <Tag color="blue">{styleOptions.find((s) => s.value === currentResult.style)?.label}</Tag>
                  <span style={{ color: '#999', fontSize: 12 }}>约 {currentResult.word_count} 字</span>
                </div>
                <div
                  style={{
                    background: '#fafafa',
                    padding: 16,
                    borderRadius: 8,
                    whiteSpace: 'pre-wrap',
                    minHeight: 200,
                    lineHeight: 1.8,
                  }}
                >
                  {currentResult.rewritten_text}
                </div>
                <div style={{ marginTop: 16, textAlign: 'right' }}>
                  <Button
                    type="primary"
                    icon={<VideoCameraOutlined />}
                    onClick={() => navigate('/video', { state: { scriptId: currentResult.id } })}
                  >
                    用这条文案生成视频
                  </Button>
                </div>
              </div>
            ) : (
              <div style={{ color: '#999', textAlign: 'center', padding: 60 }}>输入文案并点击"AI 改写"查看结果</div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 历史记录 */}
      <Collapse
        style={{ marginTop: 24 }}
        defaultActiveKey={[]}
        items={[
          {
            key: 'history',
            label: `改写历史（${scripts.length} 条）`,
            children: (
              <List
                dataSource={scripts}
                locale={{ emptyText: '暂无改写记录' }}
                renderItem={(item) => (
                  <List.Item
                    style={{ cursor: 'pointer' }}
                    onClick={() => setCurrentResult(item)}
                    actions={[
                      <Button
                        key="video"
                        size="small"
                        icon={<VideoCameraOutlined />}
                        onClick={(e) => { e.stopPropagation(); navigate('/video', { state: { scriptId: item.id } }) }}
                      />,
                      <Button
                        key="publish"
                        size="small"
                        icon={<SendOutlined />}
                        loading={publishing}
                        onClick={(e) => { e.stopPropagation(); handleGeneratePublish(item.id) }}
                      />,
                      <Button
                        key="copy"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={(e) => { e.stopPropagation(); handleCopy(item.rewritten_text) }}
                      />,
                      <Popconfirm
                        key="del"
                        title="确定删除？"
                        onConfirm={(e) => { e?.stopPropagation(); handleDelete(item.id) }}
                        onCancel={(e) => e?.stopPropagation()}
                      >
                        <Button size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                      </Popconfirm>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <span>
                          <Tag>{styleOptions.find((s) => s.value === item.style)?.label}</Tag>
                          {item.original_text.slice(0, 50)}{'...'}
                        </span>
                      }
                      description={item.rewritten_text.slice(0, 80) + '...'}
                    />
                  </List.Item>
                )}
              />
            ),
          },
        ]}
      />

      <Modal
        title="多平台发布文案"
        open={publishModal}
        onCancel={() => setPublishModal(false)}
        footer={null}
        width={700}
      >
        {publishData && (
          <Tabs items={[
            { key: 'douyin', label: '抖音', children: <PlatformContent data={publishData.douyin} /> },
            { key: 'shipinhao', label: '视频号', children: <PlatformContent data={publishData.shipinhao} /> },
            { key: 'kuaishou', label: '快手', children: <PlatformContent data={publishData.kuaishou} /> },
            { key: 'xiaohongshu', label: '小红书', children: <PlatformContent data={publishData.xiaohongshu} /> },
          ]} />
        )}
      </Modal>
    </div>
  )
}

function PlatformContent({ data }: { data: any }) {
  if (!data) return <div style={{ color: '#999' }}>暂无数据</div>
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <strong>标题：</strong>
        <div style={{ fontSize: 16, marginTop: 4, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
          {data.title}
          <Button type="link" size="small" icon={<CopyOutlined />}
            onClick={() => { navigator.clipboard.writeText(data.title); message.success('标题已复制') }} />
        </div>
      </div>
      <div style={{ marginBottom: 16 }}>
        <strong>描述/正文：</strong>
        <div style={{ marginTop: 4, padding: 8, background: '#f5f5f5', borderRadius: 4, whiteSpace: 'pre-wrap' }}>
          {data.desc}
          <Button type="link" size="small" icon={<CopyOutlined />}
            onClick={() => { navigator.clipboard.writeText(data.desc); message.success('描述已复制') }} />
        </div>
      </div>
      {data.tags && (
        <div>
          <strong>推荐标签：</strong>
          <div style={{ marginTop: 4, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
            {data.tags}
            <Button type="link" size="small" icon={<CopyOutlined />}
              onClick={() => { navigator.clipboard.writeText(data.tags); message.success('标签已复制') }} />
          </div>
        </div>
      )}
    </div>
  )
}
