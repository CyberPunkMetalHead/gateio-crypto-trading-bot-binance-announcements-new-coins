# API Dockerfile

FROM python:3.9-alpine
RUN mkdir /app
COPY src /app
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt
CMD [ "python", "main.py"]
