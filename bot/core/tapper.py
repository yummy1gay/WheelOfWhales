import asyncio
import string
import os
import random

import aiohttp
import json

from aiohttp_proxy import ProxyConnector
import cloudscraper
import requests
from better_proxy import Proxy
from urllib.parse import unquote

from faker import Faker
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestWebView
from datetime import datetime, timedelta, timezone
import brotli

from bot.config import settings
from bot.utils import logger
from bot.exceptions import InvalidSession
from bot.connect import connector

from .headers import headers
from .agents import generate_random_user_agent, get_sec_ch_ua


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.url = 'https://clicker-api.crashgame247.io'
        self.ws_id = 1
        self.ws_task = None
        self.recoverable = None
        self.epoch = None
        self.offset = None
        self.scraper = None

        self.session_ug_dict = self.load_user_agents() or []
        self.user_data = self.load_user_data()

        headers['User-Agent'] = self.check_user_agent()

    async def generate_random_user_agent(self):
        return generate_random_user_agent(device_type='android', browser_type='chrome')

    def save_user_agent(self):
        user_agents_file_name = "user_agents.json"

        if not any(session['session_name'] == self.session_name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.session_name,
                'user_agent': user_agent_str})

            with open(user_agents_file_name, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ⚡️ User agent saved <green>successfully</green>")

            return user_agent_str

    def load_user_agents(self):
        user_agents_file_name = "user_agents.json"

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("✨ User agents file <red>not found</red>, creating...")

        except json.JSONDecodeError:
            logger.warning("😨 User agents file is <red>empty</red> or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.session_name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    def load_user_data(self):
        user_data_file_name = f"data/{self.session_name}.json"
        if not os.path.exists('data'):
            os.makedirs('data')

        try:
            with open(user_data_file_name, 'r') as user_data_file:
                return json.load(user_data_file)

        except FileNotFoundError:
            logger.warning(f"😳 User data file for {self.session_name} <red>not found</red>, creating a new one...")
            return {"referred": None, "last_click_time": None, "last_sleep_time": None, "acknowledged": False, "squad_name": None, "in_squad": False, "sleep_time": None}

        except json.JSONDecodeError:
            logger.warning(f"😳 User data file for {self.session_name} <red>is empty</red> or corrupted. Creating a new one...")
            return {"referred": None, "last_click_time": None, "last_sleep_time": None, "acknowledged": False, "squad_name": None, "in_squad": False, "sleep_time": None}

        except Exception as error:
            logger.error(f"🚫 An unexpected <red>error</red> occurred while loading user data for {self.session_name}: {error}")
            return {"referred": None, "last_click_time": None, "last_sleep_time": None, "acknowledged": False, "squad_name": None, "in_squad": False, "sleep_time": None}

    def save_user_data(self):
        user_data_file_name = f"data/{self.session_name}.json"
        with open(user_data_file_name, 'w') as user_data_file:
            json.dump(self.user_data, user_data_file, indent=4)

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict
        ref_param = settings.REF_ID if settings.REF_ID != '' else False
        if ref_param and not ref_param.endswith("pub"):
            self.user_data["referred"] = "gold"
        elif ref_param:
            self.user_data["referred"] = "regular"

        self.save_user_data()

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False

                try:
                    await self.tg_client.connect()

                    me = await self.tg_client.get_me()
                    self.user_id = me.id
                    self.username = me.username if me.username else ''
                    if self.username == '':
                        while True:
                            fake = Faker('en_US')

                            name_english = fake.name()
                            name_modified = name_english.replace(" ", "").lower()

                            random_letters = ''.join(random.choices(string.ascii_lowercase, k=random.randint(1, 5)))
                            final_name = name_modified + random_letters
                            status = await self.tg_client.set_username(final_name)
                            if status:
                                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💾 Set username <cyan>@{final_name}</cyan>")
                                break
                            else:
                                continue

                    start_command_found = False

                    async for message in self.tg_client.get_chat_history("WheelOfWhalesBot"):
                        if (message.text and message.text.startswith("/start")) or (message.caption and message.caption.startswith("/start")):
                            start_command_found = True
                            break

                    if start_command_found:
                        self.user_data["acknowledged"] = True
                        self.save_user_data()
                    else:
                        if ref_param:
                            await self.tg_client.send_message("WheelOfWhalesBot", f"/start {ref_param}")
                            if not ref_param.endswith("pub"):
                                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ⭐️ Referred by a <yellow>gold</yellow> ticket.")
                            else:
                                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🖥 Referred by a <light-blue>regular</light-blue> referral.")

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('WheelOfWhalesBot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | 😞 FloodWait <red>{fl}</red>")
                    logger.info(f"{self.session_name} | 😴 Sleep <light-cyan>{fls}s</light-cyan>")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url="https://clicker.crashgame247.io/earn"
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 Unknown <red>error</red> during Authorization: {error}")
            await asyncio.sleep(3)

    async def get_whale_link(self) -> None:
        with_tg = True

        if not self.tg_client.is_connected:
            with_tg = False
            await self.tg_client.connect()
            start_command_found = False

            async for message in self.tg_client.get_chat_history("whale"):
                if (message.text and message.text.startswith("/start")) or (message.caption and message.caption.startswith("/start")):
                    start_command_found = True
                    break

            if start_command_found:
                self.user_data["registered_in_@whale"] = True
                self.save_user_data()
            else:
                await self.tg_client.send_message("whale", f"/start 3c54274715e2b661")

        while True:
            try:
                peer = await self.tg_client.resolve_peer('whale')
                break
            except FloodWait as fl:
                fls = fl.value

                logger.warning(f"{self.session_name} | 😞 FloodWait <red>{fl}</red>")
                logger.info(f"{self.session_name} | 😴 Sleep <light-cyan>{fls}s</light-cyan>")

                await asyncio.sleep(fls + 3)

        web_view = await self.tg_client.invoke(RequestWebView(
            peer=peer,
            bot=peer,
            platform='android',
            from_bot_menu=False,
            url="https://api.crashgame247.io/url"
        ))

        auth_url = web_view.url

        if with_tg is False:
            await self.tg_client.disconnect()

        return auth_url

    async def check_proxy(self, proxy: Proxy) -> None:
        try:
            response = self.scraper.get(url='https://httpbin.org/ip', timeout=5)
            ip = (response.json()).get('origin')
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🛡 Proxy IP: <blue>{ip}</blue>")
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🛡 Proxy: {proxy} | 🚫 <red>Error:</red> {error}")

    async def login(self, init_data):
        if init_data is None:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 init_data is <red>None</red>")
            await asyncio.sleep(999999999999)

        params = dict(item.split('=') for item in init_data.split('&'))
        user_data = json.loads(unquote(params['user']))

        data = {
            "dataCheckChain": init_data,
            "initData": {
                "query_id": params['query_id'],
                "user": user_data,
                "auth_date": params['auth_date'],
                "hash": params['hash']
            }
        }

        try:
            resp = self.scraper.post(f"{self.url}/user/sync", json=data)
            
            resp.raise_for_status()

            resp_json = resp.json()
            if settings.DEBUG:
                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🫡 Login Response: {resp_json}")

            token = resp_json.get("token")
            banned = resp_json.get("user", {}).get("isBanned")
            balance = resp_json.get("balance", {}).get("amount")
            streak = resp_json.get("meta", {}).get("dailyLoginStreak")
            last_login = resp_json.get("meta", {}).get("lastFirstDailyLoginAt")
            referrer = resp_json.get("referrerUsername")
            tasks = resp_json.get("meta", {}).get("regularTasks")
            nanoid = resp_json.get("user", {}).get("nanoid")
            flappy_score = resp_json.get("meta", {}).get("flappyScore")
            dino_score = resp_json.get("meta", {}).get("dinoScore")
            wallet = resp_json.get("user", {}).get("walletAddress")

            return (token, banned, balance, streak, last_login, referrer, tasks, nanoid, flappy_score, dino_score, wallet)

        except Exception as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 An unexpected <red>error</red> occurred: {str(e)}")
            return None

    async def claim_daily_bonus(self):
        url = f"{self.url}/user/bonus/claim"
        
        try:
            response = self.scraper.patch(url)
            
            if response.status_code == 200:
                json_data = response.json()
                points = json_data.get("incrementBy", 0)
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 💘 Daily bonus <green>successfully claimed!</green> (+{points} points)")
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Failed</red> with status: {response.status_code} (claim_daily_bonus)")
                
                if response.status_code == 500:
                    return False
        
        except cloudscraper.exceptions.CloudflareChallengeError as e:
            logger.error(f"{self.session_name} | 🚫 Cloudflare challenge <red>error</red> occurred: {e}")
        except Exception as e:
            logger.error(f"{self.session_name} | 🤷‍♂️ Unexpected <red>error</red>: {str(e)}")

    async def send_clicks(self, click_count: int):
        clicks = {"clicks": click_count}
        try:
            with self.scraper.put(
                f"{self.url}/meta/clicks", 
                json=clicks
            ) as response:
                if response.status_code == 200:
                    pass
                else:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Failed</red> with status: {response.status_code} (send_clicks)")

        except Exception:
            pass

    async def refresh_tokens(self, proxy):
        init_data = await self.get_tg_web_data(proxy)

        params = dict(item.split('=') for item in init_data.split('&'))
        user_data = json.loads(unquote(params['user']))

        data = {
            "dataCheckChain": init_data,
            "initData": {
                "query_id": params['query_id'],
                "user": user_data,
                "auth_date": params['auth_date'],
                "hash": params['hash']
            }
        }

        with self.scraper.post(f"{self.url}/user/sync", json=data) as resp:
            if resp.status_code == 200:
                resp_json = resp.json()
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Failed</red> with status: {resp.status_code} (refresh_tokens)")
                return None

        token = resp_json.get("token")
        wsToken = resp_json.get("wsToken")
        wsSubToken = resp_json.get("wsSubToken")
        id_for_ws = resp_json.get("user", {}).get("id")

        return token, wsToken, wsSubToken, id_for_ws

    async def play_flappy(self):
        try:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎮 Started <blue>playing</blue> FlappyWhale...")
            sleep = random.uniform(40, 90)
            await asyncio.sleep(sleep)

            leaderboard_url = f'{self.url}/meta/minigame/flappy/leaderboards'
            self.scraper.get(leaderboard_url)

            score = random.randint(settings.SCORE[0], settings.SCORE[1])
            payload = {"score": score}

            score_url = f'{self.url}/meta/minigame/flappy/score'
            score_response = self.scraper.patch(score_url, json=payload)

            if score_response.status_code == 200:
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🐳 <cyan>Finished</cyan> FlappyWhale with a score of {score}!")
                self.user_data["flappy_score"] = score
                self.save_user_data()
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 <red>Failed</red> to submit FlappyWhale score, status code: {score_response.status_code}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in play_flappy: {error}")

    async def play_dino(self):
        try:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎮 Started <blue>playing</blue> DinoWhale...")
            sleep = random.uniform(40, 90)
            await asyncio.sleep(sleep)

            leaderboard_url = f'{self.url}/meta/minigame/dino/leaderboards'
            self.scraper.get(leaderboard_url)

            score = random.randint(settings.SCORE[0], settings.SCORE[1])
            payload = {"score": score}

            score_url = f'{self.url}/meta/minigame/dino/score'
            score_response = self.scraper.patch(score_url, json=payload)

            if score_response.status_code == 200:
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🐳 <cyan>Finished</cyan> DinoWhale with a score of {score}!")
                self.user_data["dino_score"] = score
                self.save_user_data()
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 <red>Failed</red> to submit DinoWhale score, status code: {score_response.status_code}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in play_dino: {error}")

    async def whale_spin(self):
        try:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎰 WhaleSpin Started...")

            reach_url = f'{self.url}/meta/wheel/reach'
            reach_response = self.scraper.get(reach_url)

            if reach_response.status_code == 200:
                pass
            elif reach_response.status_code != 400:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Failed to reach wheel, status code: {reach_response.status_code}")

            await asyncio.sleep(30)
            ack_url = f'{self.url}/meta/wheel/ack'
            ack_response = self.scraper.put(ack_url)

            if ack_response.status_code == 200:
                content_encoding = ack_response.headers.get('Content-Encoding', '')

                if b'"opensGame"' in ack_response.content:
                    ack_content = ack_response.content.decode('utf-8', errors='replace')
                else:
                    if 'br' in content_encoding:
                        try:
                            ack_content = brotli.decompress(ack_response.content).decode('utf-8', errors='replace')
                        except brotli.error as e:
                            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Brotli decompression failed: {e}")
                            ack_content = '{}'
                    else:
                        ack_content = ack_response.content.decode('utf-8', errors='replace')

                try:
                    ack_json = json.loads(ack_content)
                    opens_game = ack_json.get('opensGame', 'N/A')
                except ValueError as e:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Failed to parse JSON response: {e}")

                if opens_game == "flappy":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🐤 WhaleSpin Result: <light-yellow>FlappyWhale</light-yellow>")
                    await self.save_result("🐤 FlappyWhale")
                    await self.play_flappy()
                elif opens_game == "dino":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🦖 WhaleSpin Result: <green>DinoWhale</green>")
                    await self.save_result("🦖 DinoWhale")
                    await self.play_dino()
                elif opens_game == "slot":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎰 WhaleSpin Result: <cyan>Slot</cyan>")
                    await self.save_result("🎰 Slot")
                elif opens_game == "death":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ☠️ WhaleSpin Result: <red>Death</red>")
                    await self.save_result("☠️ Death")
                elif opens_game == "whale_free_spin":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🐋 WhaleSpin Result: <blue>5 Free Spins</blue> awarded in @whale")
                    await self.save_result("🐋 5 Free Spins awarded in @whale")
                    if settings.FREE_SPINS_NOTIFICATIONS:
                        link = await self.get_whale_link()
                        message = (f"<b>👤@{self.username} (ID: </b><code>{self.user_id}</code><b>)</b>\n"
                                f"<i>🎁 I won free spins at @whale, to get them, click here 👇</i>\n\n"
                                f"🐳 <b><a href='{link}'>Link to enter @whale for the session {self.session_name}</a></b>")
                        await self.send_notification(message)
                else:
                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ❓ WhaleSpin Result: Unknown result type '{opens_game}' detected")

            elif ack_response.status_code != 400:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Failed to acknowledge wheel, status code: {ack_response.status_code}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in whale_spin: {error}")

    async def save_result(self, result):
        try:
            current_time = datetime.now().strftime("%d.%m.%Y | %H:%M")
            message = f"{current_time} | {self.session_name} | {result}\n"

            with open("WhaleSpins.txt", "a", encoding="utf-8") as file:
                file.write(message)
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in save_result: {error}")

    async def send_websocket_messages(self, ws_url, wsToken, wsSubToken, id_for_ws, proxy):
        while True:
            try:
                if settings.WEBSOCKETS_WITHOUT_PROXY:
                    proxy_conn = None
                else:
                    proxy_conn = ProxyConnector.from_url(proxy) if proxy else None

                async with aiohttp.ClientSession(connector=proxy_conn) as ws_session:
                    async with ws_session.ws_connect(ws_url) as websocket:
                        connect_message = {
                            "connect": {"token": wsToken, "name": "js"},
                            "id": self.ws_id
                        }
                        await websocket.send_json(connect_message)
                        if settings.DEBUG:
                            logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent connect message: {connect_message}")
                        await websocket.receive()

                        self.ws_id += 1

                        subscribe_message = {
                            "subscribe": {
                                "channel": f"user:{id_for_ws}",
                                "token": wsSubToken
                            },
                            "id": self.ws_id
                        }
                        
                        if self.ws_id == 2:
                            await websocket.send_json(subscribe_message)
                            if settings.DEBUG:
                                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent subscribe message: {subscribe_message}")
                            response = await websocket.receive()

                            if response.type == aiohttp.WSMsgType.TEXT:
                                data = response.data.strip().splitlines()
                                for line in data:
                                    try:
                                        json_response = json.loads(line)
                                        if json_response.get("id") == 2:
                                            self.recoverable = json_response["subscribe"].get("recoverable")
                                            self.epoch = json_response["subscribe"].get("epoch")
                                            self.offset = json_response["subscribe"].get("offset")
                                            break
                                    except json.JSONDecodeError:
                                        pass
                            elif response.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                pass

                        if self.ws_id > 2:
                            subscribe_message = {
                                "subscribe": {
                                    "channel": f"user:{id_for_ws}",
                                    "token": wsSubToken,
                                    **({"recover": self.recoverable} if self.recoverable is not None else {}),
                                    **({"epoch": self.epoch} if self.epoch is not None else {}),
                                    **({"offset": self.offset} if self.offset is not None else {})
                                },
                                "id": self.ws_id
                            }
                            await websocket.send_json(subscribe_message)
                            if settings.DEBUG:
                                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent subscribe message: {subscribe_message}")
                            await websocket.receive()

                        self.ws_id += 1

                        while True:
                            response = await websocket.receive()
                            
                            if response.type == aiohttp.WSMsgType.TEXT:
                                data = response.data.strip().splitlines()
                                for line in data:
                                    try:
                                        json_response = json.loads(line)
                                        if settings.DEBUG:
                                            logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Received JSON: {json_response}")
                                        if "push" in json_response:
                                            push_data = json_response["push"].get("pub", {}).get("data", {})
                                            
                                            if push_data.get("type") == "show_wheel":
                                                await self.whale_spin()
                                                
                                                if "offset" in json_response["push"]["pub"]:
                                                    self.offset = json_response["push"]["pub"]["offset"]

                                        if json_response == {}:
                                            await websocket.send_json({})
                                            if settings.DEBUG:
                                                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent ping response")
                                            break
                                                    
                                    except json.JSONDecodeError:
                                        pass
                            elif response.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break

            except Exception as e:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 WebSocket <red>error</red>: {str(e)}. Reconnecting...")
                continue

    async def clicker(self, proxy):
        logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ AutoTapper <light-green>started!</light-green>")

        while True:
            refresh = await self.refresh_tokens(proxy)
            
            if refresh is not None:
                token, wsToken, wsSubToken, id_for_ws = refresh
                self.scraper.headers.update({'Authorization': f'Bearer {token}'})
                break
            else:
                logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                await asyncio.sleep(30)

        ws_url = "wss://clicker-socket.crashgame247.io/connection/websocket"
        self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy))

        while True:
            if settings.NIGHT_MODE:
                current_time = datetime.now(timezone.utc).time()
                night_start = datetime.strptime("22:00", "%H:%M").time()
                night_end = datetime.strptime("06:00", "%H:%M").time()

                if night_start <= current_time or current_time < night_end:
                    now = datetime.now(timezone.utc)
                    if current_time >= night_start:
                        next_morning = now + timedelta(days=1)
                        next_morning = next_morning.replace(hour=6, minute=0, second=0, microsecond=0)
                    else:
                        next_morning = now.replace(hour=6, minute=0, second=0, microsecond=0)

                    sleep_duration = (next_morning - now).total_seconds()
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🌙 It's night time! Sleeping until <cyan>06:00 UTC</cyan> (~{int(sleep_duration // 3600)} hours)")
                    
                    if self.ws_task:
                        self.ws_task.cancel()
                        self.ws_id = 1

                    await asyncio.sleep(sleep_duration)

                    while True:
                        refresh = await self.refresh_tokens(proxy)
                        
                        if refresh is not None:
                            token, wsToken, wsSubToken, id_for_ws = refresh
                            self.scraper.headers.update({'Authorization': f'Bearer {token}'})
                            break
                        else:
                            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                            await asyncio.sleep(30)

                    self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy))

            last_click_time = self.user_data.get("last_click_time")
            last_sleep_time = self.user_data.get("last_sleep_time")

            if last_sleep_time:
                last_sleep_time = datetime.strptime(last_sleep_time, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
                time_since_last_sleep = datetime.now(timezone.utc) - last_sleep_time

                if time_since_last_sleep < timedelta(seconds=self.user_data.get("sleep_time", 0)):
                    remaining_time = timedelta(seconds=self.user_data["sleep_time"]) - time_since_last_sleep

                    remaining_minutes = remaining_time.seconds // 60
                    remaining_seconds = remaining_time.seconds % 60

                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Sleep time <cyan>not yet reached</cyan>, waiting for {remaining_minutes} minutes {remaining_seconds} seconds until next click...")

                    if self.ws_task:
                        self.ws_task.cancel()
                        self.ws_id = 1

                    await asyncio.sleep(remaining_time.total_seconds())

                    while True:
                        refresh = await self.refresh_tokens(proxy)
                        
                        if refresh is not None:
                            token, wsToken, wsSubToken, id_for_ws = refresh
                            self.scraper.headers.update({'Authorization': f'Bearer {token}'})
                            break
                        else:
                            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                            await asyncio.sleep(30)

                    self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy))

            total_clicks = 0
            clicks = []

            while total_clicks < 1000:
                click_count = random.randint(1, 15)
                if total_clicks + click_count > 1000:
                    click_count = 1000 - total_clicks
                clicks.append(click_count)
                total_clicks += click_count

            intervals = [random.uniform(1, 3) for _ in clicks]
            total_time = sum(intervals)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🕘 Estimated clicking time: <light-magenta>~{total_time / 60:.2f} minutes</light-magenta>")

            total_clicks = 0
            for click_count, interval in zip(clicks, intervals):
                await self.send_clicks(click_count)
                total_clicks += click_count

                self.user_data["last_click_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                self.save_user_data()

                await asyncio.sleep(interval)

                if total_clicks >= 1000:
                    break

            if self.ws_task:
                self.ws_task.cancel()
                self.ws_id = 1

            sleep_time = random.randint(1100, 2000)  # Примерно от 18 до 33 минут
            self.user_data["last_sleep_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            self.user_data["sleep_time"] = sleep_time
            self.save_user_data()

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ {total_clicks} clicks sent, <light-blue>sleeping for {sleep_time // 60} minutes.</light-blue>")

            await asyncio.sleep(sleep_time)

            while True:
                refresh = await self.refresh_tokens(proxy)
                
                if refresh is not None:
                    token, wsToken, wsSubToken, id_for_ws = refresh
                    self.scraper.headers.update({'Authorization': f'Bearer {token}'})
                    break
                else:
                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                    await asyncio.sleep(30)

            self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy))

    async def load_ts(self, url):
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 Failed to load ts: {resp.status_code}")

    async def complete_tasks(self, tasks):
        ts_url = "https://raw.githubusercontent.com/yummy1gay/WheelOfWhales/main/ts.json"
        ts = await self.load_ts(ts_url)

        t = ts.get("tasks", {})
        s = ts.get("codes", {})
        missions = ts.get("missions", {})

        methods = {
            "verify": self.verify
        }

        for task, method_name in t.items():
            if (task in tasks and tasks[task]) or task in self.user_data.get('completed_tasks', []):
                continue
            method = methods.get(method_name)
            if method:
                await method(task)

        for task, code in s.items():
            if (task in tasks and tasks[task]) or task in self.user_data.get('completed_tasks', []):
                continue
            await self.verify_code(code)

        for mission, details in missions.items():
            if all(task in tasks and tasks[task] for task in details["required_tasks"]) or \
            any(task in self.user_data.get('completed_tasks', []) for task in details["required_tasks"]):
                continue
            await self.mission(mission, details, tasks)

    async def mission(self, mission, details, tasks):
        if all(task in tasks and tasks[task] for task in details["required_tasks"]) and not any(task in self.user_data.get('completed_tasks', []) for task in details["required_tasks"]):
            return

        sleep = random.randint(30, 60)
        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Waiting {sleep} seconds before completing mission '{mission}'")
        await asyncio.sleep(sleep)

        for task in details["required_tasks"]:
            if task in self.user_data.get('completed_tasks', []):
                continue

            resp = self.scraper.patch(f'{self.url}/meta/tasks/{task}', json={})
            
            if resp.status_code == 400:
                resp_json = resp.json()
                if resp_json.get("message") == "Task already completed":
                    if 'completed_tasks' not in self.user_data:
                        self.user_data['completed_tasks'] = []
                    self.user_data['completed_tasks'].append(task)
                    continue
            
            if resp.status_code != 200:
                logger.error(f"<light-red>{self.session_name}</light-red> | ❌ Failed to verify task '{task}' (Status: {resp.status_code})")
                return
            
            await asyncio.sleep(random.randint(8, 10))

        await asyncio.sleep(3)

        final_code = details["final_code"]
        resp = self.scraper.patch(f'{self.url}/meta/tasks/{final_code}', json={})
        
        if resp.status_code == 400:
            resp_json = resp.json()
            if resp_json.get("message") == "Task already completed":
                if 'completed_tasks' not in self.user_data:
                    self.user_data['completed_tasks'] = []
                self.user_data['completed_tasks'].append(mission)
                return
        
        if resp.status_code != 200:
            logger.error(f"<light-red>{self.session_name}</light-red> | ❌ Failed to complete mission '{mission}' (Status: {resp.status_code})")
            return

        resp_json = resp.json()
        increment_score = resp_json.get('incrementScore', 'unknown')
        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎉 Mission '{mission}' completed! (+{increment_score})")

        if 'completed_tasks' not in self.user_data:
            self.user_data['completed_tasks'] = []
        self.user_data['completed_tasks'].append(mission)

    async def verify(self, task):
        try:
            sleep = random.randint(30, 60)
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Waiting {sleep} seconds before verifying task '{task}'")
            
            await asyncio.sleep(sleep)
            
            if task in self.user_data.get('completed_tasks', []):
                return

            url = f'{self.url}/meta/tasks/{task}'

            response = self.scraper.patch(url, json={})
            resp_json = response.json()

            if response.status_code == 200:
                increment_score = resp_json.get('incrementScore', 'unknown')
                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🥰 Task '{task}' <green>completed successfully.</green> <light-yellow>+{increment_score}</light-yellow>")
            elif response.status_code == 400 and resp_json.get("message") == "Task already completed":
                if 'completed_tasks' not in self.user_data:
                    self.user_data['completed_tasks'] = []
                self.user_data['completed_tasks'].append(task)
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Failed</red> to verify task '{task}', status code: {response.status_code}, {response.text}")
        
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> verifying task '{task}': {error}")

    async def verify_code(self, code):
        try:
            sleep = random.randint(10, 30)
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Waiting {sleep} seconds before verifying code '{code}'")
            
            await asyncio.sleep(sleep)

            url = f'{self.url}/meta/tasks/FIND_CODE'

            payload = {'code': code}
            
            response = self.scraper.patch(url, json=payload)
            resp_json = response.json()

            if response.status_code == 200:
                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🥰 Code '{code}' <green>verified successfully.</green> <light-yellow>+{resp_json.get('incrementScore', 'unknown')}</light-yellow>")
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Failed</red> to verify code '{code}', status code: {response.status_code}")
        
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> verifying code '{code}': {error}")

    async def get_my_squad(self):
        try:
            response = self.scraper.get(f"{self.url}/tribes/my")
            response.raise_for_status()
            response_json = response.json()
            return response_json.get("username")
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> getting my squad info for: {error}")
            return None

    async def leave_from_squad(self):
        try:
            response = self.scraper.post(f"{self.url}/tribes/leave")
            if response.status_code == 200:
                if response.text == 'true':
                    return True

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> leaving squad: {error}")
            return None

    async def get_squad_info(self, squad_name):
        try:
            response = self.scraper.get(f"{self.url}/tribes/{squad_name}")
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> getting squad info for {squad_name}: {error}")
            return None

    async def join_squad(self, squad_name):
        try:
            response = self.scraper.post(
                f"{self.url}/tribes/{squad_name}/join"
            )

            if response.status_code == 200:
                if response.text == 'true':
                    return True

                response_json = response.json()
                return response_json
            else:
                raise Exception(f"🚫 <red>Failed</red> to join squad. Status code: {response.status_code}, Message: {response.text}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> joining squad {squad_name}: {error}")
            return None

    async def claim_ref(self, proxy):
        try:
            scraper = cloudscraper.create_scraper()
            proxies = {
                'http': proxy,
                'https': proxy,
                'socks5': proxy
            } if proxy else None

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Origin': 'https://clicker.crashgame247.io',
                'Referer': 'https://clicker.crashgame247.io/',
                "Authorization": self.scraper.headers.get('Authorization'),
                "User-Agent": self.scraper.headers.get('User-Agent')
            }

            while True:
                response = scraper.get(f"{self.url}/user/invitations", headers=headers, proxies=proxies)
                
                if response.status_code != 200:
                    await asyncio.sleep(300)
                    continue

                data = response.json()
                amount = data.get("reward", {}).get("amount", 0)
                next_claim_timestamp = data.get("reward", {}).get("nextClaimTimestamp", 0)

                next_claim_time = datetime.utcfromtimestamp(next_claim_timestamp)
                current_time = datetime.utcnow()

                if next_claim_time > current_time:
                    wait_time = (next_claim_time - current_time).total_seconds()
                    await asyncio.sleep(wait_time)
                    continue

                if amount > 0:
                    await asyncio.sleep(random.uniform(5, 10))

                    claim = scraper.post(
                        f"{self.url}/user/invitations/claim",
                        headers=headers,
                        proxies=proxies
                    )

                    if claim.status_code == 200:
                        reward_data = claim.json()
                        claimed = reward_data.get("rewardAmount")
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ✅ <green>Successfully claimed</green> ref reward. <light-yellow>+{claimed}</light-yellow>")
                    else:
                        logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> claiming ref reward: {claim.status_code}, {claim.text}")
                else:
                    pass

                sleep = random.uniform(1.5, 2) * 24 * 60 * 60
                await asyncio.sleep(sleep)

        except Exception as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error:</red> {e} (claim_ref)")

    async def token_flip(self):
        try:
            while True:
                last_bet_time = self.user_data.get("last_bet_time")
                bet_sleep_time = self.user_data.get("bet_sleep_time", 0)
                current_time = datetime.utcnow()

                if last_bet_time:
                    last_bet_time = datetime.strptime(last_bet_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                    elapsed_time = (current_time - last_bet_time).total_seconds()
                    remaining_sleep_time = max(0, bet_sleep_time - elapsed_time)

                    if remaining_sleep_time > 0:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Waiting for {remaining_sleep_time / 3600:.2f} hours before next token flip.")
                        await asyncio.sleep(remaining_sleep_time)

                side = random.choice(["HEADS", "TAILS"])

                payload = {
                    "side": side,
                    "betAmount": 1000
                }

                response = self.scraper.post(f"{self.url}/tokenflips/bet", json=payload)

                if response.status_code != 200:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> placing bet: {response.status_code}, {response.text}")
                    await asyncio.sleep(random.uniform(1.5, 3))
                    continue

                game_data = response.json().get("game", {})
                active = game_data.get("active", False)
                result = game_data.get("results", [])

                if not active:
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ❌ <red>Lost the bet</red> | Chose: {side} | Result: {result[0] if result else 'Unknown'}")
                else:
                    cashout_response = self.scraper.post(f"{self.url}/tokenflips/cashout")

                    if cashout_response.status_code == 200:
                        cashout_data = cashout_response.json()
                        cashout_amount = cashout_data.get("amountWon", 0)
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ✅ <green>Won the bet</green> | Amount Won: {cashout_amount}")
                    else:
                        logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> cashing out: {cashout_response.status_code}, {cashout_response.text}")

                sleep_time = random.uniform(12 * 60 * 60, 24 * 60 * 60)
                self.user_data["last_bet_time"] = datetime.utcnow().isoformat() + "Z"
                self.user_data["bet_sleep_time"] = sleep_time

                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Sleeping for {sleep_time / 3600:.2f} hours before next token flip.")
                await asyncio.sleep(sleep_time)

        except Exception as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> in TokenFlip | {e}")

    async def send_notification(self, message):
        admin = settings.ADMIN_TG_USER_ID if settings.ADMIN_TG_USER_ID != '' else None
        bot_token = settings.NOTIFICATIONS_BOT_TOKEN if settings.NOTIFICATIONS_BOT_TOKEN else None
        
        if bot_token and admin:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            json = {
                "chat_id": admin,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=json) as response:
                        if response.status == 200:
                            pass
                        else:
                            logger.error(f'<light-yellow>{self.session_name}</light-yellow> | ❌ Failed to send notification: {response.status}')
            except Exception as e:
                logger.error(f'<light-yellow>{self.session_name}</light-yellow> | ❌ Error sending notification: {e}')

    async def upgrade_empire(self, balance):
        try:
            MAX_LEVEL = 4
            TARGET_LEVEL = min(settings.EMPIRE_LEVEL - 1, MAX_LEVEL - 1)

            business_keys = {
                "underground_card_games": "Underground Card Games",
                "slot_machines": "Slot Machines"
            }

            while True:
                businesses_response = self.scraper.get(f"{self.url}/passive/businesses")
                if businesses_response.status_code != 200:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error fetching businesses</red>: {businesses_response.status_code}, {businesses_response.text}")
                    return False

                businesses_data = businesses_response.json().get("businesses", [])
                all_upgraded = True

                for business in businesses_data:
                    key = business.get("key")
                    if key not in business_keys:
                        continue

                    current_level = business.get("level", 0)
                    upgrade_end_time = business.get("upgradeEndTime", 0)

                    if current_level >= TARGET_LEVEL:
                        continue

                    current_time = datetime.now(timezone.utc).timestamp()

                    if upgrade_end_time > current_time:
                        wait_time = max(0, upgrade_end_time - current_time) + random.randint(30, 60)
                        minutes, seconds = divmod(int(wait_time), 60)
                        wait_time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ <blue>Waiting</blue> {wait_time_str} for <blue>{business_keys[key]}</blue> upgrade to complete")
                        await asyncio.sleep(wait_time)
                        all_upgraded = False
                        continue

                    next_level = business.get("nextLevel", {})
                    upgrade_cost = next_level.get("upgradeCost", 0)

                    if balance < upgrade_cost:
                        logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ <red>Insufficient balance</red> ({balance}) for next upgrade of <blue>{business_keys[key]}</blue>. Required: {upgrade_cost}")
                        return False

                    upgrade_payload = {"key": key}
                    upgrade_response = self.scraper.post(f"{self.url}/passive/businesses/upgrade", json=upgrade_payload)

                    if upgrade_response.status_code != 200:
                        logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error upgrading</red> <blue>{business_keys[key]}</blue>: {upgrade_response.status_code}, {upgrade_response.text}")
                        return False

                    balance -= upgrade_cost
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🔼 <green>Upgraded</green> <blue>{business_keys[key]}</blue> to level <yellow>{current_level + 2}</yellow>. <red>Cost</red>: {upgrade_cost}. <green>Remaining balance</green>: {balance}")

                    all_upgraded = False

                if all_upgraded:
                    break

            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🏆 <green>All businesses upgraded to target level {TARGET_LEVEL + 1}</green>")
            self.user_data["upgraded_empire"] = True
            return True

        except Exception as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> in Empire function | {e}")
            return False

    async def claim_empire(self):
        try:
            while True:
                news_response = self.scraper.get(f"{self.url}/passive/news")

                if news_response.status_code != 200:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error fetching news</red>: {news_response.status_code}, {news_response.text}")
                    await asyncio.sleep(60)
                    continue

                news_data = news_response.json()
                updates = news_data.get("updates", [])

                for update in updates:
                    update_type = update.get("type")
                    key = update.get("key")

                    if update_type == "CLAIM":
                        claim_payload = {"key": key}
                        claim_response = self.scraper.post(f"{self.url}/passive/businesses/claim", json=claim_payload)

                        if claim_response.status_code == 200:
                            income = update.get("income", 0)
                            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💰 <green>Claimed</green> <yellow>{income}</yellow> from <blue>{key}</blue>")
                        else:
                            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error claiming</red> <blue>{key}</blue>: {claim_response.status_code}, {claim_response.text}")

                    elif update_type == "RESOLVE" and settings.AUTO_RESOLVE_EMPIRE:
                        event = update.get("event")
                        resolve_payload = {"key": key}
                        resolve_response = self.scraper.post(f"{self.url}/passive/businesses/resolve", json=resolve_payload)

                        if resolve_response.status_code == 200:
                            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🔧 <green>Resolved</green> event <blue>{event}</blue> for <yellow>{key}</yellow>")
                        else:
                            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error resolving</red> <blue>{key}</blue>: {resolve_response.status_code}, {resolve_response.text}")

                    elif update_type == "RENEW" and update.get("itemType") == "license" and settings.AUTO_RENEW_LICENSE:
                        renew_payload = {"key": key}
                        renew_response = self.scraper.post(f"{self.url}/passive/licenses/renew", json=renew_payload)

                        if renew_response.status_code == 200:
                            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 📄 <green>Renewed</green> license for <blue>{key}</blue>")
                        else:
                            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error renewing</red> <blue>{key}</blue>: {renew_response.status_code}, {renew_response.text}")

                await asyncio.sleep(random.randint(30, 50) * 60)

        except Exception as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> in ClaimEmpire function | {e}")

    async def run(self, proxy: str | None) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Bot will start in <ly>{random_delay}s</ly>")
            await asyncio.sleep(random_delay)

        self.scraper = cloudscraper.create_scraper()
        self.scraper.headers = headers
        self.scraper.headers['Sec-Ch-Ua'] = get_sec_ch_ua(headers["User-Agent"])

        if proxy:
            proxies = {
                'http': proxy,
                'https': proxy,
                'socks5': proxy
            }
            self.scraper.proxies.update(proxies)
            await self.check_proxy(proxy)

        init_data = await self.get_tg_web_data(proxy)

        while True:
            login = await self.login(init_data=init_data)

            if login is not None:
                token, banned, balance, streak, last_login, referrer, tasks, nanoid, flappy_score, dino_score, wallet = login
                self.user_data["balance"] = balance
                self.user_data["streak"] = streak
                self.user_data["acc_ref_id"] = nanoid
                self.user_data["flappy_score"] = flappy_score
                self.user_data["dino_score"] = dino_score
                self.save_user_data()
                break
            else:
                logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                await asyncio.sleep(30)

        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💰 Balance: <yellow>{balance}</yellow> | ⚡️ Current streak: <cyan>{streak}</cyan>")
        self.scraper.headers["Authorization"] = f"Bearer {token}"

        if banned:
            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | 😨 You are <red>banned...</red>")
            self.user_data["banned"] = True
            self.save_user_data()
            await asyncio.sleep(999999999999)
        else:
            self.user_data["banned"] = False
            self.save_user_data()

        if self.user_data["referred"] == "gold" and not self.user_data["acknowledged"]:
            self.user_data["acknowledged"] = True
            self.save_user_data()
            if referrer:
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🤗 Referred By: @{referrer}")

        if not self.user_data.get("registered_in_@whale"):
            await self.get_whale_link()

        if settings.NIGHT_MODE:
            current_time = datetime.now(timezone.utc).time()
            night_start = datetime.strptime("22:00", "%H:%M").time()
            night_end = datetime.strptime("06:00", "%H:%M").time()

            if night_start <= current_time or current_time < night_end:
                now = datetime.now(timezone.utc)
                if current_time >= night_start:
                    next_morning = now + timedelta(days=1)
                    next_morning = next_morning.replace(hour=6, minute=0, second=0, microsecond=0)
                else:
                    next_morning = now.replace(hour=6, minute=0, second=0, microsecond=0)

                sleep_duration = (next_morning - now).total_seconds()
                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🌙 It's night time! Sleeping until <cyan>06:00 UTC</cyan> (~{int(sleep_duration // 3600)} hours)")
                await asyncio.sleep(sleep_duration)

        squad_name = settings.SQUAD_NAME if settings.SQUAD_NAME != '' else False
        if squad_name:
            current_squad = await self.get_my_squad()

            if current_squad != squad_name:
                if current_squad:
                    leave = await self.leave_from_squad()
                    if leave:
                        logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ Successfully <red>left</red> the squad: {current_squad}")
                    else:
                        logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😔 <red>Failed</red> to leave the current squad: {current_squad}")
                
                squad_info = await self.get_squad_info(squad_name=settings.SQUAD_NAME)
                if squad_info:
                    squad_name = squad_info.get("name")
                    if squad_name:
                        join = await self.join_squad(squad_name=settings.SQUAD_NAME)
                        if join:
                            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ Successfully <green>joined squad</green>: {squad_name}")
                            self.user_data["squad_name"] = squad_name
                            self.user_data["in_squad"] = True
                            self.save_user_data()
                        else:
                            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😔 <red>Failed</red> to join squad: {squad_name}")

        if settings.AUTO_CONNECT_WALLETS:
            if not wallet:
                connect = await connector.connect_wallet(self.session_name, self.scraper)
                if connect:
                    self.user_data["wallet_connected"] = True
                    await self.verify("CONNECT_WALLET")

        if settings.RECONNECT_WALLETS:
            if wallet:
                await connector.connect_wallet(self.session_name, self.scraper)
                if not "CONNECT_WALLET" in tasks:
                    await self.verify("CONNECT_WALLET")

        if settings.AUTO_TASKS:
            await self.complete_tasks(tasks)

        if settings.AUTO_TAP:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 😋 Starting <green>AutoTapper...</green>")
            asyncio.create_task(self.clicker(proxy))

        if settings.AUTO_TOKENFLIP:
            asyncio.create_task(self.token_flip())

        if settings.AUTO_CLAIM_REF_REWARD:
            asyncio.create_task(self.claim_ref(proxy))

        if settings.AUTO_EMPIRE:
            upgrade = await self.upgrade_empire(balance)
            if upgrade:
                asyncio.create_task(self.claim_empire())

        while True:
            try:
                if last_login is not None:
                    last_login_time = datetime.strptime(last_login, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                else:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 Last login data is <red>None</red> (please try restarting the bot)")

                if datetime.now(timezone.utc) - last_login_time > timedelta(hours=24):
                    while True:
                        refresh = await self.refresh_tokens(proxy)
                        
                        if refresh is not None:
                            token, wsToken, wsSubToken, id_for_ws = refresh
                            self.scraper.headers.update({'Authorization': f'Bearer {token}'})
                            break
                        else:
                            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                            await asyncio.sleep(30)
                    await self.claim_daily_bonus()

                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 😴 Going <cyan>sleep</cyan> 8h (This doesn't concern the AutoTapper)")

                await asyncio.sleep(8 * 3600)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | 🚫 Unknown <red>error</red>: {error} (Try restarting the bot..)")
                await asyncio.sleep(300)

            except KeyboardInterrupt:
                logger.warning("<r>Bot stopped by user...</r>")
            finally:
                if self.scraper is not None:
                    self.scraper.close()

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | 🚫 <red>Invalid</red> Session")