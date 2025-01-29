if [ ! -d /vosk-model-spk-0.4/]; then
  curl https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip
  tar -xf vosk-model-spk-0.4.zip
fi
if [ ! -d /vosk-model-ru-0.42/]; then
  curl https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip
  tar -xf vosk-model-ru-0.42.zip
fi

docker-compose -f docker-compose.yml up -d --build