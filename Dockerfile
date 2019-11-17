FROM python:3

WORKDIR /app

VOLUME /data

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY . .

CMD ["python3", "chart_create.py"]
