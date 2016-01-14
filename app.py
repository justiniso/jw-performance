#!/usr/bin/env bash
"""
This is a simple image manipulation web service. Images can be uploaded, served, transcoded, cropped, and resized
using the endpoints provided in this API.

A Redis cache is used to store data about the images and users. We store the following keys in our cache:

    images.all                  --  List of all image ids in the system
    images.{img_id}.location    --  The filepath of this image on this machine
    images.{img_id}.last_job    --  The last job performed on this image
    images.{img_id}.actions     --  List of all actions that have been performed on this image
    user.{user_id}.images       --  List of all image ID's associated with this user

"""
import uuid
import os
import logging
import threading

import werkzeug
from flask import Flask, send_file, Response
from flask_restful import Api, Resource, marshal_with, reqparse, fields, abort
from werkzeug.utils import secure_filename
from redis import StrictRedis

import transcoder

TEST_HOST = 'localhost'
TEST_PORT = 5000
WORKER_THREAD_COUNT = 10
ALLOWED_EXTENSIONS = ('jpg', 'jpeg', 'png', 'bmp')


app = Flask(__name__)

_log = logging.getLogger(__name__)


store = StrictRedis()


@app.route('/')
def home():
    return 'I am up! Try uploading to "/images"'


@app.route('/serve/<img_id>')
def serve(img_id):
    """Serve out the image"""
    location = store.get('images.{img_id}.location'.format(img_id=img_id))

    with open(location, 'rb') as f:
        img = f.read()
    base, ext = os.path.splitext(location)

    mimetype = ext

    if mimetype == 'jpg' or mimetype == 'jpeg':
        mimetype = 'image/jpeg'
    elif mimetype == 'png':
        mimetype = 'image/png'
    elif mimetype == 'bmp':
        mimetype = 'image/bmp'

    return Response(img, mimetype=mimetype)


@app.route('/debug/all-image-ids')
def all_image_ids():
    """Return all image IDs for debugging"""
    if not app.debug:
        abort(403)
    return ',\n'.join(store.lrange('images.all', 0, -1))


@app.route('/debug/dump-queue')
def dump_queue():
    """Dump all jobs in the queue for debugging; they will not be processed by the workers"""
    if not app.debug:
        abort(403)

    jobs = []
    while not transcoder.queue.empty():
        jobs.append(str(transcoder.queue.get(block=False)))

    return ',\n'.join(jobs) or 'Empty Queue!'


