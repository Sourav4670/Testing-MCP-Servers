FROM python:3.11.9-slim
WORKDIR /app

COPY pyproject.toml ./
COPY tools/ tools/
COPY server.py ./
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 5053
#ENTRYPOINT ["python", "server.py"]
ENTRYPOINT ["internet-speed-test-mcp"]
CMD ["--mode", "streamable-http", "--host", "0.0.0.0", "--port", "5053"]
#CMD ["--mode", "sse", "--host", "0.0.0.0", "--port", "5051"]