from logging import Handler


# TODO:
class TelegramHandler(Handler):
    def __init__(self, token, chat_id):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def emit(self, record):
        import telegram

        bot = telegram.Bot(token=self.token)
        bot.send_message(self.chat_id, text=self.format(record))


def get_telegram_bot_updates(token):
    import requests

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    ret = requests.get(url)
    try:
        return ret.json()
    except Exception:
        return ret
