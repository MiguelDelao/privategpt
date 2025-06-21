# Development-focused Dockerfile for Next.js UI
# TODO: Add production optimization as technical debt

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY src/privategpt_ui/sandbox-ui/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY src/privategpt_ui/sandbox-ui .

# Expose port
EXPOSE 3000

# Development command with hot reload
CMD ["npm", "run", "dev"]