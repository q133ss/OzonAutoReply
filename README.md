# OzonAutoReply

## Build (PyInstaller, браузер Playwright включен)

1) Активируйте venv и установите зависимости (если еще не установлены):
```
.\venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

2) Скачайте Chromium в папку проекта:
```
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\playwright-browsers"
python -m playwright install chromium
```

3) Соберите exe:
```
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\playwright-browsers"
python -m PyInstaller --noconfirm --windowed --name OzonAutoReply ^
  --add-data "ozon_ai.db;." ^
  --add-data "ozon_ai\data;ozon_ai\data" ^
  --add-data "playwright-browsers;playwright-browsers" ^
  --collect-all playwright ^
  --collect-all playwright_stealth ^
  --hidden-import ozon_ai.playwright_runner ^
  app.py
```

Готовый exe: `dist\OzonAutoReply\OzonAutoReply.exe`

## Примечания
- База `ozon_ai.db` берется на момент сборки. Чтобы использовать актуальную базу, просто замените файл в `dist\OzonAutoReply\_internal\ozon_ai.db`.
- В `dist\OzonAutoReply\_internal\playwright-browsers` лежит встроенный Chromium для Playwright.
