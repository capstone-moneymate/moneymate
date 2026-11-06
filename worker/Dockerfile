# 판단 채점 서버(judge_api.py) 이미지. docker-compose.yml 의 judge 서비스가 쓴다.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul

WORKDIR /app

# 의존성 먼저 설치 (코드만 바뀌면 이 층은 캐시를 쓴다)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000
CMD ["uvicorn", "judge_api:app", "--host", "0.0.0.0", "--port", "8000"]
