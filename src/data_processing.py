

def format_result(data: list[dict]) -> dict[str, list:dict]:
    """
    Функция для формирования результата распознавания речи. Объединяет последовательные реплики
    от одного источника, подсчитывает общее время диалога.

    :param data: список словарей, содержащих информацию о репликах
    :return: словарь содержащий итоговый результат
    """
    res = {'dialog': [], 'result_duration': {}}

    tmp_array = []
    tmp_duration = {}

    for i in data:
        current_source = 'transmitter' if i['spk'] == 0 else 'receiver'
        current_duration = i['result'][-1]['end'] - i['result'][0]['start']
        if current_source in tmp_duration:
            tmp_duration[current_source] += current_duration
        else:
            tmp_duration[current_source] = current_duration

        if len(tmp_array) > 0 and tmp_array[-1]['source'] == current_source:
            tmp_array[-1]['text'] = f"{tmp_array[-1]['text']} {i['text']}"
            tmp_array[-1]['raised_voice'] = tmp_array[-1]['raised_voice'] if tmp_array[-1]['duration'] > current_duration else i['raised_voice']
            tmp_array[-1]['duration'] += current_duration
            tmp_array[-1]['duration'] = round(tmp_array[-1]['duration'])
        else:
            tmp_array.append({'source': current_source,
                              'text': i['text'],
                              'duration': round(current_duration, 1),
                              'raised_voice': i['raised_voice']})

    res['dialog'] = tmp_array
    res['result_duration'] = {key: round(value, 1) for key, value in tmp_duration.items()}

    return res
