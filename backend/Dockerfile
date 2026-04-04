FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/backend-requirements.txt

COPY . /workspace

EXPOSE 8000

CMD ["python", "backend/start_backend.py"]
