from celery import shared_task

from apps.tasks.models import AsyncTask

from .models import DocumentReview
from .services import DocumentReviewService


@shared_task(bind=True)
def review_document_task(self, task_id, review_id, model_version=None):
    task = AsyncTask.objects.get(task_id=task_id)
    review = DocumentReview.objects.get(id=review_id)
    task.mark_running()

    try:
        DocumentReviewService().review(
            review=review,
            user_id=review.user_id,
            model_version=model_version,
        )
        task.mark_success({"review_id": str(review.id)})
        return {"review_id": str(review.id)}
    except Exception as exc:
        task.mark_failed(exc)
        raise
