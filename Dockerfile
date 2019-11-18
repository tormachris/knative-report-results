FROM python:3

WORKDIR /app

VOLUME /data
VOLUME /chart
VOLUME /text

ENV SEARCHDIR /data
ENV CHARTDIR /chart
ENV TEXTDIR /text

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && rm requirements.txt

COPY chart_create.py .

CMD ["python3", "chart_create.py"]
