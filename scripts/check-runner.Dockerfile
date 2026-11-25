# Linux runtime verification without access to the host Docker socket.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends redis-server \
    && rm -rf /var/lib/apt/lists/*
COPY 06-lab-complete/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt pyyaml
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /lab/06-lab-complete
CMD ["python", "check_production_ready.py"]
