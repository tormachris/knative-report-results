FROM python:3

WORKDIR /app

VOLUME /data
VOLUME /chart

ENV SEARCHDIR /data
ENV CHARTDIR /chart

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY chart_create.py .

CMD ["python3", "chart_create.py"]
