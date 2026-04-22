FROM python:3.11.9-slim

WORKDIR /app

COPY pyproject.toml ./
COPY tools/ tools/
COPY server.py ./
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 5052
ENTRYPOINT ["simple-weather-mcp"]
ENV TRANSPORT_TYPE=streamable-http
ENV APP_HOST=0.0.0.0
ENV APP_PORT=5052
