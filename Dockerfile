FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY requirements.txt pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose the port that the MCP server runs on
EXPOSE 8080

# Run the MCP server
CMD ["python", "mcp_server.py"]