class Image(Resource):
    """
    API Resource for a specific image identified by its ID
    """

    @marshal_with({
        'id': fields.String,
        'actions': fields.List(fields.String),
        'location': fields.String,
        'last_job': fields.String,
        'last_job_state': fields.String
    })
    def get(self, img_id):
        location = store.get('images.{img_id}.location'.format(img_id=img_id))
        actions = store.lrange('images.{img_id}.actions'.format(img_id=img_id), 0, -1)
        actions.reverse()
        last_job = store.get('images.{img_id}.last_job'.format(img_id=img_id))
        if last_job:
            last_job_state = store.get(last_job)
        else:
            last_job = 'none'
            last_job_state = 'none'

        return {
            'id': img_id,
            'actions': actions,
            'location': location,
            'last_job': last_job,
            'last_job_state': last_job_state
        }

    @marshal_with({'job_id': fields.String})
    def put(self, img_id):
        parser = reqparse.RequestParser()
        parser.add_argument('action', required=True)
        parser.add_argument('extension', type=str, required=False)
        parser.add_argument('size', type=str, required=False)
        parser.add_argument('box', type=str, required=False)

        data = parser.parse_args()

        job_id = 'job-{}'.format(uuid.uuid4())

        src = store.get('images.{img_id}.location'.format(img_id=img_id))

        if not src:
            abort(404)

        if not data.action:
            abort(400, description='Please specify an action')

        params = {}

        # Enqueue a transcode job
        if data['action'] == 'transcode':
            if 'extension' not in data:
                abort(400, description='Transcoding requires an extension')
            if data['extension'] not in ALLOWED_EXTENSIONS:
                abort(400, description='Use valid extension: {}'.format(ALLOWED_EXTENSIONS))
            base, ext = os.path.splitext(src)
            dest = os.path.join('/tmp', '.'.join([base, data['extension']]))

            params = {'src': src, 'dest': dest, 'job_id': job_id, 'img_id': img_id}

        # Enqueue a resize job
        elif data['action'] == 'resize':
            try:
                size = data['size'].split(',')
                size = (int(size[0]), int(size[1]))
            except (TypeError, ValueError, AttributeError, IndexError):
                abort(400, description='Invalid size. Specify width and height delimited by a comma: "50,50"')
            params = {'src': src, 'dest': src, 'size': size, 'job_id': job_id, 'img_id': img_id}

        # Enqueue a crop job
        elif data['action'] == 'crop':
            try:
                box = data['box'].split(',')
                box = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
            except (TypeError, ValueError, AttributeError, IndexError):
                abort(400, description='Invalid bounding box. Specify box delimited by comma: "50,150,90,80"')
            params = {'src': src, 'dest': src, 'box': box, 'job_id': img_id, 'img_id': job_id}

        else:
            abort(400, description='Invalid image action: {}'.format(data['action']))

        store.set(job_id, 'queued')
        store.set('images.{img_id}.last_job'.format(img_id=img_id), job_id)
        store.lpush('images.{img_id}.actions'.format(img_id=img_id), data['action'])
        transcoder.queue.put((data['action'], params))

        return {'job_id': job_id}

    @marshal_with({'success': fields.Boolean})
    def delete(self, img_id):
        location = store.get('images.{img_id}.location'.format(img_id=img_id))
        os.unlink(location)

        user_id = store.get('images.{img_id}.user'.format(img_id=img_id))

        # Delete all data associated with this image
        store.delete('images.{img_id}.location'.format(img_id=img_id))
        store.delete('images.{img_id}.actions'.format(img_id=img_id))
        store.lrem('images.all', 0, img_id)
        store.lrem('user.{user_id}.images'.format(user_id=user_id), 0, img_id)

        return {'success': True}


class Images(Resource):
    """
    API Resource for images (list and post)
    """

    @marshal_with({
        'id': fields.String,
        'location': fields.String
    })
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', type=unicode, required=True)
        parser.add_argument('file', type=werkzeug.datastructures.FileStorage, location='files', required=True)
        data = parser.parse_args(strict=True)

        img_id = str(uuid.uuid4())
        user_id = data['user_id']

        filename = secure_filename(str(uuid.uuid4()) + os.path.splitext(data['file'].filename)[-1])
        filename = os.path.join('/tmp', filename)

        # If we failed to store the image, set the filename to empty
        try:
            data['file'].save(filename)
            store = True
        except OSError:
            filename = ''

        if store:
            if os.path.getsize(filename) == 0:
                _log.warn('File with no bytes uploaded by user {} (img # {})'.format(user_id, img_id))

        # Store data about this image
        store.set('images.{img_id}.location'.format(img_id=img_id), filename)
        store.set('images.{img_id}.user'.format(img_id=img_id), user_id)
        store.lpush('images.{img_id}.actions'.format(img_id=img_id), 'upload')
        store.lpush('images.all', img_id)
        store.lpush('user.{user_id}.images'.format(user_id=user_id), img_id)

        return {
            'id': img_id,
            'location': filename
        }


class Job(Resource):
    """
    API resource for a transcode job
    """

    @marshal_with({'status': fields.String})
    def get(self, job_id):
        status = store.get(job_id)
        if not status:
            abort(404)
        return {'status': status}


api = Api(app)
api.add_resource(Images, '/images')
api.add_resource(Image, '/image/<img_id>')
api.add_resource(Job, '/job/<job_id>')


# Development mode
if __name__ == '__main__':

    # Start all of the worker threads to do the transcoding
    for _ in xrange(WORKER_THREAD_COUNT):
        t = threading.Thread(target=transcoder.worker)
        t.daemon = True
        t.start()

    app.run(TEST_HOST, TEST_PORT, debug=True)

# Production mode
else:
    app.debug = False


