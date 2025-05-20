FROM python:3.10.8-slim
WORKDIR /app
COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY ./radarr.py /app
CMD ["python", "radarr.py"]  