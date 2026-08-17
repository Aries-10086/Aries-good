from __future__ import annotations

from django.test import SimpleTestCase

from apps.tasks.models import AsyncTask, InvalidTaskTransition


class AsyncTaskStateMachineTests(SimpleTestCase):
    def _task(self, *, status=AsyncTask.Status.PENDING):
        return AsyncTask(task_id="task-1", type="ping", status=status)

    def test_mark_running_only_from_pending(self):
        task = self._task()
        task.save = lambda update_fields=None: None

        task.mark_running()

        self.assertEqual(task.status, AsyncTask.Status.RUNNING)

    def test_mark_running_rejects_non_pending_status(self):
        task = self._task(status=AsyncTask.Status.RUNNING)
        task.save = lambda update_fields=None: None

        with self.assertRaises(InvalidTaskTransition):
            task.mark_running()

    def test_reset_for_retry_only_from_failed(self):
        task = self._task(status=AsyncTask.Status.FAILED)
        task.save = lambda update_fields=None: None

        task.reset_for_retry()

        self.assertEqual(task.status, AsyncTask.Status.PENDING)
        self.assertEqual(task.error, "")

    def test_reset_for_retry_rejects_non_failed_status(self):
        task = self._task(status=AsyncTask.Status.PENDING)
        task.save = lambda update_fields=None: None

        with self.assertRaises(InvalidTaskTransition):
            task.reset_for_retry()
