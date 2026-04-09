FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + Node.js 20
RUN apt-get update && apt-get install -y \
    bash \
    nginx \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Next.js dependencies and build
COPY pr_review_dashboard/package.json pr_review_dashboard/package-lock.json ./pr_review_dashboard/
RUN cd pr_review_dashboard && npm ci --production=false

# Copy everything
COPY . .

# Build the Next.js frontend
RUN cd pr_review_dashboard && npm run build

# Ensure start.sh is executable
RUN chmod +x start.sh

ENV PYTHONPATH=/app
EXPOSE 7860

CMD ["./start.sh"]
