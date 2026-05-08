FROM python:3.11-slim-bullseye

# Install Node.js (needed for OpenClaw) and curl
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install OpenClaw globally
RUN npm install -g openclaw@latest

# Install Playwright browsers for OpenClaw (Ghost scraping)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx playwright install --with-deps chromium

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose FastAPI and OpenClaw Gateway ports
EXPOSE 8000 18789

# Make start script executable
RUN chmod +x start.sh

CMD ["./start.sh"]
