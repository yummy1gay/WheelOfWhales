[![PYTHON 3.10](https://img.shields.io/badge/-PYTHON%203.10-black?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3100/)
[![CHANNEL](https://img.shields.io/badge/-CHANNEL-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/hidden_coding)
[![CHAT](https://img.shields.io/badge/-CHAT-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/hidden_codding_chat)
[![BOT LINK](https://img.shields.io/badge/-BOT%20LINK-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/wheelofwhalesbot?start=CGYJGk91pub)
[![BOT MARKET](https://img.shields.io/badge/-BOT%20MARKET-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/hcmarket_bot?start=referral_5143703753)

## ✨ Features  
|Feature|Supported|
|:-----:|:-------:|
|Multithreading|✅|
|Proxy binding to session|✅|
|Auto Referral|✅|
|Automatic joining to squad|✅|
|Automatic connection wallets|✅|
|AutoTapper|✅|
|Automatic wheel spinning|✅|
|AutoPlay games (Flappy and Dino)|✅|
|Auto Empire|✅|
|Auto TokenFlip|✅|
|AutoTasks|✅|
|WebSockets|✅|
|Support for pyrogram .session|✅|

## ⚙️ [Settings](https://github.com/yummy1gay/WheelOfWhales/blob/main/.env-example/)
|Settings|Description|
|:------:|:---------:|
|**API_ID**|Platform data from which to run the Telegram session (default - android)|
|**API_HASH**|Platform data from which to run the Telegram session (default - android)|
|**AUTO_TAP**|Automatic clicking (default - True)|
|**AUTO_CONNECT_WALLETS**|Automatic connection of TON wallets to accounts. Addresses and seed phrases are saved in connected_wallets.txt (default - False)|
|**SCORE**|Score per game (default is [5, 30] (That is, 5 to 30))|
|**SQUAD_NAME**|@username of the squad channel/chat without the '@' symbol|
|**REF_ID**|Text after 'start=' in your referral link|
|**AUTO_TASKS**|Automatically performs tasks (default - True)|
|**AUTO_CLAIM_REF_REWARD**|Name saying itself (default - True)|
|**AUTO_TOKENFLIP**|Automatic TokenFlip game every half-day to a day (random choice). (default - False)|
|**AUTO_EMPIRE**|Automatic empire. LevelUP Underground Card Games and Slot Machines, and auto claiming empire rewards (default - True)|
|**EMPIRE_LEVEL**|Empire level to upgrade, max 4 (default - 1)|
|**AUTO_RESOLVE_EMPIRE**|Automatically resolves events in the empire (default - False)|
|**AUTO_RENEW_LICENSE**|Automatically renews licenses when required(default - False)|
|**USE_RANDOM_DELAY_IN_RUN**|Name saying itself (default - True)|
|**RANDOM_DELAY_IN_RUN**|Random seconds delay for ^^^ (default is [5, 30])|
|**NIGHT_MODE**|Pauses operations from 22:00 to 06:00 UTC (default - False)|
|**RECONNECT_WALLETS**|If you have lost the wallets information, you can reconnect new wallets by setting this parameter to True. (default - False)|
|**USE_PROXY_FROM_FILE**|Whether to use a proxy from the `bot/config/proxies.txt` file (True / False)|
|**WEBSOCKETS_WITHOUT_PROXY**|WebSockets are used without a proxy due to this setting, resulting in fewer WebSocket errors.|
|**FREE_SPINS_NOTIFICATIONS**|Sends notifications about free spins won in the wheels. The notification also provides a link to log into the @whale session account (this feature allows you to access @whale on the account where the spins were won without logging into the account itself) (default - False) ***UPD from Jan 27: Free spins have stopped being awarded (?), I haven't seen them since Jan 9.***|
|**NOTIFICATIONS_BOT_TOKEN**|The `BOT_TOKEN` of the bot that will be used to send notifications. Get it by contacting to [BotFather](https://t.me/botfather)|
|**ADMIN_TG_USER_ID**|The Telegram `UserID` to whom the bot will send notifications. Get it by contacting to [IDBot](https://t.me/username_to_id_bot)|

## Quick Start 📚

To quickly install the required libraries and run the bot:

1. Open `run.bat` on Windows or `run.sh` on Linux.

---

## 🎓 Prerequisites

Make sure you have Python **3.10** installed.  
Download Python [here](https://www.python.org/downloads/).

### Obtaining API Keys

1. Visit [my.telegram.org](https://my.telegram.org) and log in with your phone number.
2. Select "API development tools" and fill out the form to register a new application.
3. Note down your **API_ID** and **API_HASH** from the site and add them to the `.env` file.

---

## 🛠️ Installation
You can download the [**repository**](https://github.com/yummy1gay/WheelOfWhales) by cloning it to your system and installing the necessary dependencies:
```shell
git clone https://github.com/yummy1gay/WheelOfWhales.git
cd WheelOfWhales
```

Then you can do automatic installation by typing:

Windows:
```shell
run.bat
```

Linux:
```shell
run.sh
```

# <img src="https://upload.wikimedia.org/wikipedia/commons/3/35/Tux.svg" alt="Tux" width="21" /> Linux manual installation
```shell
sudo sh install.sh
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cp .env-example .env
nano .env  # Here you must specify your API_ID and API_HASH, the rest is taken by default

python3 main.py
```

You can also use arguments for quick start, for example:
```shell
~/WheelOfWhales >>> python3 main.py --action (1/2)
# Or
~/WheelOfWhales >>> python3 main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```

# <img src="https://upload.wikimedia.org/wikipedia/commons/5/5f/Windows_logo_-_2012.svg" alt="Windows Logo" width="25" /> Windows manual installation
```shell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env-example .env
# Here you must specify your API_ID and API_HASH, the rest is taken by default

python main.py
```

You can also use arguments for quick start, for example:
```shell
~/WheelOfWhales >>> python main.py --action (1/2)
# Or
~/WheelOfWhales >>> python main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```

### Contacts

[![Support](https://img.shields.io/badge/For%20support%20or%20questions-BOT%20AUTHOR-blue?style=for-the-badge&logo=telegram&logoColor=white&labelColor=black)](https://t.me/yummy1gay)
