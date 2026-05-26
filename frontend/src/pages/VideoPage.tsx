import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Table, Tag, Button, Modal, Form, Input, Select, message, Switch, Progress, Empty, Alert, Card, Upload, Image, Popconfirm, Steps } from 'antd'
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
  const [form] = Form.useForm()
  const [wizardStep, setWizardStep] = useState(0)

  const loadData = () => {
    Promise.all([
      videoApi.list().then(setProjects),
      contentApi.scripts().then(setScripts),
      voiceApi.profiles().then(setVoices),
    ]).catch(() => message.error('加载数据失败'))
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
      const mode = values.video_mode || 'image_animation'

      let lip_sync_enabled = 0
      let lip_sync_mode = 'none'
      let image_animation_type: string | null = null

      if (mode === 'digital_human') {
        lip_sync_enabled = 1; lip_sync_mode = 'digital_human'
      } else if (mode === 'lip_sync_pip') {
        lip_sync_enabled = 1; lip_sync_mode = 'pip'
      } else if (mode === 'lip_sync_full') {
        lip_sync_enabled = 1; lip_sync_mode = 'full'
      } else if (mode === 'auto_align') {
        lip_sync_enabled = 1; lip_sync_mode = 'auto_align'
      } else if (mode === 'virtual_host') {
        lip_sync_enabled = 1; lip_sync_mode = 'virtual_host'
      } else if (mode === 'audio_only') {
        lip_sync_enabled = 1; lip_sync_mode = 'audio_only'
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
        bgm_volume: 0.3,
      })
      message.success('项目创建成功')
      setModalOpen(false)
      setWizardStep(0)
      setUploadedMaterials([])
      form.resetFields()
      loadData()
    } catch (e: any) {
      if (e?.errorFields) {
        message.warning('请完善：' + e.errorFields.map((f: any) => f.name.join('/')).join('、'))
      } else if (e?.message) {
        message.error('创建失败：' + e.message)
      } else {
        message.error('创建失败，请检查必填项')
      }
    }
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
        description="建议优先上传自己的实拍照片/视频素材，出来的视频才是独一无二的。系统搜图匹配只是备用方案，不一定精准适配你的内容。支持Ken Burns镜头动画、交叉淡化转场。露脸可选'自动对齐'或'对口型'模式，不露脸选'图文解说'。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Table
        columns={columns}
        dataSource={projects}
        rowKey="id"
        locale={{ emptyText: <Empty description="暂无视频项目，点击右上角新建" /> }}
      />

            <Modal
        title="新建视频项目"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setWizardStep(0) }}
        footer={null}
        width={600}
      >
        <Steps current={wizardStep} size="small" style={{ marginBottom: 24 }}
          items={[{ title: "基础信息" }, { title: "文案配音" }, { title: "视频模式" }, { title: "上传素材" }]} />

        <Form form={form} layout="vertical">
          {wizardStep === 0 && (
            <>
              <Form.Item name="title" label="项目名称" rules={[{ required: true, message: "请输入" }]}>
                <Input placeholder="如：明清历史解说第一期" size="large" />
              </Form.Item>
              <Form.Item name="aspect_ratio" label="画面比例" initialValue="9:16">
                <Select options={[
                  { label: "9:16 竖版（手机全屏）", value: "9:16" },
                  { label: "16:9 横版（电脑电视）", value: "16:9" },
                  { label: "1:1 方形", value: "1:1" },
                ]} />
              </Form.Item>
            </>
          )}

          {wizardStep === 1 && (
            <>
              <Form.Item name="script_id" label="解说文案" rules={[{ required: true, message: "请选择" }]}>
                {scripts.length === 0 ? (
                  <div style={{ padding: 16, background: "rgba(245,158,11,0.1)", borderRadius: 8, fontSize: 13, color: "#fbbf24" }}>
                    还没有文案。请先去 <a href="/content" style={{ color: "#60a5fa" }}>内容改写</a> 创作或导入文案。
                  </div>
                ) : (
                  <Select placeholder="选择已改写好的文案" size="large"
                    options={scripts.map((s) => ({ label: (s.rewritten_text || s.original_text).slice(0, 60) + "...", value: s.id }))} />
                )}
              </Form.Item>
              <Form.Item name="voice_id" label="配音">
                <Select placeholder="选个声音" allowClear size="large"
                  options={voices.map((v) => ({ label: v.name, value: v.id }))} />
              </Form.Item>
              <Form.Item name="subtitle_enabled" label="自动生成字幕" initialValue={true} valuePropName="checked">
                <Switch />
              </Form.Item>
            </>
          )}

          {wizardStep === 2 && (
            <>
              <Form.Item name="video_mode" label="你想做什么样的视频？" initialValue="image_animation">
                <Select size="large" options={[
                  { label: "🖼️ 图文解说（图片+镜头动画，不露脸）", value: "image_animation" },
                  { label: "🎤 露脸口播（自拍视频自动调速对齐，免费）", value: "auto_align" },
                  { label: "🤖 AI虚拟主播（一张照片→呼吸感微动，免费）", value: "virtual_host" },
                  { label: "⏹️ 静态素材（无特效）", value: "none" },
                  { label: "── 以下需要GPU ──", value: "", disabled: true },
                  { label: "🗣️ 数字人（一张照片→开口说话）", value: "digital_human" },
                  { label: "🎥 画中画口播（自拍视频缩小到角落）", value: "lip_sync_pip" },
                  { label: "🎬 全屏口播（自拍视频铺满全屏）", value: "lip_sync_full" },
                ]} />
              </Form.Item>
              <Form.Item noStyle shouldUpdate={(prev, cur) => prev.video_mode !== cur.video_mode}>
                {({ getFieldValue }) => {
                  const mode = getFieldValue("video_mode")
                  if (mode === "image_animation") {
                    return <Form.Item name="animation_sub_type" label="镜头效果" initialValue="zoom_in">
                      <Select options={[
                        { label: "缓慢放大", value: "zoom_in" }, { label: "缓慢缩小", value: "zoom_out" },
                        { label: "左移", value: "pan_left" }, { label: "右移", value: "pan_right" },
                        { label: "上移", value: "pan_up" }, { label: "下移", value: "pan_down" },
                      ]} />
                    </Form.Item>
                  }
                  return null
                }}
              </Form.Item>
            </>
          )}

          {wizardStep === 3 && (
            <Card size="small" title="上传素材（建议）" style={{ borderRadius: 12 }}>
              <div style={{ fontSize: 12, color: "#fbbf24", marginBottom: 8 }}>
                上传你自己的实拍照片/视频，视频才有专属风格。不传则自动搜图。
              </div>
              <Upload multiple accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.mov,.avi,.webm,.mkv"
                action={(file: any) => "/api/upload/file?file_type=" + (file.name.match(/\.(mp4|mov|avi|webm|mkv)$/i) ? "videos" : "images")}
                onChange={(info: any) => {
                  if (info.file.status === "done") {
                    const resp = info.file.response
                    if (resp?.code === 0) {
                      setUploadedMaterials(prev => prev.includes(resp.data.path) ? prev : [...prev, resp.data.path])
                      message.success(info.file.name + " 上传成功")
                    } else { message.error(info.file.name + " 失败") }
                  }
                }}>
                <Button icon={<InboxOutlined />}>选择文件</Button>
              </Upload>
              {uploadedMaterials.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 12, color: "#94a3b8" }}>
                  已选 {uploadedMaterials.length} 个文件
                </div>
              )}
            </Card>
          )}
        </Form>

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
          <Button onClick={() => { if (wizardStep === 0) { setModalOpen(false); setWizardStep(0) } else setWizardStep(wizardStep - 1) }}>
            {wizardStep === 0 ? "取消" : "上一步"}
          </Button>
          {wizardStep < 3 ? (
            <Button type="primary" onClick={async () => {
              if (wizardStep === 0) { try { await form.validateFields(["title"]) } catch { return } }
              else if (wizardStep === 1) { try { await form.validateFields(["script_id"]) } catch { return } }
              setWizardStep(wizardStep + 1)
            }}>下一步</Button>
          ) : (
            <Button type="primary" onClick={handleCreate}>创建项目</Button>
          )}
        </div>
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
