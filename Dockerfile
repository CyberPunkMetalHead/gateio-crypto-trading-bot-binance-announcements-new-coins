# API Dockerfile
FROM python:3.9-alpine

# Copy requirements file and install them
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy module files
COPY src/gateio_new_coins_announcements_bot ./src/gateio_new_coins_announcements_bot
COPY pyproject.toml .
COPY README.md .
COPY setup.cfg .
COPY setup.py .
COPY main.py .

# Install files in src/gateio_new_coins_announcements_bot as module
RUN pip3 install -e .

# Copy relevant files to run bot
COPY config.yml .
COPY old_coins.json .
COPY auth/auth.yml ./auth/

#root directory contains main.py to start the bot as well as all config/auth.yml files
WORKDIR .

CMD [ "python", "main.py"]
