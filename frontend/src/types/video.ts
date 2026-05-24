export interface VideoProject {
  id: number
  title: string
  script_id?: number
  voice_id?: number
  bgm_path?: string
  bgm_volume: number
  material_paths_json: string
  subtitle_enabled: number
  lip_sync_enabled: number
  lip_sync_mode: string
  image_animation_type?: string
  subtitle_animation: string
  aspect_ratio: string
  status: string
  collected: number
  output_path?: string
  duration_seconds?: number
  created_at: string
  updated_at: string
}

export interface AsyncTask {
  id: number
  task_type: string
  ref_id?: number
  celery_task_id?: string
  status: string
  progress: number
  progress_message?: string
  error_message?: string
  result_json: string
  created_at: string
  updated_at: string
}
