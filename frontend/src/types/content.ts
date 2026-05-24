export interface RewrittenScript {
  id: number
  topic_id?: number
  original_text: string
  rewritten_text: string
  rewrite_prompt?: string
  style: string
  word_count: number
  is_approved: number
  source_type: string
  source_url?: string
  created_at: string
}

export interface RewriteRequest {
  original_text: string
  style: string
  topic_id?: number
  source_url?: string
}
