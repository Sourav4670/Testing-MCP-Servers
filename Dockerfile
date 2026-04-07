FROM python:3.11.9-slim
WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 5053
ENTRYPOINT ["python", "-m", "travel_advisor"]
CMD ["--mode", "streamable-http", "--host", "0.0.0.0", "--port", "5053"]