FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bash \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure start.sh is executable
RUN chmod +x start.sh

ENV PYTHONPATH=/app
EXPOSE 7860

# We use start.sh to launch FastAPI, Streamlit, and Nginx
CMD ["./start.sh"]
