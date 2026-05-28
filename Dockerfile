FROM python:3.11-slim

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir numpy pandas matplotlib

WORKDIR /app

COPY minimal_pinn/ ./minimal_pinn/
COPY notes/ ./notes/

ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1

ENTRYPOINT ["python", "-m"]
