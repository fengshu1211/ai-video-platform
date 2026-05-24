export interface Track {
  id: number
  name: string
  description?: string
  is_active: number
  created_at: string
}

export interface HotTopic {
  id: number
  track_id: number
  platform?: string
  title: string
  source_url?: string
  metrics_json: string
  ai_analysis?: string
  status: string
  created_at: string
}
