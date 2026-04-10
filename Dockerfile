FROM ghcr.io/meta-pytorch/openenv-base:latest

WORKDIR /app

COPY . .  

RUN uv pip install --system .

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]