# The API as a Lambda container image (deploy/aws-lambda/deploy.sh). Build context:
# the project root. The Lambda Web Adapter extension forwards Lambda events to
# uvicorn, so the app runs unchanged.
# --provenance=false matters: Lambda rejects image indexes that carry attestations.
#   docker buildx build --platform linux/arm64 --provenance=false --sbom=false -f deploy/aws-lambda/Dockerfile .
FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /var/task
COPY pyproject.toml ./
COPY app ./app
# The embedding extra brings boto3, which start.py also uses.
RUN pip install --no-cache-dir ".[embedding]" && python -m compileall -q app
COPY deploy/aws-lambda/start.py ./

# Lambda's filesystem is read-only except /tmp, which is also HOME. AWS_LWA_ASYNC_INIT
# lets a start longer than Lambda's 10 s init phase finish inside the first request
# instead of restarting.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/health \
    AWS_LWA_INVOKE_MODE=response_stream \
    AWS_LWA_ASYNC_INIT=true

RUN useradd --system --uid 10001 api
USER api

EXPOSE 8080
CMD ["python", "start.py"]
