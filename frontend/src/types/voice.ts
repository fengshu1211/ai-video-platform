export interface VoiceProfile {
  id: number
  name: string
  provider: string
  voice_id: string
  gender?: string
  style?: string
  sample_url?: string
  is_custom: number
  status: string
  created_at: string
}
