ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/api
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV PIP_TRUSTED_HOST=pypi.org

WORKDIR /app

COPY api/requirements.txt /app/api/requirements.txt
COPY api/requirements-x86.txt /app/api/requirements-x86.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r /app/api/requirements-x86.txt

COPY api /app/api
COPY data /app/data
COPY scripts /app/scripts

EXPOSE 9090

WORKDIR /app/api
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9090"]
