import json
import os
import subprocess
import wave

from librosa import note_to_hz, load, pyin
from sox import file_info
from websocket import create_connection, ABNF
from numpy import mean, isnan
from sklearn.cluster import KMeans

VOSK_SERVER = os.getenv('VOSK_SERVER')

base_temp_path = "../"


def is_high_pitch(audio_file: wave.Wave_read, data: bytes, threshold: float = 200.0) -> bool:
    """
    Проверяет, является ли тон голоса аудиофайла высоким

    :param audio_file: ссылка на аудиофайл
    :param data: массив байтов текущей части аудиофайла
    :param threshold: пороговая частота в Гц (например, 200 Гц)
    :return: true, если тон высокий, иначе False
    """
    with wave.open("tmp_frames.wav", "wb") as handle:
        handle.setparams(audio_file.getparams())
        handle.writeframes(data)

    y, sr = load('tmp_frames.wav', sr=None)
    pitches, _, _ = pyin(y, fmin=note_to_hz('C2'), fmax=note_to_hz('C7'))
    valid_pitches = pitches[~isnan(pitches)]
    if len(valid_pitches):
        avg_pitch = mean(valid_pitches)
        os.remove('tmp_frames.wav')
        return bool(avg_pitch > threshold)
    else:
        os.remove('tmp_frames.wav')
        return False


def wsSend(uri: str, primary_converted_file: str) -> dict[list]:
    """
    Производит распознование аудио файла путём отправки его на vosk сервер

    :param uri: ссылка на vosk сервер (docker host)
    :param primary_converted_file: путь к подготовленому для распознования wav-файлу
    :return: список результатов распознования разбитых по фразам
    """
    answer = []
    wf = wave.open(primary_converted_file, "rb")
    ws = create_connection(uri)
    ws.send('{ "config" : { "sample_rate" : %d } }' % (wf.getframerate()))
    buffer_size = int(wf.getframerate() * 0.2)
    while True:
        data = wf.readframes(buffer_size)

        if len(data) == 0:
            break
        ws.send(data, ABNF.OPCODE_BINARY)
        res = json.loads(ws.recv())

        if 'result' in res:
            if len(res['result']):
                res['raised_voice'] = is_high_pitch(wf, data=data, threshold=230)
                answer.append(res)

    ws.send('{"eof" : 1}')
    res = json.loads(ws.recv())
    if 'result' in res:
        if len(res['result']):
            res['raised_voice'] = is_high_pitch(wf, data=data, threshold=230)
            answer.append(res)
    ws.close()

    return answer


def diarization(answer: dict) -> dict[list]:
    """
    Производит диаризацию (определения говорящих) на основе кластера и переключения между собеседниками.

    :param answer: список содержащий результаты обработки vosk сервера
    :return: список answer с определёнными спикерами для каждого отрывка диалога
    """
    transcriptions = []
    n_clusters = 2
    kmeans = None

    X = [x['spk'] for x in answer if 'spk' in x]
    if len(X) >= n_clusters:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        kmeans.fit(X)
    last_spk = 0
    for frase in answer:
        if 'spk' in frase and kmeans:
            last_spk = int(kmeans.predict([frase['spk']])[0])
        else:
            last_spk = 1 if last_spk == 0 else 0
        transcriptions.append(
            {
                'text': frase['text'],
                'result': frase['result'],
                'spk': last_spk,
                'raised_voice': frase['raised_voice']
            }
        )

    return transcriptions


def worker(unprocessed_file: str) -> list[dict]:
    """
    Производит обработку аудиофайла, конвертацию его в нужный формат для дальнейшей обработки
    и возворащает итоговый результат

    :param unprocessed_file: путь к исходному аудиофайлу
    :return: список транскрипций, где каждая реплика содержит текст, результаты, идентификатор говорящего,
             и информацию о повышении тона голоса
    """
    primary_converted_file = '../tmp.wav'
    if os.path.exists(primary_converted_file):
        os.remove(primary_converted_file)
    subprocess.call(['ffmpeg', '-i', unprocessed_file, '-ar', '16000', '-acodec', 'pcm_s16le', primary_converted_file])

    res = file_info.info(primary_converted_file)
    sample_rate = res['sample_rate']
    if sample_rate > 16000:
        sample_rate = 16000
    if sample_rate < 8000:
        sample_rate = 8000

    file_for_recognition = os.path.basename(primary_converted_file)
    file_for_recognition = os.path.splitext(file_for_recognition)[0]
    file_for_recognition = os.path.join(base_temp_path, file_for_recognition + '_converted' + '.wav')
    if os.path.exists(file_for_recognition):
        os.remove(file_for_recognition)
    subprocess.call(
        'sox "{}" -r {} -c 1 -b 16 "{}" remix {}'.format(primary_converted_file, sample_rate, file_for_recognition, 1),
        shell=True)

    result = wsSend(VOSK_SERVER, file_for_recognition)
    transcriptions = diarization(result)
    transcriptions.sort(key=lambda x: x['result'][0]['start'])

    return transcriptions
