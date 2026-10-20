import re


def change_phone_format(phone) -> str | None:
    if phone is None or phone == '':
        return None
    else:
        phone = re.sub('[^0-9 +]', '', phone)

    if phone.startswith('0'):
        phone = '62'+phone[1:]
    elif phone.startswith('8'):
        phone = '62'+phone

    if not phone.startswith('+'):
        phone = '+'+phone

    return phone
