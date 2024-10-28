FROM python:3.12-slim

RUN apt install -y libpq-dev

ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install --upgrade pip && \
    pip install poetry

WORKDIR /app

RUN poetry install --no-root

COPY frostbite main.py ./

# run the app
CMD ["uvicorn", "main:app"]