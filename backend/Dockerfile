# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (needed for asyncpg, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy everything from current context to a temporary space
# This prevents "file not found" errors regardless of Render's context settings
COPY . .

# Universal fix for Monorepos:
# If Render is looking at the repository root, requirements.txt is at backend/requirements.txt
# If Render is looking at the backend folder, requirements.txt is at ./requirements.txt
# We normalize this by moving everything to the /app root if we find the backend folder.
RUN if [ -d "backend" ]; then \
        echo "Root context detected. Moving backend files..." && \
        mv backend/* . && \
        mv backend/.* . 2>/dev/null || true && \
        rm -rf backend; \
    else \
        echo "Subfolder context detected. Files are already in place."; \
    fi

# Debug: list files to see what we have
RUN ls -la

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port (Render sets the PORT environment variable)
EXPOSE 8000

# Command to run the application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
