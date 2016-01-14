"""
The transcoder is the core functionality of the app. It does the heavy-lifting of performing the jobs and
transcoding image formats. You can push jobs to the transcoder workers using the queue in this module.
"""
import os
import errno
import logging
import threading
from Queue import Queue, Empty

from PIL import Image
from redis import StrictRedis

_log = logging.getLogger(__name__)

queue = Queue()
store = StrictRedis()


def _makedirpath(dest):
    dirname = os.path.dirname(dest)
    try:
        os.makedirs(dirname)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            raise


def transcode(src, dest):
    """
    Transcode an image file from a source to a destination file. This will remove the source file
    """
    try:
        image = Image.open(src)

        _makedirpath(dest)
        image.save(dest)
    except IOError:
        _log.warn('Image truncation error')

    if src != dest:
        try:
            os.unlink(src)
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise


def resize(src, dest, size):
    """
    Resize an image and save the resized image to the new destination. Size is described by a

    :param src: Source file
    :param dest: Destination file
    :type size: tuple
    :param size: A tuple of x and y (in pixels) of the new size, e.g. (200, 548)
    """
    try:
        image = Image.open(src)

        _makedirpath(dest)
        image = image.resize(size, Image.ANTIALIAS)
        image.save(dest)
    except IOError:
        _log.warn('Image truncation error')


def crop(src, dest, box):
    """
    Crop the image to points described by the box

    :param src: Source file
    :param dest: Destination file
    :type box: tuple
    :param box: Tuple of the new bounding box for the image, e.g. (200, 50, 90, 80)
    """
    try:
        image = Image.open(src)

        _makedirpath(dest)
        image = image.crop(box)
        image.save(dest)
    except IOError:
        _log.warn('Image truncation error')


def worker():
    """
    Initiate the asset processing and start delegating the background jobs

    :type queue: JobQueue
    """
    while True:
        try:
            job = queue.get(timeout=100)
        except Empty:
            _log.debug('Found nothing to process')
            continue

        action, params = job

        src = params.get('src')
        dest = params.get('dest')
        job_id = params.get('job_id')
        img_id = params.get('img_id')

        store.set(job_id, 'processing')

        # Only try to process one image at a time
        lock = threading.Lock()
        lock.acquire()
        try:
            if action == 'transcode':
                transcode(src, dest)
            elif action == 'resize':
                resize(src, dest, params.get('size'))
            elif action == 'crop':
                crop(src, dest, params.get('box'))

            # Update the new destination and job status
            store.set('images.{img_id}.location'.format(img_id=img_id), dest)
            store.set(job_id, 'done')

        except Exception, e:
            _log.warn('Error in job {}: {}'.format(job_id, e))
            store.set(job_id, 'error: {}'.format(e))
            raise
