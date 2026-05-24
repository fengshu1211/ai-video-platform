import { useEffect, useState } from 'react'
import { Button, Image, message, Popconfirm, Upload, Card, Empty } from 'antd'
import { InboxOutlined, DeleteOutlined, PictureOutlined } from '@ant-design/icons'
import { uploadApi } from '../services/api'

export default function MaterialLibraryPage() {
  const [files, setFiles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const loadFiles = async () => {
    setLoading(true)
    try {
      const res: any = await uploadApi.listFiles()
      const list = Array.isArray(res) ? res : (res.data || [])
      setFiles(list)
    } catch {
      message.error('加载素材库失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadFiles() }, [])

  const handleDelete = async (path: string) => {
    try {
      await uploadApi.deleteFile(path)
      message.success('已删除')
      setFiles((p) => p.filter((f) => f.path !== path))
    } catch {
      message.error('删除失败')
    }
  }

  const isImage = (name: string) =>
    ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].some((ext) => name.toLowerCase().endsWith(ext))

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2><PictureOutlined style={{ color: '#722ed1', marginRight: 8 }} />素材库</h2>
        <Upload
          multiple
          accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.mov,.avi,.webm,.mkv"
          action={(file: any) => {
            const isImg = isImage(file.name)
            return `/api/upload/file?file_type=${isImg ? 'images' : 'videos'}`
          }}
          onChange={(info: any) => {
            if (info.file.status === 'done') {
              const resp = info.file.response
              if (resp?.code !== 0) {
                message.error(`${info.file.name} 上传失败：${resp?.message || '未知错误'}`)
                return
              }
              message.success(`${info.file.name} 上传成功`)
              loadFiles()
            } else if (info.file.status === 'error') {
              message.error(`${info.file.name} 上传失败`)
            }
          }}
        >
          <Button type="primary" icon={<InboxOutlined />}>上传素材</Button>
        </Upload>
      </div>

      {files.length === 0 && !loading && (
        <Empty description="暂无素材，点击右上角上传" />
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        {files.map((f) => (
          <Card
            key={f.path}
            size="small"
            style={{ width: 220 }}
            cover={
              isImage(f.name)
                ? <Image src={`/uploads/${f.path}`} style={{ height: 140, objectFit: 'cover' }} />
                : <div style={{ height: 140, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <video src={`/uploads/${f.path}`} controls preload="metadata" style={{ height: 140, maxWidth: '100%', objectFit: 'cover' }} />
                  </div>
            }
            actions={[
              <Popconfirm title="确定删除？" onConfirm={() => handleDelete(f.path)}>
                <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>,
            ]}
          >
            <Card.Meta
              title={<div style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</div>}
              description={`${(f.size / 1024).toFixed(0)} KB · ${f.type === 'image' ? '图片' : '视频'}`}
            />
          </Card>
        ))}
      </div>
    </div>
  )
}
