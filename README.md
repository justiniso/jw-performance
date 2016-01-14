# JW Image Transcoding Service

This is a small service that manipulates images. You can upload an image and crop, resize, or transcode that image using
using the API endpoints.


## Run the API

Create a virtual environment

```bash
virtualenv venv
source venv/bin/activate
```

Install the dependencies

```bash
pip install -r requirements.txt
```

Start Redis

```bash
redis-server

# Or, to run in the background
redis-server &
```

Start the application

```bash
python app.py
```


## Run the tests

You should follow the same steps above for a virtual environment.

To run all tests:

```bash
py.test tests
```

To run an individual test:

```bash
py.test tests/<name_of_module>.py
```