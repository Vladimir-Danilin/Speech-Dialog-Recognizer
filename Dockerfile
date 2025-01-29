FROM python:3.10

RUN apt-get update
RUN apt-get install libsox-fmt-all -y
RUN apt-get install ffmpeg sox -y

COPY requirements.txt /src/requirements.txt
WORKDIR /src/

RUN pip install numpy typing_extensions
RUN pip install -r requirements.txt
RUN pip install websocket-client

COPY src/ /src/
EXPOSE 5000

RUN chmod +x ./entrypoint.sh
ENTRYPOINT [ "./entrypoint.sh" ]