FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/render_sdk/Spectra6_render_x86_64

ENV LD_LIBRARY_PATH=/app/render_sdk/lib

CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]