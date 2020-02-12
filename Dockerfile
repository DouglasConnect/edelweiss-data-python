FROM python:3.7-slim-stretch

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python-dev \
    libssl-dev \
    libpq5 \
    libpq-dev \
    git \
    curl \
	&& rm -rf /var/lib/apt/lists/*
RUN pip install -U pip poetry
ENV POETRY_VIRTUALENVS_CREATE=false
COPY ./edelweiss_data ./edelweiss_data
COPY ./tests ./tests
COPY ./poetry.lock ./poetry.lock
COPY ./pyproject.toml ./pyproject.toml
COPY ./README.md ./README.md
RUN poetry install --no-interaction --no-ansi
RUN poetry run pytest ./tests
