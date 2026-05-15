#FROM python:3.11-slim
#
#WORKDIR /app
#
#COPY . .
#
#RUN pip install --no-cache-dir -r requirements.txt
#
#RUN chmod +x ./render_sdk/Spectra6_render_x86_64
#
#ENV PORT=8080
#
#CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app


FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libstdc++6 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x /app/render_sdk/Spectra6_render_x86_64

ENV LD_LIBRARY_PATH=/app/render_sdk/lib
ENV PORT=8080

EXPOSE 8080

CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 0 \
    main:app