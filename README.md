# Инструкция по сборке

---
Подразумевается, что на компьютере установлены Docker, Git.
Версии, используемые при разработке:
- Docker - 24.0.7
- Git - 2.34.1
---

# Инструкция по сборке проекта

Склонируйте репозиторий к себе:
```
git clone https://github.com/tApps-team/moneyswap_tg_bot.git
```
Перейдите в папку проекта:
```
cd moneyswap_tg_bot/
```
---
Откройте файл .env:
```
nano .env
```

Добавьте в файл .env следующее содержимое:
```
TOKEN=

WEBAPP_URL_ONE=
WEBAPP_URL_TWO=
WEBAPP_URL_THREE=

```

Выйдите и сохраните файл .env:
- нажмите Ctrl + X
- подтвердите изменения нажав Y
- нажмите Enter
---

**Перед сборкой убедитесь, что service Docker активен!**

Соберите образ
```
docker build --tag 'tg_bot' .
```
---
Запустите контейнер
```
docker run -d 'tg_bot'
```
