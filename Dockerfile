# API Dockerfile
FROM python:3.9-alpine

#Setting workdir 
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Copy module files
COPY src/gateio_new_coins_announcements_bot ./src/gateio_new_coins_announcements_bot
COPY pyproject.toml .
COPY README.md .
COPY setup.cfg .
COPY setup.py .
COPY main.py .

# Copy relevant files to run bot
COPY config.yml .
COPY old_coins.json .
COPY auth/auth.yml ./auth/

# install necessary requirements
RUN pip3 install -r requirements.txt

# create the app user
RUN addgroup -S app && adduser -H -S app -G app

# chown all the files to the app user
RUN chown -R app:app /app

# change to the app user
USER app

CMD [ "python", "main.py"]
