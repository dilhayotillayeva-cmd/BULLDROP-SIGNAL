# BULLDROP SIGNAL — Render Free Web Service

Bu versiya Render **Web Service Free** uchun tayyorlangan.

## GitHub
ZIP ichidagi 3 faylni repository root'iga yuklang:
- bot.py
- requirements.txt
- render.yaml

## Render
New -> Web Service -> GitHub repository.

Build Command:
`pip install -r requirements.txt`

Start Command:
`python bot.py`

Plan:
`Free`

## Token
Bot tokenini GitHub kodiga yozmang.

Render -> Environment -> Add Environment Variable:

Key:
`BOT_TOKEN`

Value:
BotFather bergan YANGI token.

Admin ID:
`6982309853` kod ichida allaqachon mavjud.

## Muhim
Bot polling ishlatadi va shu bilan birga Render talab qiladigan HTTP portni ochadi.
