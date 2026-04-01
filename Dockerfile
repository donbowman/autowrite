FROM python:3.13-trixie

# Install system dependencies required for CairoSVG
RUN apt-get update && apt-get install -y \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY autowrite/ ./autowrite/

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Set environment variable required by TensorFlow/Keras
ENV TF_USE_LEGACY_KERAS=1

EXPOSE 8000

# Run the FastAPI backend
CMD ["uvicorn", "autowrite.main:app", "--host", "0.0.0.0", "--port", "8000"]
