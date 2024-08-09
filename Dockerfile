FROM python:3.12 AS builder

WORKDIR /app

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

COPY . .

RUN poetry config repositories.pypi https://pypi.tuna.tsinghua.edu.cn/simple
RUN poetry config virtualenvs.create false && poetry install

EXPOSE 8000

# Start FastAPI using Uvicorn
CMD ["python", "main.py"]
