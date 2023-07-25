FROM python:3.9-alpine
RUN pip3 install bs4 requests
WORKDIR /app
COPY *.py ./
ENTRYPOINT python3 main.py
ENV MODE server_v2
EXPOSE 8080