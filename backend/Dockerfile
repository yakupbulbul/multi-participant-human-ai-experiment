FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY pytest.ini ./
COPY tests ./tests

# --workers 1 on purpose: session state, timers and WebSocket connections live
# in process memory. More workers would split participants across processes
# and silently break the experiment. (Scaling path: Redis pub/sub, out of scope.)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
