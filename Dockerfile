FROM python:3.11.9-slim

WORKDIR /app

COPY pyproject.toml ./
COPY tools/ tools/
COPY server.py ./
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 5051
ENTRYPOINT ["simple-weather-mcp"]
CMD ["--mode", "streamable-http", "--host", "0.0.0.0", "--port", "5051"]
