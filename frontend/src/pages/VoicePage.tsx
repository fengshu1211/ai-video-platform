import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Tag, Button, Spin, Empty, message, Upload, Modal, Input, Select } from 'antd'
import {
  SoundOutlined, PlayCircleOutlined, PauseCircleOutlined,
  ManOutlined, WomanOutlined, RobotOutlined, UploadOutlined,
  PlusOutlined, EditOutlined, DeleteOutlined, VideoCameraOutlined,
} from '@ant-design/icons'
import { voiceApi } from '../services/api'
import type { VoiceProfile } from '../types/voice'

const genderOptions = [
  { label: '男声', value: 'male' },
  { label: '女声', value: 'female' },
  { label: '特殊音色', value: 'special' },
]

const genderIcon = (g: string) => {
  if (g === 'male') return <ManOutlined style={{ fontSize: 28, color: '#1677ff' }} />
  if (g === 'female') return <WomanOutlined style={{ fontSize: 28, color: '#eb2f96' }} />
  return <RobotOutlined style={{ fontSize: 28, color: '#fa8c16' }} />
}

export default function VoicePage() {
  const [voices, setVoices] = useState<VoiceProfile[]>([])
  const [loading, setLoading] = useState(false)
  const [playingId, setPlayingId] = useState<number | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // 上传弹窗
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadName, setUploadName] = useState('')
  const [uploadGender, setUploadGender] = useState('male')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  // 编辑弹窗
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editVoice, setEditVoice] = useState<VoiceProfile | null>(null)
  const [editName, setEditName] = useState('')
  const [editGender, setEditGender] = useState('')
  const [editing, setEditing] = useState(false)
  const navigate = useNavigate()

  const loadVoices = () => {
    setLoading(true)
    voiceApi.profiles().then(setVoices).catch(() => message.error('加载语音列表失败')).finally(() => setLoading(false))
  }

  useEffect(() => { loadVoices() }, [])

  const handlePlay = (voiceId: number) => {
    if (playingId === voiceId) {
      audioRef.current?.pause()
      setPlayingId(null)
      return
    }
    const audio = new Audio(`/api/voice/profiles/${voiceId}/preview`)
    audio.onended = () => setPlayingId(null)
    audio.onerror = () => { message.error('播放失败'); setPlayingId(null) }
    audio.play().catch(() => message.error('播放失败'))
    audioRef.current = audio
    setPlayingId(voiceId)
  }

  // ── 上传 ──
  const handleUpload = async () => {
    if (!uploadName.trim()) return message.warning('请输入语音名称')
    if (!uploadFile) return message.warning('请选择音频文件')
    setUploading(true)
    try {
      await voiceApi.uploadCustom(uploadName, uploadGender, uploadFile)
      message.success('上传成功')
      setUploadModalOpen(false)
      setUploadName('')
      setUploadFile(null)
      loadVoices()
    } catch {
      message.error('上传失败')
    } finally {
      setUploading(false)
    }
  }

  // ── 编辑 ──
  const openEdit = (v: VoiceProfile) => {
    setEditVoice(v)
    setEditName(v.name)
    setEditGender(v.gender || 'female')
    setEditModalOpen(true)
  }

  const handleEdit = async () => {
    if (!editVoice) return
    setEditing(true)
    try {
      await voiceApi.update(editVoice.id, { name: editName, gender: editGender })
      message.success('已更新')
      setEditModalOpen(false)
      loadVoices()
    } catch {
      message.error('更新失败')
    } finally {
      setEditing(false)
    }
  }

  // ── 删除 ──
  const handleDelete = async (v: VoiceProfile) => {
    try {
      await voiceApi.delete(v.id)
      message.success('已删除')
      if (playingId === v.id) { audioRef.current?.pause(); setPlayingId(null) }
      loadVoices()
    } catch {
      message.error('删除失败')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2><SoundOutlined style={{ color: '#52c41a', marginRight: 8 }} />语音系统</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setUploadModalOpen(true)}>
          上传自定义语音
        </Button>
      </div>

      <Spin spinning={loading}>
        {voices.length === 0 && !loading ? (
          <Empty description="暂无可用语音" />
        ) : (
          <Row gutter={[16, 16]}>
            {voices.map((v) => (
              <Col span={6} key={v.id}>
                <Card
                  hoverable
                  extra={
                    v.is_custom ? (
                      <div style={{ display: 'flex', gap: 4 }}>
                        <Button size="small" type="text" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); openEdit(v) }} />
                        <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={(e) => { e.stopPropagation(); handleDelete(v) }} />
                      </div>
                    ) : null
                  }
                  actions={[
                    <Button
                      type="link"
                      icon={playingId === v.id ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                      onClick={() => handlePlay(v.id)}
                      key="play"
                    >
                      {playingId === v.id ? '停止' : '试听'}
                    </Button>,
                    <Button type="link" icon={<VideoCameraOutlined />} onClick={() => navigate('/video', { state: { voiceId: v.id } })} key="video">
                      生成视频
                    </Button>,
                  ]}
                >
                  <Card.Meta
                    avatar={genderIcon(v.gender || '')}
                    title={v.name}
                    description={
                      <div>
                        <Tag color={v.is_custom ? 'orange' : 'green'}>{v.is_custom ? '自定义' : '预置'}</Tag>
                        <Tag>{v.gender === 'male' ? '男声' : v.gender === 'female' ? '女声' : v.gender === 'special' ? '特殊' : v.style || v.provider}</Tag>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>

      {/* 上传弹窗 */}
      <Modal
        title="上传自定义语音"
        open={uploadModalOpen}
        onOk={handleUpload}
        onCancel={() => { setUploadModalOpen(false); setUploadFile(null) }}
        confirmLoading={uploading}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Input
            placeholder="语音名称，如：我的声音"
            value={uploadName}
            onChange={(e) => setUploadName(e.target.value)}
          />
          <Select value={uploadGender} onChange={setUploadGender} options={genderOptions} />
          <Upload
            accept=".mp3,.wav,.m4a,.ogg"
            maxCount={1}
            beforeUpload={(file) => { setUploadFile(file); return false }}
            onRemove={() => setUploadFile(null)}
          >
            <Button icon={<UploadOutlined />}>选择音频样本（至少10秒，AI语音复刻）</Button>
          </Upload>
        </div>
      </Modal>

      {/* 编辑弹窗 */}
      <Modal
        title="编辑语音信息"
        open={editModalOpen}
        onOk={handleEdit}
        onCancel={() => setEditModalOpen(false)}
        confirmLoading={editing}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Input
            placeholder="语音名称"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
          />
          <Select value={editGender} onChange={setEditGender} options={genderOptions} />
        </div>
      </Modal>
    </div>
  )
}
