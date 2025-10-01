FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && pip install --no-cache-dir gunicorn
COPY . /app
ENV FLASK_APP=web.app:app
EXPOSE 8000
CMD ['gunicorn','-c','gunicorn.conf.py','web.app:app']
