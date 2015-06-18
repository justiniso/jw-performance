import unittest
from jobqueue import Job, JobQueue


class TestJobQueue(unittest.TestCase):

    def test_priority_retrieval(self):
        """Tests that retrieving jobs from the queue will always do so in priority order"""

        jobs = [Job(1, ''), Job(2, ''), Job(1, ''), Job(3, ''), Job(1, ''), Job(3, '')]

        q = JobQueue(async=False)
        for job in jobs:
            q.push_job(job)

        last_job = None
        comparison_made = 0
        while not q.jobs.empty():
            job = q.pop_job()
            if last_job is not None:
                comparison_made += 1
                self.assertLessEqual(last_job.subpriority, job.subpriority)
            last_job = job

        self.assertTrue(comparison_made, 'No comparisons were made, something went wrong!')