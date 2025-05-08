from datetime import datetime


def extract_text(list_text):
    if isinstance(list_text, str):
        return list_text
    else:
        all_text = ''
        for text in list_text:
            if isinstance(text, str):
                all_text += text
            else:
                all_text += text['text']
                    
        return all_text


def extract_message(message, account):

    # Date of publication
    date = datetime.strptime(message['date'], "%Y-%m-%dT%H:%M:%S")
    date = date.strftime('%Y-%m-%d %H:%M:%S')

    # Media
    has_photo = 'photo' in message or 'thumbnail' in message
    has_video = 'file' in message

    # Text
    text = extract_text(message['text'])

    return {'account': account, 'id': message['id'], 'date': date, 'text': text, 'has_photo': has_photo, 'has_video': has_video}
