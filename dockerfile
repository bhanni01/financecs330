# Use a slim official Python image to keep the image small
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout (better for logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Copy only requirements first (Docker layer caching: this layer only
# rebuilds when requirements.txt changes, not on every code change)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code
COPY . .

# Document that the container listens on port 5000
EXPOSE 5000

# Persist the SQLite database across container restarts
VOLUME ["/app/instance"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "app:app"]
