import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Table, Tag, Button, Modal, Form, Input, Select, message, Switch, Progress, Empty, Alert, Card, Upload, Image, Popconfirm } from 'antd'
import {
  VideoCameraOutlined, PlusOutlined, PlayCircleOutlined, DeleteOutlined,
  ThunderboltOutlined, InboxOutlined, HeartOutlined, HeartFilled,
} from '@ant-design/icons'
import { videoApi, contentApi, voiceApi, uploadApi } from '../services/api'
import type { VideoProject } from '../types/video'
import type { RewrittenScript } from '../types/content'
import type { VoiceProfile } from '../types/voice'

export default function VideoPage() {
  const location = useLocation()
  const passedScriptId = (location.state as any)?.scriptId as number | undefined
  const passedVoiceId = (location.state as any)?.voiceId as number | undefined

  const [projects, setProjects] = useState<VideoProject[]>([])
  const [scripts, setScripts] = useState<RewrittenScript[]>([])
  const [voices, setVoices] = useState<VoiceProfile[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [uploadedMaterials, setUploadedMaterials] = useState<string[]>([])
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [libraryFiles, setLibraryFiles] = useState<any[]>([])
  const [selectedLib, setSelectedLib] = useState<string[]>([])
  const [templates, setTemplates] = useState<any[]>([])
  const [applyingTemplate, setApplyingTemplate] = useState<string | null>(null)
  const [form] = Form.useForm()

  const loadData = () => {
    Promise.all([
      videoApi.list().then(setProjects),
      contentApi.scripts().then(setScripts),
      voiceApi.profiles().then(setVoices),
      fetch('/api/templates/projects').then(r => r.json()).then(d => setTemplates(d.templates || [])),
    ]).catch(() => message.error('加载数据失败'))
  }

  const applyTemplate = async (templateId: string) => {
    setApplyingTemplate(templateId)
    try {
      const res = await fetch(`/api/templates/projects/${templateId}/apply`)
      const data = await res.json()
      if (!res.ok) { message.error('获取模板失败'); return }
      const tmpl = data.template
      // Create project from template
      const createRes = await videoApi.create({
        title: tmpl.title,
        script_text: tmpl.script_text,
        voice_id: voices.find(v => v.voice_id === tmpl.voice_id)?.id || voices[0]?.id,
        aspect_ratio: tmpl.aspect_ratio,
        subtitle_enabled: tmpl.subtitle_enabled,
        image_animation_type: tmpl.image_animation_type,
      })
      if (createRes) {
        message.success(`已创建「${tmpl.title}」，点击生成即可`)
        loadData()
      }
    } catch { message.error('应用模板失败') }
    setApplyingTemplate(null)
  }

  useEffect(() => { loadData() }, [])

  // 如果从内容页/语音页带 ID 跳转过来，自动打开创建弹窗（仅首次）
  const autoOpened = useRef(false)
  useEffect(() => {
    if (autoOpened.current) return
    const values: any = {}
    if (passedScriptId && scripts.length > 0) values.script_id = passedScriptId
    if (passedVoiceId && voices.length > 0) values.voice_id = passedVoiceId
    if (Object.keys(values).length > 0) {
      autoOpened.current = true
      setModalOpen(true)
      form.setFieldsValue(values)
    }
  }, [passedScriptId, passedVoiceId, scripts.length, voices.length, form])
  useEffect(() => {
    const timer = setInterval(loadData, 5000)
    return () => clearInterval(timer)
  }, [])

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      const mode = values.video_mode || 'none'

      // 模式映射
      let lip_sync_enabled = 0
      let lip_sync_mode = 'none'
      let image_animation_type: string | null = null

      if (mode === 'digital_human') {
        lip_sync_enabled = 1
        lip_sync_mode = 'digital_human'
      } else if (mode === 'lip_sync_pip') {
        lip_sync_enabled = 1
        lip_sync_mode = 'pip'
      } else if (mode === 'lip_sync_full') {
        lip_sync_enabled = 1
        lip_sync_mode = 'full'
      } else if (mode === 'auto_align') {
        lip_sync_enabled = 1
        lip_sync_mode = 'auto_align'
      } else if (mode === 'virtual_host') {
        lip_sync_enabled = 1
        lip_sync_mode = 'virtual_host'
      } else if (mode === 'audio_only') {
        lip_sync_enabled = 1
        lip_sync_mode = 'audio_only'
      } else if (mode === 'image_animation') {
        image_animation_type = values.animation_sub_type || 'zoom_in'
      }

      await videoApi.create({
        title: values.title,
        script_id: values.script_id,
        voice_id: values.voice_id,
        aspect_ratio: values.aspect_ratio ?? '9:16',
        subtitle_enabled: values.subtitle_enabled ?? 1,
        lip_sync_enabled,
        lip_sync_mode,
        image_animation_type,

        material_paths_json: JSON.stringify(uploadedMaterials),
        bgm_volume: values.bgm_volume ?? 0.3,
      })
      message.success('项目创建成功')
      setModalOpen(false)
      setUploadedMaterials([])
      form.resetFields()
      loadData()
    } catch { /* validation */ }
  }

  const handleGenerate = async (id: number) => {
    try {
      const res: any = await videoApi.generate(id)
      if (res.code === 1) {
        message.warning(res.message)
        return
      }
      message.success('视频生成任务已提交，正在自动搜图+语音合成+配字幕')
      loadData()
    } catch {
      message.error('提交失败')
    }
  }

  const handleCollect = async (id: number, collected: number) => {
    await videoApi.collect(id)
    message.success(collected ? '已取消收藏' : '已收藏到成品库')
    loadData()
  }

  const handleDelete = async (id: number) => {
    await videoApi.delete(id)
    message.success('已删除')
    loadData()
  }

  const statusMap: Record<string, { color: string; label: string }> = {
    draft: { color: 'default', label: '草稿' },
    processing: { color: 'processing', label: '生成中' },
    completed: { color: 'success', label: '已完成' },
    failed: { color: 'error', label: '失败' },
  }

  const columns = [
    { title: '项目名称', dataIndex: 'title', key: 'title' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => {
        const m = statusMap[s] || { color: 'default', label: s }
        return <Tag color={m.color}>{m.label}</Tag>
      },
    },
    {
      title: '时长', dataIndex: 'duration_seconds', key: 'duration',
      render: (v: number | null) => v ? `${Math.floor(v)}秒` : '-',
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作', key: 'actions',
      render: (_: any, record: VideoProject) => (
        <div style={{ display: 'flex', gap: 8 }}>
          {record.status === 'draft' && (
            <Button size="small" type="primary" icon={<ThunderboltOutlined />} onClick={() => handleGenerate(record.id)}>
              一键生成
            </Button>
          )}
          {record.status === 'completed' && record.output_path && (
            <Button size="small" type="link" onClick={() => window.open(`/api/video/projects/${record.id}/output`, '_blank')}>
              播放
            </Button>
          )}
          {record.status === 'completed' && (
            <Button size="small" type="link"
              icon={record.collected ? <HeartFilled style={{ color: '#eb2f96' }} /> : <HeartOutlined />}
              onClick={() => handleCollect(record.id, record.collected)}>
              {record.collected ? '已收藏' : '收藏'}
            </Button>
          )}
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>删除</Button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2><VideoCameraOutlined style={{ color: '#722ed1', marginRight: 8 }} />视频生成</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          if (scripts.length === 0) {
            message.warning('还没有文案，请先去「内容改写」创作文案')
            return
          }
          setModalOpen(true)
        }}>
          新建项目
        </Button>
      </div>

      <Alert
        message="视频生成说明"
        description="建议优先上传自己的实拍照片/视频素材，出来的视频才是独一无二的。系统搜图匹配只是备用方案，不一定精准适配你的内容。支持Ken Burns镜头动画、交叉淡化转场。露脸可选’自动对齐’或’对口型’模式，不露脸选’图文解说’。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 成品模板 */}
      {templates.length > 0 && (
        <Card size="small" title="成品模板（一键创建）" style={{ marginBottom: 16, borderRadius: 12 }}>
          <div style={{ display: ‘flex’, gap: 12, overflowX: ‘auto’, paddingBottom: 4 }}>
            {templates.map((t: any) => (
              <Card
                key={t.id}
                size="small"
                hoverable
                style={{ minWidth: 200, borderRadius: 10, border: ‘1px solid rgba(148,163,184,0.08)’ }}
                onClick={() => applyTemplate(t.id)}
                loading={applyingTemplate === t.id}
              >
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{t.title}</div>
                <div style={{ fontSize: 12, color: ‘#94a3b8’, marginBottom: 6 }}>{t.desc}</div>
                <Tag color="blue" style={{ fontSize: 11 }}>{t.category}</Tag>
                <Tag color="green" style={{ fontSize: 11 }}>一键创建</Tag>
              </Card>
            ))}
          </div>
        </Card>
      )}

      <Table
        columns={columns}
        dataSource={projects}
        rowKey="id"
        locale={{ emptyText: <Empty description="暂无视频项目，点击右上角新建" /> }}
      />

      <Modal
        title="新建视频项目"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        width={560}
      >
        <Form form={form} layout="vertical">
          {/* ── 基础信息 ── */}
          <Card size="small" title="📋 基础信息" style={{ marginBottom: 12 }}>
            <Form.Item name="title" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
              <Input placeholder="如：明清历史解说第一期" />
            </Form.Item>
            <Form.Item name="script_id" label="解说文案" rules={[{ required: true, message: '请选择文案' }]}>
              {scripts.length === 0 ? (
                <div style={{ padding: 12, background: 'rgba(245,158,11,0.1)', borderRadius: 8, fontSize: 13, color: '#fbbf24' }}>
                  还没有文案。请先去 <a href="/content" style={{ color: '#60a5fa' }}>内容改写</a> 创作或导入文案，有了文案才能生成视频。
                </div>
              ) : (
              <Select
                placeholder="选择已改写好的文案"
                options={scripts.map((s) => ({
                  label: (s.rewritten_text || s.original_text).slice(0, 50) + '...',
                  value: s.id,
                }))}
              />
              )}
            </Form.Item>
            <Form.Item name="voice_id" label="配音">
              <Select
                placeholder="选个声音"
                allowClear
                options={voices.map((v) => ({ label: v.name, value: v.id }))}
              />
            </Form.Item>
          </Card>

          {/* ── 视频模式（核心选择）── */}
          <Card size="small" title="🎬 视频模式" style={{ marginBottom: 12 }}>
            <Form.Item name="video_mode" label="你想做什么样的视频？" initialValue="image_animation">
              <Select
                options={[
                  { label: '🖼️ 图文解说（图片+镜头动画，不露脸）', value: 'image_animation' },
                  { label: '🎤 露脸口播（自拍视频自动调速对齐，免费）', value: 'auto_align' },
                  { label: '🤖 AI虚拟主播（一张照片→呼吸感微动，免费）', value: 'virtual_host' },
                  { label: '⏹️ 静态素材（无特效）', value: 'none' },
                  { label: '── 以下需要GPU ──', value: '', disabled: true },
                  { label: '🗣️ 数字人（一张照片→开口说话）', value: 'digital_human' },
                  { label: '🎥 画中画口播（自拍视频缩小到角落）', value: 'lip_sync_pip' },
                  { label: '🎬 全屏口播（自拍视频铺满全屏）', value: 'lip_sync_full' },
                ]}
              />
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(prev, cur) => prev.video_mode !== cur.video_mode}>
              {({ getFieldValue }) => {
                const mode = getFieldValue('video_mode')
                if (mode === 'image_animation') {
                  return (
                    <Form.Item name="animation_sub_type" label="镜头效果" initialValue="zoom_in">
                      <Select options={[
                        { label: '缓慢放大（纪录片感）', value: 'zoom_in' },
                        { label: '缓慢缩小', value: 'zoom_out' },
                        { label: '从左往右平移', value: 'pan_left' },
                        { label: '从右往左平移', value: 'pan_right' },
                        { label: '从下往上平移', value: 'pan_up' },
                        { label: '从上往下平移', value: 'pan_down' },
                      ]} />
                    </Form.Item>
                  )
                }
                if (mode === 'digital_human') {
                  return (
                    <div style={{ padding: 8, background: '#fff7e6', borderRadius: 4, fontSize: 12, color: '#d48806' }}>
                      💡 上传素材时，第一张图会自动作为数字人照片使用
                    </div>
                  )
                }
                if (mode === 'lip_sync_pip' || mode === 'lip_sync_full') {
                  return (
                    <div style={{ padding: 8, background: '#fff7e6', borderRadius: 4, fontSize: 12, color: '#d48806' }}>
                      💡 上传素材时，第一个视频会自动对口型
                    </div>
                  )
                }
                return null
              }}
            </Form.Item>
            <Form.Item name="aspect_ratio" label="画面比例" initialValue="9:16">
              <Select options={[
                { label: '📱 竖版 9:16（抖音/快手）', value: '9:16' },
                { label: '💻 横版 16:9（B站/YouTube）', value: '16:9' },
                { label: '⬜ 方形 1:1（微信/小红书）', value: '1:1' },
              ]} />
            </Form.Item>
          </Card>

          {/* ── 素材上传 ── */}
          <Card size="small" title="🖼️ 上传素材（强烈建议）" style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: '#fbbf24', marginBottom: 8 }}>
              ⭐ 上传你自己的实拍照片/视频，视频才有专属风格。不传则自动搜图（匹配度有限）。
            </div>
            <Upload
              multiple
              accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.mov,.avi,.webm,.mkv"
              action="/api/upload/file?file_type=videos"
              showUploadList={false}
              onChange={(info: any) => {
                if (info.file.status === 'done') {
                  const resp = info.file.response
                  const path = resp?.data?.path || resp?.path
                  if (path) {
                    setUploadedMaterials((p: string[]) => [path, ...p])
                    message.success(`${info.file.name} 已上传`)
                  }
                } else if (info.file.status === 'error') {
                  message.error(`${info.file.name} 上传失败`)
                }
              }}
            >
              <Button icon={<InboxOutlined />} size="small">本地上传</Button>
            </Upload>
            <Button size="small" style={{ marginLeft: 8 }} icon={<InboxOutlined />} onClick={async () => {
              setLibraryOpen(true)
              try {
                const res: any = await uploadApi.listFiles()
                const files = Array.isArray(res) ? res : (res.data || res.code !== undefined ? res.data : [])
                setLibraryFiles(files)
                if (files.length === 0) message.info('素材库为空')
              } catch { message.error('加载素材库失败') }
            }}>素材库</Button>
            {uploadedMaterials.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {uploadedMaterials.map((path, i) => (
                  <Tag key={i} closable onClose={() => setUploadedMaterials((p: string[]) => p.filter((x: string) => x !== path))}
                    style={{ marginBottom: 4 }}>
                    {path.split('/').pop()}
                  </Tag>
                ))}
              </div>
            )}
          </Card>

          {/* ── 高级设置（默认折叠）── */}
          <Card size="small" title="⚙️ 高级设置" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              <Form.Item name="subtitle_enabled" label="自动生成字幕" initialValue={true} valuePropName="checked" style={{ marginBottom: 0 }}>
                <Switch checkedChildren="开" unCheckedChildren="关" />
              </Form.Item>
              <Form.Item name="bgm_volume" label="背景音乐音量" initialValue={0.3} style={{ marginBottom: 0 }}>
                <Select style={{ width: 120 }} options={[
                  { label: '轻柔', value: 0.15 },
                  { label: '适中', value: 0.3 },
                  { label: '明显', value: 0.5 },
                ]} />
              </Form.Item>
            </div>
          </Card>

          <Alert
            message="点击确定后生成视频，自动执行：AI导演分析 → 搜图匹配 → 语音合成 → 字幕生成"
            type="info"
            showIcon
            style={{ fontSize: 12 }}
          />
        </Form>
      </Modal>

      <Modal
        title="素材库"
        open={libraryOpen}
        onCancel={() => setLibraryOpen(false)}
        onOk={() => {
          setUploadedMaterials((p: string[]) => [...p, ...selectedLib])
          setSelectedLib([])
          setLibraryOpen(false)
        }}
        okText="确认选择"
        width={700}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, maxHeight: 450, overflow: 'auto' }}>
          {libraryFiles.map((f: any) => (
            <div key={f.path} style={{
              width: 140, position: 'relative',
              border: selectedLib.includes(f.path) ? '2px solid #1677ff' : '1px solid #eee',
              borderRadius: 6, padding: 4, cursor: 'pointer'
            }} onClick={() => {
              setSelectedLib((p: string[]) => p.includes(f.path) ? p.filter((x: string) => x !== f.path) : [...p, f.path])
            }}>
              <Popconfirm title="确定删除？" onConfirm={async (e) => {
                e?.stopPropagation()
                try { await uploadApi.deleteFile(f.path); message.success('已删除'); setLibraryFiles((p: any[]) => p.filter((x: any) => x.path !== f.path)) }
                catch { message.error('删除失败') }
              }} onCancel={(e) => e?.stopPropagation()}>
                <Button size="small" danger icon={<DeleteOutlined />} type="link"
                  style={{ position: 'absolute', top: 2, right: 2, zIndex: 1 }}
                  onClick={(e) => e.stopPropagation()} />
              </Popconfirm>
              {f.type === 'image'
                ? <Image src={`/uploads/${f.path}`} preview={true} style={{ width: '100%', height: 90, objectFit: 'cover', borderRadius: 4 }} />
                : <div style={{ width: '100%', height: 90, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 4 }}>
                    <video src={`/uploads/${f.path}`} controls style={{ width: '100%', height: 90, objectFit: 'cover' }} />
                  </div>
              }
              <div style={{ fontSize: 10, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</div>
              <div style={{ fontSize: 10, color: '#999' }}>{(f.size/1024).toFixed(0)}KB</div>
            </div>
          ))}
          {libraryFiles.length === 0 && (
            <div style={{ color: '#999', padding: 40, textAlign: 'center', width: '100%' }}>
              <p style={{ fontSize: 16, marginBottom: 8 }}>暂无素材</p>
              <p style={{ fontSize: 12 }}>请先在上方上传人物照片或背景素材</p>
              <Button type="primary" onClick={() => setLibraryOpen(false)} style={{ marginTop: 12 }}>关闭</Button>
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
