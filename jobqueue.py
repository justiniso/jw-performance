from Queue import PriorityQueue
import datetime
import os
from track import rclient

PRIORITY = 5


class ClassBase(object):
    """Simple base class for helpers like serialization"""

    def __init__(self):
        self.created = datetime.datetime.now()

    def __repr__(self):
        return str(self.serialize())

    def serialize(self):
        return self.__dict__


class Job(ClassBase):
    """This is the actual job that will be created on an upload request. The serialized form will be passed to the
    redis queue to then be picked up by the workers.

    :param customer_id: Unique identifier for a customer to use in subpriority algorithm
    :param filename: Source filename to be transcoded
    """

    customer_id = None
    subpriority = None
    started = None
    completed = None

    def __init__(self, customer_id, filename):
        super(Job, self).__init__()
        self.customer_id = customer_id
        self.filename = filename
        self.dest_filename = self._get_dest_filename(filename)

    def _get_dest_filename(self, filename):
        """Given a filename construct the destination filename. This will be in an 'images' directory adjacent to
        this file
        """
        raw_name = os.path.splitext(os.path.basename(filename))[0]
        directory = os.path.join(os.path.dirname(__file__), 'images')
        return os.path.join(directory, raw_name + '.png')

    def start(self):
        self.started = datetime.datetime.now()

    def complete(self):
        self.completed = datetime.datetime.now()


class JobQueue(ClassBase):
    """Job Queue MUST be thread-safe

    If async is set, use redis to track the number of jobs per user
    """

    def __init__(self, async=True):
        super(JobQueue, self).__init__()
        self.jobs = PriorityQueue()
        self.async = async

        self.customer_jobs = dict() if not async else None

    def push_job(self, job):
        """Add new job to the queue"""
        customer_key = job.customer_id

        if self.async:
            rclient.incr('customer.{}'.format(customer_key))
            jobcount = int(rclient.get('customer.{}'.format(customer_key)))
        else:
            try:
                self.customer_jobs[customer_key]
            except KeyError:
                self.customer_jobs[customer_key] = 1
            else:
                self.customer_jobs[customer_key] += 1
            jobcount = self.customer_jobs[customer_key]

        job.subpriority = PRIORITY + jobcount
        self.jobs.put((job.subpriority, job))

    def pop_job(self):
        _, job = self.jobs.get()
        if self.async:
            rclient.decr('customer.{}'.format(job.customer_id))
        else:
            self.customer_jobs[job.customer_id] -= 1
        return job
