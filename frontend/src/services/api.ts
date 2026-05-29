import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// 请求拦截：自动附带用户API keys + user_id
api.interceptors.request.use((config) => {
  try {
    const keys = JSON.parse(localStorage.getItem('user_api_keys') || '{}')
    if (Object.keys(keys).length > 0) {
      config.headers['X-DashScope-Key'] = keys.dashscope_key || ''
      config.headers['X-Pexels-Key'] = keys.pexels_key || ''
      config.headers['X-Pixabay-Key'] = keys.pixabay_key || ''
      config.headers['X-SiliconFlow-Key'] = keys.siliconflow_key || ''
    }
    const user = JSON.parse(localStorage.getItem('current_user') || '{}')
    if (user.userId) {
      config.headers['X-User-Id'] = String(user.userId)
    }
  } catch {}
  return config
})

// 响应拦截：统一提取 data
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.message || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

// ─── 文案模板 ───
export const templateApi = {
  list: (): Promise<any> => api.get('/templates'),
  generate: (data: { template_id: string; fields: Record<string, string>; style?: string }): Promise<any> => api.post('/templates/generate', data),
}

// ─── 赛道/选题 ───
export const trackApi = {
  list: (): Promise<any> => api.get('/topics/tracks'),
  create: (data: { name: string; description?: string }): Promise<any> => api.post('/topics/tracks', data),
}

export const topicApi = {
  list: (track_id?: number, platform?: string): Promise<any> =>
    api.get('/topics/hot', { params: { track_id, platform } }),
  detail: (id: number): Promise<any> => api.get(`/topics/hot/${id}`),
  refresh: (track_id: number): Promise<any> => api.post(`/topics/hot/refresh?track_id=${track_id}`),
}

// ─── 内容改写 ───
export const contentApi = {
  rewrite: (data: { original_text: string; style?: string; topic_id?: number; source_url?: string }): Promise<any> =>
    api.post('/content/rewrite', data),
  scripts: (): Promise<any> => api.get('/content/scripts'),
  scriptDetail: (id: number): Promise<any> => api.get(`/content/scripts/${id}`),
  updateScript: (id: number, data: { rewritten_text?: string; is_approved?: number }): Promise<any> =>
    api.patch(`/content/scripts/${id}`, data),
  deleteScript: (id: number): Promise<any> => api.delete(`/content/scripts/${id}`),
  scrape: (url: string, platform: string): Promise<any> => api.post('/content/scrape', { url, platform }),
  generateTitles: (originalText: string): Promise<any> => api.post('/content/titles', { original_text: originalText }),
  generatePublish: (id: number): Promise<any> => api.post(`/content/scripts/${id}/publish`),
}

// ─── 语音 ───
export const voiceApi = {
  profiles: (): Promise<any> => api.get('/voice/profiles'),
  tts: (text: string, voice_id: number): Promise<any> => api.post('/voice/tts', { text, voice_id }),
  uploadCustom: (name: string, gender: string, file: File): Promise<any> => {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('gender', gender)
    fd.append('file', file)
    return api.post('/voice/profiles/custom', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  update: (id: number, data: { name?: string; gender?: string }): Promise<any> => {
    const fd = new FormData()
    if (data.name) fd.append('name', data.name)
    if (data.gender) fd.append('gender', data.gender)
    return api.patch(`/voice/profiles/${id}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (id: number): Promise<any> => api.delete(`/voice/profiles/${id}`),
}

// ─── 视频项目 ───
export const videoApi = {
  create: (data: any): Promise<any> => api.post('/video/projects', data),
  list: (): Promise<any> => api.get('/video/projects'),
  detail: (id: number): Promise<any> => api.get(`/video/projects/${id}`),
  update: (id: number, data: any): Promise<any> => api.patch(`/video/projects/${id}`, data),
  generate: (id: number): Promise<any> => api.post(`/video/projects/${id}/generate`),
  delete: (id: number): Promise<any> => api.delete(`/video/projects/${id}`),
  collect: (id: number): Promise<any> => api.post(`/video/projects/${id}/collect`),
  library: (): Promise<any> => api.get('/video/library'),
}

// ─── 任务追踪 ───
export const taskApi = {
  list: (params?: { ref_type?: string; ref_id?: number }): Promise<any> => api.get('/tasks/', { params }),
  detail: (id: number): Promise<any> => api.get(`/tasks/${id}`),
  cancel: (id: number): Promise<any> => api.post(`/tasks/${id}/cancel`),
}

// ─── 素材搜索 ───
export const materialApi = {
  search: (q: string): Promise<any> => api.get('/materials/search', { params: { q } }),
  download: (url: string, video_id: number): Promise<any> => api.post('/materials/download', { url, video_id }),
}

// ─── 上传/素材库 ───
export const uploadApi = {
  listFiles: (): Promise<any> => api.get('/upload/files'),
  deleteFile: (path: string): Promise<any> => api.delete(`/upload/files?path=${encodeURIComponent(path)}`),
  file: (file: File, file_type = 'images'): Promise<any> => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/upload/file?file_type=${file_type}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default api
