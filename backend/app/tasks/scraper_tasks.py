"""内容抓取异步任务（后期实现）"""
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2)
def scrape_content_task(self, url: str, platform: str):
    """抓取平台内容"""
    return {"status": "not_implemented", "url": url, "platform": platform}
