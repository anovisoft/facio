FROM python:3.12-slim

WORKDIR /app

COPY packages/domain ./packages/domain
COPY apps/api ./apps/api

RUN pip install --no-cache-dir -e ./packages/domain \
    && pip install --no-cache-dir -e ./apps/api

EXPOSE 8000

ENV FACIO_TALK_MODE=scripted
ENV FACIO_GOLDENS_DIR=/app/apps/api/goldens

CMD ["uvicorn", "facio_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
