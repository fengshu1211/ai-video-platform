import { useEffect, useState, useMemo } from 'react'
import { Button, Image, message, Popconfirm, Upload, Card, Empty, Input, Tabs, Checkbox, Space, Select, Badge } from 'antd'
import { InboxOutlined, DeleteOutlined, PictureOutlined, SearchOutlined, DownloadOutlined } from '@ant-design/icons'
import { uploadApi } from '../services/api'

const CATEGORIES = ['全部', '人物', '产品', '场景', '素材', '未分类']

export default function MaterialLibraryPage() {
  const [files, setFiles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [activeCat, setActiveCat] = useState('全部')
  const [selected, setSelected] = useState<string[]>([])
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  const loadFiles = async () => {
    setLoading(true)
    try {
      const res: any = await uploadApi.listFiles()
      const list = Array.isArray(res) ? res : (res.data || [])
      setFiles(list)
    } catch { message.error('加载素材库失败') } finally { setLoading(false) }
  }

  useEffect(() => { loadFiles() }, [])

  const handleDelete = async (path: string) => {
    try { await uploadApi.deleteFile(path); message.success('已删除'); setFiles(p => p.filter(f => f.path !== path)) } catch { message.error('删除失败') }
  }

  const batchDelete = async () => {
    for (const path of selected) { try { await uploadApi.deleteFile(path) } catch {} }
    message.success('批量删除完成')
    setFiles(p => p.filter(f => !selected.includes(f.path)))
    setSelected([])
  }

  const isImage = (name: string) =>
    ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].some(ext => name.toLowerCase().endsWith(ext))

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
    const counts: Record<string, number> = { '全部': files.length }
    files.forEach(f => { const c = classify(f.name); counts[c] = (counts[c] || 0) + 1 })
    return counts
  }, [files])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0 }}><PictureOutlined style={{ color: '#722ed1', marginRight: 8 }} />素材库</h2>
        <Space>
          <Upload multiple accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.mov,.avi,.webm,.mkv"
            action={(file: any) => `/api/upload/file?file_type=${isImage(file.name) ? 'images' : 'videos'}`}
            onChange={(info: any) => {
              if (info.file.status === 'done') { message.success(`${info.file.name} 上传成功`); loadFiles() }
              else if (info.file.status === 'error') message.error(`${info.file.name} 上传失败`)
            }}>
            <Button type="primary" icon={<InboxOutlined />}>上传素材</Button>
          </Upload>
          {selected.length > 0 && (
            <Popconfirm title={`确定删除选中的${selected.length}个文件？`} onConfirm={batchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除选中({selected.length})</Button>
            </Popconfirm>
          )}
          <Select size="small" value={viewMode} onChange={setViewMode} style={{ width: 80 }}
            options={[{ label: '网格', value: 'grid' }, { label: '列表', value: 'list' }]} />
        </Space>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <Input prefix={<SearchOutlined />} placeholder="搜索文件名..." value={search} onChange={e => setSearch(e.target.value)}
          style={{ width: 220, borderRadius: 8 }} allowClear size="small" />
        <Tabs activeKey={activeCat} onChange={setActiveCat} size="small" style={{ flex: 1 }}
          items={CATEGORIES.map(c => ({
            key: c, label: <Badge count={catCounts[c] || 0} offset={[8, -2]} size="small" style={{ zIndex: 0 }}>
              <span style={{ paddingRight: 8 }}>{c}</span>
            </Badge>
          }))} />
      </div>

      {files.length === 0 && !loading && <Empty description="暂无素材，点击右上角上传" />}

      <div style={viewMode === 'grid'
        ? { display: 'flex', flexWrap: 'wrap', gap: 12 }
        : { display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filtered.map(f => (
          viewMode === 'grid' ? (
            <Card key={f.path} size="small" style={{ width: 200, borderRadius: 10, overflow: 'hidden' }}
              cover={isImage(f.name)
                ? <Image src={`/uploads/${f.path}`} style={{ height: 130, objectFit: 'cover' }} />
                : <div style={{ height: 130, background: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <video src={`/uploads/${f.path}`} controls preload="metadata" style={{ height: 130, maxWidth: '100%', objectFit: 'cover' }} />
                </div>}
              actions={[
                <Checkbox checked={selected.includes(f.path)} key="sel" onChange={e => {
                  setSelected(e.target.checked ? [...selected, f.path] : selected.filter(x => x !== f.path))
                }} />,
                <Button size="small" key="dl" type="link" icon={<DownloadOutlined />} href={`/uploads/${f.path}`} target="_blank" />,
                <Popconfirm key="del" title="确定删除？" onConfirm={() => handleDelete(f.path)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>,
              ]}>
              <Card.Meta title={<div style={{ fontSize: 12 }}>{f.name.slice(0, 20)}</div>}
                description={<span>{Math.round(f.size / 1024)}KB · <Badge color="blue" style={{ fontSize: 10 }} text={classify(f.name)} /></span>} />
            </Card>
          ) : (
            <Card key={f.path} size="small" style={{ borderRadius: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Checkbox checked={selected.includes(f.path)} onChange={e => {
                  setSelected(e.target.checked ? [...selected, f.path] : selected.filter(x => x !== f.path))
                }} />
                <div style={{ width: 40, height: 40, borderRadius: 6, overflow: 'hidden', flexShrink: 0, background: '#1a1a2e' }}>
                  {isImage(f.name) ? <Image src={`/uploads/${f.path}`} style={{ width: 40, height: 40, objectFit: 'cover' }} preview={false} />
                    : <PlayCircleOutlined style={{ fontSize: 20, margin: 10 }} />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>{Math.round(f.size / 1024)}KB · <Badge color="blue" style={{ fontSize: 10 }} text={classify(f.name)} /></div>
                </div>
                <Space size="small">
                  <Button size="small" type="link" icon={<DownloadOutlined />} href={`/uploads/${f.path}`} target="_blank" />
                  <Popconfirm title="确定删除？" onConfirm={() => handleDelete(f.path)}>
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              </div>
            </Card>
          )
        ))}
      </div>
    </div>
  )
}
