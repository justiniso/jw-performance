"""
The transcoder is the core functionality of the app. It does the heavy-lifting of performing the jobs and
transcoding images from other images to .png
"""
import os
import errno

from PIL import Image
from track import rclient


def transcode(src, dest):
    """Transcode an image file from a source to a destination file. This will remove the source file"""
    dirname = os.path.dirname(dest)
    try:
        os.makedirs(dirname)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            raise

    image = Image.open(src)
    image.save(dest)
    os.unlink(src)


def do_job(job):
    """Given a job to transcode, perform it and push key these metrics to redis

    :type job: Job
    :param job: The job containing the source and destination filenames set
    :return: None
    """
    job.start()
    transcode(job.filename, job.dest_filename)
    job.complete()

    wait_time_in_queue = job.started - job.created
    rclient.lpush('asset.time.queue', wait_time_in_queue.total_seconds())

    process_time = job.completed - job.started
    rclient.lpush('asset.time.process', process_time.total_seconds())

    total_wait_time_for_asset = job.completed - job.created
    rclient.lpush('asset.time.wait', total_wait_time_for_asset.total_seconds())

    bytes_read = os.path.getsize(job.dest_filename)
    rclient.lpush('asset.bytes', bytes_read)

    rclient.incr('asset.count.completed', 1)