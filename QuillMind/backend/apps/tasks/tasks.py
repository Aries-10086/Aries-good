import time

from celery import shared_task

from .models import AsyncTask


@shared_task(bind=True)
def ping_task(self, task_id):
    task = AsyncTask.objects.get(task_id=task_id)
    task.mark_running()

    try:
        time.sleep(3)
        result = {"message": "pong"}
        task.mark_success(result)
        return result
    except Exception as exc:
        task.mark_failed(exc)
        raise
