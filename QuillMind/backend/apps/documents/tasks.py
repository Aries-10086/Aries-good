from celery import shared_task
from django.conf import settings

from apps.tasks.models import AsyncTask, InvalidTaskTransition

from .models import DocumentReview
from .services import DocumentReviewService


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    soft_time_limit=settings.DOCUMENT_REVIEW_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.CELERY_TASK_TIME_LIMIT,
)
def review_document_task(self, task_id, review_id, model_version=None):
    task = AsyncTask.objects.get(task_id=task_id)
    review = DocumentReview.objects.get(id=review_id)

    if self.request.retries > 0 and task.status == AsyncTask.Status.FAILED:
        task.reset_for_retry()
    task.mark_running()

    try:
        DocumentReviewService().review(
            review=review,
            user_id=review.user_id,
            model_version=model_version,
        )
        task.mark_success({"review_id": str(review.id)})
        return {"review_id": str(review.id)}
    except InvalidTaskTransition:
        raise
    except Exception as exc:
        task.mark_failed(exc)
        raise
