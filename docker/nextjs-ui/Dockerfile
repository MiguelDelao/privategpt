# Development-focused Dockerfile for Next.js UI
# TODO: Add production optimization as technical debt

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY src/privategpt_ui/sandbox-ui/package*.json ./

# Install dependencies as root first
RUN npm ci --no-fund --no-audit

# Copy source code before changing ownership
COPY src/privategpt_ui/sandbox-ui .

# Skip permission changes for development simplicity

# Expose port
EXPOSE 3000

# Development command with hot reload
CMD ["npm", "run", "dev"]