FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY dashboard/requirements.txt /tmp/dashboard-requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/dashboard-requirements.txt

COPY . /workspace

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
