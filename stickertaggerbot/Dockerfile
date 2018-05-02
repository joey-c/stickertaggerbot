FROM python:3.6
ADD . /stickertaggerbot/
RUN pip install -r stickertaggerbot/requirements.txt
CMD ["gunicorn", "--bind=0.0.0.0", "stickertaggerbot.application:application"]