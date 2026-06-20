import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Table, Tag, Button, Modal, Form, Input, Select, message, Switch, Progress, Empty, Alert, Card, Upload, Image, Popconfirm, Steps, Space, Dropdown } from 'antd'
import {
  VideoCameraOutlined, PlusOutlined, PlayCircleOutlined, DeleteOutlined,
  ThunderboltOutlined, InboxOutlined, HeartOutlined, HeartFilled,
  EllipsisOutlined, EditOutlined,
} from '@ant-design/icons'
import { videoApi, contentApi, voiceApi, uploadApi, taskApi } from '../services/api'
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
  const [editingId, setEditingId] = useState<number | null>(null)  // 编辑中的项目ID，null=新建
  const [uploadedMaterials, setUploadedMaterials] = useState<string[]>([])
  const [uploadFileList, setUploadFileList] = useState<any[]>([])
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [libraryFiles, setLibraryFiles] = useState<any[]>([])
  const [selectedLib, setSelectedLib] = useState<string[]>([])
  const [form] = Form.useForm()
  const [wizardStep, setWizardStep] = useState(0)
  const [generatingTasks, setGeneratingTasks] = useState<Record<number, { taskId: number; progress: number; message: string }>>({})

  // 上传组件 — input 覆盖式，避开 Modal 拦截
  const MaterialUploader = ({ onUpload, materials }: { onUpload: any, materials: any, acceptVideo?: boolean }) => {
    const [busy, setBusy] = useState(false)

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (!files || files.length === 0) return
      setBusy(true)
      const file = files[0]
      const fd = new FormData()
      fd.append('file', file)
      const ft = /\.(mp4|mov|avi|webm|mkv)$/i.test(file.name) ? 'videos' : 'images'
      fetch(`/api/upload/file?file_type=${ft}`, { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
          if (data.code === 0 && data.data?.path) {
            onUpload((prev: string[]) => prev.includes(data.data.path) ? prev : [...prev, data.data.path])
            message.success(`${file.name} 上传成功`)
          } else {
            message.error(`${file.name}：${data.message || '失败'}`)
          }
        })
        .catch(() => message.error(`${file.name}：网络错误`))
        .finally(() => {
          setBusy(false)
          const el = document.getElementById('_mp_upload') as HTMLInputElement
          if (el) el.value = ''
        })
    }

    return (
      <div style={{ position: 'relative', marginBottom: 8 }}>
        <div style={{
          padding: '12px 16px', border: '2px dashed rgba(148,163,184,0.25)', borderRadius: 8,
          textAlign: 'center', color: busy ? '#3b82f6' : '#94a3b8', fontSize: 14,
          background: busy ? 'rgba(59,130,246,0.05)' : 'transparent',
          pointerEvents: 'none',
        }}>
          {busy ? '上传中...' : materials.length > 0 ? `已上传 ${materials.length} 个文件，点此继续添加` : '点击添加图片或视频素材'}
        </div>
        <input
          id="_mp_upload"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,.mp4,.mov,.avi,.webm,.mkv"
          onChange={handleChange}
          style={{
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
            opacity: 0, cursor: 'pointer', zIndex: 10,
          }}
        />
        {materials.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {materials.map((path: string, i: number) => {
              const name = path.split('/').pop() || path
              return (
                <Tag key={i} closable onClose={() => onUpload((prev: string[]) => prev.filter((p) => p !== path))}
                  style={{ marginBottom: 4 }}>
                  {name.length > 20 ? name.slice(0, 18) + '...' : name}
                </Tag>
              )
            })}
          </div>
        )}
      </div>
    )
  }

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
      const values = form.getFieldsValue()
      if (!values.title) { message.warning('请输入项目名称'); return }
      if (!values.script_id) { message.warning('请选择文案'); return }

      const payload = {
        title: values.title,
        script_id: values.script_id,
        voice_id: values.voice_id || 1,
        material_paths_json: JSON.stringify(uploadedMaterials),
      }

      if (editingId) {
        // 编辑已有项目
        await videoApi.update(editingId, payload)
        message.success('项目已更新，正在重新生成视频...')
        setModalOpen(false)
        setEditingId(null)
        setUploadedMaterials([])
        form.resetFields()
        handleGenerate(editingId)
      } else {
        // 新建项目
        const result = await videoApi.create({ ...payload, aspect_ratio: '9:16', subtitle_enabled: 1, lip_sync_enabled: 0, lip_sync_mode: 'none', image_animation_type: 'zoom_in', bgm_volume: 0.3 })
        if (!result || !result.id) { message.error('创建失败'); return }
        message.success('项目创建成功，正在生成视频...')
        setModalOpen(false)
        handleGenerate(result.id)
        setUploadedMaterials([])
        form.resetFields()
      }
      loadData()
    } catch (e: any) {
      if (e?.errorFields) {
        message.warning('请完善：' + e.errorFields.map((f: any) => f.name.join('/')).join('、'))
      } else if (e?.message) {
        message.error('操作失败：' + e.message)
      } else {
        message.error('操作失败，请检查必填项')
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
      const taskId = res.data?.task_id
      if (taskId) {
        setGeneratingTasks((prev) => ({ ...prev, [id]: { taskId, progress: 0, message: '排队中...' } }))
      }
      message.success('任务已提交，后台生成中')
      loadData()
    } catch (e: any) {
      message.error('提交失败：' + (e?.message || '未知错误'))
    }
  }

  // 轮询正在生成的任务进度
  useEffect(() => {
    const taskEntries = Object.entries(generatingTasks)
    if (taskEntries.length === 0) return
    const timer = setInterval(async () => {
      let changed = false
      const updated = { ...generatingTasks }
      for (const [pid, task] of taskEntries) {
        try {
          const t: any = await taskApi.detail(task.taskId)
          if (t.status === 'completed') {
            delete updated[Number(pid)]
            changed = true
            message.success(`项目 #${pid} 视频生成完成`)
            loadData()
          } else if (t.status === 'failed') {
            delete updated[Number(pid)]
            changed = true
            message.error(`项目 #${pid} 生成失败：${t.progress_message || '未知错误'}`)
            loadData()
          } else {
            if (t.progress !== task.progress || t.progress_message !== task.message) {
              updated[Number(pid)] = { taskId: task.taskId, progress: t.progress || 0, message: t.progress_message || '' }
              changed = true
            }
          }
        } catch { /* 忽略单次轮询失败 */ }
      }
      if (changed) setGeneratingTasks({ ...updated })
    }, 2000)
    return () => clearInterval(timer)
  }, [generatingTasks])

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
      render: (s: string, record: VideoProject) => {
        const m = statusMap[s] || { color: 'default', label: s }
        const task = generatingTasks[record.id]
        if (task) {
          return (
            <div style={{ minWidth: 140 }}>
              <Tag color="processing">生成中</Tag>
              <Progress percent={task.progress} size="small" style={{ marginTop: 2 }} />
              <div style={{ fontSize: 10, color: '#94a3b8' }}>{task.message}</div>
            </div>
          )
        }
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
        <Space size={4} wrap>
          {record.status === 'draft' && (
            <Button size="small" type="primary" icon={<ThunderboltOutlined />} onClick={() => handleGenerate(record.id)}>
              生成
            </Button>
          )}
          {record.status === 'completed' && record.output_path && (
            <Button size="small" type="primary" ghost onClick={() => window.open(`/api/video/projects/${record.id}/output`, '_blank')}>
              播放
            </Button>
          )}
          <Dropdown menu={{ items: [
            { key: 'edit', icon: <EditOutlined />, label: '编辑', onClick: () => {
              setEditingId(record.id)
              form.setFieldsValue({ title: record.title, script_id: record.script_id, voice_id: record.voice_id })
              try {
                const mats = JSON.parse(record.material_paths_json || '[]')
                setUploadedMaterials(Array.isArray(mats) ? mats : [])
              } catch { setUploadedMaterials([]) }
              setModalOpen(true)
            }},
            ...(record.status === 'completed' ? [{ key: 'collect', icon: record.collected ? <HeartFilled style={{color:'#eb2f96'}}/> : <HeartOutlined />, label: record.collected ? '取消收藏' : '收藏', onClick: () => handleCollect(record.id, record.collected) }] : []),
            { key: 'del', icon: <DeleteOutlined />, label: '删除', danger: true, onClick: () => {
              Modal.confirm({ title: '确认删除？', content: `删除项目「${record.title}」后不可恢复`, okText: '删除', okType: 'danger', cancelText: '取消', onOk: () => handleDelete(record.id) })
            }},
          ]}}>
            <Button size="small" icon={<EllipsisOutlined />}>更多</Button>
          </Dropdown>
        </Space>
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
          setEditingId(null); form.resetFields(); setModalOpen(true)
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
        title={editingId ? `编辑项目 #${editingId}` : '新建视频项目'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null); form.resetFields() }}
        footer={null}
        width={window.innerWidth < 600 ? '95%' : 520}
        style={{ top: 20 }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="项目名称" rules={[{ required: true, message: "请输入" }]}>
            <Input placeholder="如：ENF衣柜产品展示" size="large" />
          </Form.Item>
          <Form.Item name="script_id" label="解说文案" rules={[{ required: true, message: "请选择" }]}>
            {scripts.length === 0 ? (
              <div style={{ padding: 12, background: "rgba(245,158,11,0.1)", borderRadius: 8, fontSize: 13, color: "#fbbf24" }}>
                还没有文案，请先去 <a href="/template" style={{ color: "#60a5fa" }}>文案模板</a> 生成一条
              </div>
            ) : (
              <Select placeholder="选择已生成的文案" size="large"
                options={scripts.map((s) => ({ label: (s.rewritten_text || s.original_text).slice(0, 60) + "...", value: s.id }))} />
            )}
          </Form.Item>
          <Form.Item name="voice_id" label="配音（可选，默认自动选择）">
            <Select placeholder="选个声音" allowClear size="large"
              options={voices.map((v) => ({ label: v.name, value: v.id }))} />
          </Form.Item>
          <div style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 8, fontSize: 14, fontWeight: 500, color: '#e2e8f0' }}>📸 素材（可选）</div>
            <div style={{ marginBottom: 8, fontSize: 12, color: '#60a5fa', background: 'rgba(96,165,250,0.1)', padding: '6px 10px', borderRadius: 6 }}>
              ⚡ 不上传也行，系统会自动匹配工厂实拍、产品展示等素材
            </div>
            <Button icon={<InboxOutlined />} onClick={() => {
              // 动态创建 file input，绕过 Modal 拦截
              const input = document.createElement('input')
              input.type = 'file'
              input.multiple = true
              input.accept = '.jpg,.jpeg,.png,.gif,.webp,.bmp,.mp4,.mov,.avi,.webm,.mkv'
              input.onchange = (e: any) => {
                const files = e.target.files
                if (!files || files.length === 0) return
                Array.from(files).forEach((file: any) => {
                  const ft = /\.(mp4|mov|avi|webm|mkv)$/i.test(file.name) ? 'videos' : 'images'
                  const fd = new FormData()
                  fd.append('file', file)
                  fetch('/api/upload/file?file_type=' + ft, { method: 'POST', body: fd })
                    .then(r => r.json())
                    .then(data => {
                      if (data.code === 0 && data.data?.path) {
                        setUploadedMaterials((prev: string[]) => prev.includes(data.data.path) ? prev : [...prev, data.data.path])
                        message.success(`${file.name} 上传成功`)
                      } else {
                        message.error(`${file.name}：${data.message || '失败'}`)
                      }
                    })
                    .catch(() => message.error(`${file.name}：网络错误`))
                })
              }
              input.click()
            }}>
              选择文件上传
            </Button>
            <span style={{ fontSize: 12, color: '#94a3b8', marginLeft: 8 }}>
              支持 JPG/PNG/GIF/WebP/MP4/MOV
            </span>
            {uploadedMaterials.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <Space size={4} wrap>
                  {uploadedMaterials.map((path: string, i: number) => (
                    <Tag key={i} closable onClose={() => setUploadedMaterials((p: string[]) => p.filter(x => x !== path))}
                      style={{ marginBottom: 4 }}>
                      {path.split('/').pop()?.slice(0, 20) || path}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
          </div>
          <Button type="primary" size="large" block icon={<ThunderboltOutlined />}
            onClick={handleCreate} style={{ borderRadius: 10 }}>
            {editingId ? '保存并重新生成' : '创建并生成视频'}
          </Button>
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
