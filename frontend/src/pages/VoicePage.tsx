import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Tag, Button, Spin, Empty, message, Upload, Modal, Input, Select, Tabs } from 'antd'
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

function VoiceRecorder({ onRecorded }: { onRecorded: (blob: Blob) => void }) {
  const [recording, setRecording] = useState(false)
  const [duration, setDuration] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<any>(null)

  const startRecord = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      chunksRef.current = []
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        onRecorded(blob)
        clearInterval(timerRef.current)
      }
      mr.start()
      mediaRecorderRef.current = mr
      setRecording(true)
      setDuration(0)
      timerRef.current = setInterval(() => setDuration(d => d + 1), 1000)
    } catch {
      message.error('无法访问麦克风，请允许浏览器使用麦克风权限')
    }
  }

  const stopRecord = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  return (
    <div style={{ textAlign: 'center', padding: 12 }}>
      {!recording ? (
        <Button type="primary" icon={<PlayCircleOutlined />} onClick={startRecord} style={{ borderRadius: 20 }}>
          开始录音（至少10秒）
        </Button>
      ) : (
        <div>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#ef4444', marginBottom: 8 }}>
            🔴 录音中 {duration}秒
          </div>
          <Button danger icon={<PauseCircleOutlined />} onClick={stopRecord} style={{ borderRadius: 20 }}>
            停止录音
          </Button>
        </div>
      )}
    </div>
  )
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
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
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
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 20 }}><SoundOutlined style={{ color: '#52c41a', marginRight: 8 }} />语音选择</h2>
        <Button type="primary" block icon={<PlusOutlined />} onClick={() => setUploadModalOpen(true)}
          style={{ marginTop: 8, borderRadius: 10 }}>
          上传自定义语音
        </Button>
      </div>

      <Spin spinning={loading}>
        {voices.length === 0 && !loading ? (
          <Empty description="暂无可用语音" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {voices.map((v) => (
              <Card
                key={v.id}
                size="small"
                style={{ borderRadius: 12, borderColor: 'rgba(148,163,184,0.1)' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                    {genderIcon(v.gender || '')}
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {v.name}
                        <Tag color={v.is_custom ? 'orange' : 'green'} style={{ marginLeft: 6, fontSize: 10 }}>
                          {v.is_custom ? '自定义' : '预置'}
                        </Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#94a3b8' }}>
                        {v.gender === 'male' ? '男声' : v.gender === 'female' ? '女声' : v.style || ''}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                    <Button size="small" type="primary" ghost
                      icon={playingId === v.id ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                      onClick={() => handlePlay(v.id)}>
                      {playingId === v.id ? '停止' : '试听'}
                    </Button>
                    {v.is_custom && (
                      <Button size="small" type="text" danger icon={<DeleteOutlined />}
                        onClick={() => handleDelete(v)} />
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Spin>

      {/* 上传弹窗 */}
      <Modal
        title="上传自定义语音"
        open={uploadModalOpen}
        onOk={handleUpload}
        onCancel={() => { setUploadModalOpen(false); setUploadFile(null); setRecordedBlob(null) }}
        confirmLoading={uploading}
        okText="上传"
        width={400}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Input
            placeholder="语音名称，如：我的声音"
            value={uploadName}
            onChange={(e) => setUploadName(e.target.value)}
          />
          <Select value={uploadGender} onChange={setUploadGender} options={genderOptions} />
          <Tabs
            items={[
              {
                key: 'record',
                label: '手机录音',
                children: <VoiceRecorder onRecorded={(blob) => { setUploadFile(new File([blob], 'recording.wav', { type: 'audio/wav' })); setRecordedBlob(blob) }} />,
              },
              {
                key: 'file',
                label: '文件上传',
                children: (
                  <Upload accept=".mp3,.wav,.m4a,.ogg" maxCount={1}
                    beforeUpload={(file) => { setUploadFile(file); return false }}
                    onRemove={() => setUploadFile(null)}>
                    <Button icon={<UploadOutlined />}>选择音频文件（至少10秒）</Button>
                  </Upload>
                ),
              },
            ]}
          />
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
