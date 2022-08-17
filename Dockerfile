FROM python:3.9-alpine
RUN pip3 install bs4 requests
WORKDIR /app
COPY main.py main.py
ENTRYPOINT python3 main.py
EXPOSE 8080