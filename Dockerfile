# API Dockerfile

FROM python:3.9-alpine
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY src /app
CMD [ "python", "app/main.py"]
