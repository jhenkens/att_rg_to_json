FROM python:3.11-alpine
RUN pip3 install bs4 requests
WORKDIR /app
COPY *.py ./
ENTRYPOINT python3 main.py
EXPOSE 8080