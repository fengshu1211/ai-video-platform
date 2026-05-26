import { useEffect, useState, useMemo } from 'react'
import { Button, Image, message, Popconfirm, Upload, Card, Empty, Input, Tabs, Checkbox, Space, Segmented, Badge } from 'antd'
import {
  InboxOutlined, DeleteOutlined, PictureOutlined, SearchOutlined,
  DownloadOutlined, PlayCircleOutlined, AppstoreOutlined, UnorderedListOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { uploadApi } from '../services/api'

const CATEGORIES = ['全部', '人物', '产品', '场景', '素材', '未分类']

const PRESET_CATEGORIES = ['历史', '家居', '美食', '科技']

export default function MaterialLibraryPage() {
  const [files, setFiles] = useState<any[]>([])
  const [presets, setPresets] = useState<Record<string, any[]>>({})
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [activeCat, setActiveCat] = useState('全部')
  const [selected, setSelected] = useState<string[]>([])
  const [viewMode, setViewMode] = useState<string>('grid')
  const [tab, setTab] = useState<string>('mine')
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiFiles, setAiFiles] = useState<any[]>([])

  const loadFiles = async () => {
    setLoading(true)
    try {
      const res: any = await uploadApi.listFiles()
      setFiles(Array.isArray(res?.data) ? res.data : (res || []))
      // Load presets
      const pRes = await fetch('/api/materials/presets').then(r => r.json())
      setPresets(pRes?.presets || {})
    } catch { message.error('加载失败') } finally { setLoading(false) }
  }

  useEffect(() => { loadFiles() }, [])

  const handleAiGenerate = async (batch: boolean = false) => {
    const user = JSON.parse(localStorage.getItem('current_user') || '{}')
    if (!user.userId) { message.warning('请先登录'); return }
    setAiGenerating(true)
    const endpoint = batch ? 'pre-generate' : 'generate-recommended'
    try {
      const res = await fetch(`/api/materials/${endpoint}?user_id=${user.userId}`, { method: 'POST' })
      const data = await res.json()
      if (data.code === 0) {
        message.success(data.message)
        setAiFiles(data.files || [])
        loadFiles()
      } else {
        message.warning(data.message || '生成失败')
      }
    } catch { message.error('网络错误') }
    setAiGenerating(false)
  }

  const handleDelete = async (path: string) => {
    try { await uploadApi.deleteFile(path); message.success('已删除'); loadFiles() } catch { message.error('删除失败') }
  }

  const batchDelete = async () => {
    for (const p of selected) { try { await uploadApi.deleteFile(p) } catch {} }
    message.success('批量删除完成'); loadFiles(); setSelected([])
  }

  const isImage = (name: string) =>
    ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].some(e => name.toLowerCase().endsWith(e))

  const classify = (name: string) => {
    const n = name.toLowerCase()
    if (n.includes('人') || n.includes('脸') || n.includes('自拍')) return '人物'
    if (n.includes('产品') || n.includes('板材') || n.includes('柜')) return '产品'
    if (n.includes('场景') || n.includes('工地') || n.includes('工厂')) return '场景'
    if (n.includes('素材') || n.includes('背景')) return '素材'
    return '未分类'
  }

  const filtered = useMemo(() => {
    let f = files
    if (search) f = f.filter(x => x.name.toLowerCase().includes(search.toLowerCase()))
    if (activeCat !== '全部') f = f.filter(x => classify(x.name) === activeCat)
    return f
  }, [files, search, activeCat])

  const catCounts = useMemo(() => {
    const c: Record<string, number> = { '全部': files.length }
    files.forEach(f => { const cat = classify(f.name); c[cat] = (c[cat] || 0) + 1 })
    return c
  }, [files])

  const renderCard = (item: any, isPreset: boolean) => (
    <Card key={isPreset ? item.path : item.path} size="small"
      style={viewMode === 'grid' ? { width: 200, borderRadius: 10, overflow: 'hidden' } : { borderRadius: 8 }}
      cover={viewMode === 'grid' && (isImage(item.name)
        ? <Image src={`/uploads/${item.path}`} style={{ height: 130, objectFit: 'cover' }} preview={!!item.path} fallback=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='130'%3E%3Crect fill='%231a1a2e' width='200' height='130'/%3E%3Ctext fill='%23999' x='100' y='70' text-anchor='middle' font-size='14'%3E{item.name}%3C/text%3E%3C/svg%3E\" />
        : <div style={{ height: 130, background: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <PlayCircleOutlined style={{ fontSize: 36, color: '#999' }} />
        </div>)}
      actions={isPreset ? [] : [
        <Checkbox key=\"sel\" checked={selected.includes(item.path)} onChange={e => {
          setSelected(e.target.checked ? [...selected, item.path] : selected.filter(x => x !== item.path))
        }} />,
        <Button key=\"dl\" size=\"small\" type=\"link\" icon={<DownloadOutlined />}
          onClick={() => window.open(`/uploads/${item.path}`, '_blank')} />,
        <Popconfirm key=\"del\" title=\"确定删除？\" onConfirm={() => handleDelete(item.path)}>
          <Button size=\"small\" danger icon={<DeleteOutlined />} /></Popconfirm>,
      ]}>
      <Card.Meta
        title={<div style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</div>}
        description={isPreset
          ? <Badge color=\"blue\" text=\"预置\" />
          : <span>{Math.round((item.size || 0) / 1024)}KB · <Badge color=\"blue\" style={{ fontSize: 10 }} text={classify(item.name)} /></span>}
      />
    </Card>
  )

  const renderList = (items: any[], isPreset: boolean) => (
    viewMode === 'grid'
      ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>{items.map(item => renderCard(item, isPreset))}</div>
      : <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map(item => (
          <Card key={item.path} size=\"small\" style={{ borderRadius: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {!isPreset && <Checkbox checked={selected.includes(item.path)} onChange={e => {
                setSelected(e.target.checked ? [...selected, item.path] : selected.filter(x => x !== item.path))
              }} />}
              <div style={{ width: 40, height: 40, borderRadius: 6, overflow: 'hidden', flexShrink: 0, background: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {isImage(item.name)
                  ? <Image src={`/uploads/${item.path}`} style={{ width: 40, height: 40, objectFit: 'cover' }} preview={false} />
                  : <PlayCircleOutlined style={{ fontSize: 18, color: '#999' }} />}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13 }}>{item.name}</div>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>
                  {isPreset ? <Badge color=\"blue\" text=\"预置\" /> : `${Math.round((item.size || 0) / 1024)}KB · ${classify(item.name)}`}
                </div>
              </div>
              {!isPreset && <Space size=\"small\">
                <Button size=\"small\" type=\"link\" icon={<DownloadOutlined />} onClick={() => window.open(`/uploads/${item.path}`, '_blank')} />
                <Popconfirm title=\"确定删除？\" onConfirm={() => handleDelete(item.path)}>
                  <Button size=\"small\" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>}
            </div>
          </Card>
        ))}
      </div>
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0 }}><PictureOutlined style={{ color: '#722ed1', marginRight: 8 }} />素材库</h2>
        <Space>
          <Upload multiple accept=\".jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.mov,.avi,.webm,.mkv\"
            action={(file: any) => `/api/upload/file?file_type=${isImage(file.name) ? 'images' : 'videos'}`}
            onChange={(info: any) => {
              if (info.file.status === 'done') { message.success(`${info.file.name} 上传成功`); loadFiles() }
              else if (info.file.status === 'error') message.error(`${info.file.name} 上传失败`)
            }}>
            <Button type=\"primary\" icon={<InboxOutlined />}>上传我的素材</Button>
          <Button icon={<ThunderboltOutlined />} loading={aiGenerating} onClick={() => handleAiGenerate(false)} style={{ borderColor: '#f59e0b', color: '#f59e0b' }}>
            AI推荐(3张)
          </Button>
          <Button icon={<ThunderboltOutlined />} loading={aiGenerating} onClick={() => handleAiGenerate(true)} style={{ borderColor: '#10b981', color: '#10b981' }}>
            批量预生成(10张)
          </Button>
          </Upload>
          {selected.length > 0 && (
            <Popconfirm title={`确定删除选中的${selected.length}个文件？`} onConfirm={batchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除选中({selected.length})</Button>
            </Popconfirm>
          )}
          <Segmented size=\"small\" value={viewMode} onChange={v => setViewMode(v as string)}
            options={[{ label: '网格', value: 'grid', icon: <AppstoreOutlined /> }, { label: '列表', value: 'list', icon: <UnorderedListOutlined /> }]} />
        </Space>
      </div>

      <Tabs activeKey={tab} onChange={setTab} items={[
        { key: 'mine', label: `我的素材 (${files.length})` },
        { key: 'presets', label: '预置参考' },
      ]} style={{ marginBottom: 0 }} />

      {tab === 'mine' && (
        <>
          <div style={{ display: 'flex', gap: 8, margin: '12px 0', flexWrap: 'wrap' }}>
            <Input prefix={<SearchOutlined />} placeholder=\"搜索文件名...\" value={search}
              onChange={e => setSearch(e.target.value)} style={{ width: 200, borderRadius: 8 }} allowClear size=\"small\" />
            <Tabs activeKey={activeCat} onChange={setActiveCat} size=\"small\" style={{ flex: 1 }}
              items={CATEGORIES.map(c => ({ key: c, label: `${c} ${catCounts[c] || 0}` }))} />
          </div>
          {filtered.length === 0 ? <Empty description={search ? '无匹配文件' : '暂无素材，点击右上角上传'} /> : renderList(filtered, false)}
        </>
      )}

      {tab === 'presets' && (
        <div style={{ marginTop: 12 }}>
          {Object.keys(presets).length === 0 && <Empty description=\"暂无预置素材\" />}
          {PRESET_CATEGORIES.map(cat => presets[cat]?.length > 0 && (
            <div key={cat} style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>📁 {cat}</div>
              {renderList(presets[cat].map((p: any) => ({ ...p, name: p.filename || p.name })), true)}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
