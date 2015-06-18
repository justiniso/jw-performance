#!/usr/bin/env bash
import uuid
import os

from flask import Flask, request
from werkzeug.utils import secure_filename
from redis import Redis
from rq import Queue

from jobqueue import Job, JobQueue
import transcoder


app = Flask(__name__)

# Set the queues to be global as a hack. They are thread-safe so it should not cause problems
job_queue = JobQueue(async=True)
redis_queue = Queue(connection=Redis(), async=True)


@app.route('/')
def home():
    return 'I am up! Try uploading to "/upload" then transcoding those files with "/process"'


@app.route('/upload', methods=['POST'])
def upload():
    """The main upload endpoint for the transcoder service. This function should only save the uploaded files and
    enqueue new jobs"""
    customer_id = request.form['user_id']
    upfile = request.files['file']

    filename = secure_filename(str(uuid.uuid4()) + os.path.splitext(upfile.filename)[-1])
    filename = os.path.join('/tmp', filename)

    upfile.save(filename)
    assert os.path.getsize(filename) > 0, 'No bytes uploaded!'

    job = Job(customer_id, filename)
    job_queue.push_job(job)

    return 'success!'

@app.route('/process', methods=['POST'])
def process():
    """Initiate the asset processing and start delegating the background jobs"""
    while not job_queue.jobs.empty():
        redis_queue.enqueue(transcoder.do_job, job_queue.pop_job())
    return 'done!'

if __name__ == '__main__':
    app.run('localhost', 5000, debug=True)