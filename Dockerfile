FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt ./
COPY labs/step-05/requirements.txt labs/step-05/requirements.txt
COPY labs/step-13/requirements.txt labs/step-13/requirements.txt
COPY labs/step-26/requirements.txt labs/step-26/requirements.txt
COPY labs/step-33/requirements.txt labs/step-33/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY college_maintenance ./college_maintenance
COPY migrations ./migrations
COPY alembic.ini ./
RUN useradd --uid 10001 --create-home college && mkdir -p /app/.local/uploads && chown -R college:college /app/.local
USER college
CMD ["uvicorn", "college_maintenance.api:app", "--host", "0.0.0.0", "--port", "8000"]
