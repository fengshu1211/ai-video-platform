"""任务状态查询 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db, AsyncTask
from app.schemas.task import TaskOut

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.get("/")
def list_tasks(ref_type: str | None = None, ref_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(AsyncTask)
    if ref_type:
        q = q.filter(AsyncTask.task_type == ref_type)
    if ref_id:
        q = q.filter(AsyncTask.ref_id == ref_id)
    return q.order_by(AsyncTask.created_at.desc()).limit(20).all()


@router.post("/{task_id}/cancel")
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status in ("pending", "processing"):
        task.status = "failed"
        task.error_message = "用户取消"
        db.commit()
    return {"code": 0, "message": "任务已取消"}
