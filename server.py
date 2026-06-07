#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import csv
import datetime as dt
import hashlib
import json
import os
import secrets
import sqlite3
import socket
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("BENYI_DATA_DIR") or os.environ.get("RENDER_DISK_PATH") or (BASE_DIR / "data"))
DB_PATH = DATA_DIR / "benyi_v2.sqlite"
HOST = os.environ.get("BENYI_HOST", "0.0.0.0")
PORT = int(os.environ.get("BENYI_PORT", "8000"))
SESSION_COOKIE = "benyi_session"
SESSIONS = {}


ROLES = {
    "admin": "老板",
    "operation_manager": "运营负责人",
    "school_owner": "学校负责人",
    "clerk": "文员",
    "viewer": "只读",
}

SCHOOL_TYPES = ["小学", "初中", "高中", "九年一贯制", "职高", "中专", "幼儿园", "其他"]
SCHOOL_PRIORITIES = ["S级", "A级", "B级", "C级"]
SCHOOL_STATUSES = ["未启动", "已整理资料", "已发内容", "评论区有反馈", "已私信", "已加企微", "已建群", "已到店试穿", "已成交", "暂停"]
MAIN_PRODUCTS = ["校服", "书皮", "文具", "作业本", "演出服", "班服", "研学用品", "其他"]
UGC_TYPES = ["校服试穿", "校服穿搭", "学生投稿", "推荐官招募", "旧衣交换", "困难学生领取", "班级团购", "校园话题挑战", "其他"]
UGC_STATUSES = ["策划中", "物料准备中", "预热中", "进行中", "已结束", "复盘中", "暂停"]


SCHOOL_CSV_FIELDS = [
    ("school_name", "学校名称"),
    ("school_type", "学校类型"),
    ("area", "区域"),
    ("address", "地址"),
    ("student_count", "学生规模"),
    ("owner_name", "负责人"),
    ("priority", "优先级"),
    ("status", "当前推进状态"),
    ("wechat_count", "企微人数"),
    ("trial_count", "到店试穿人数"),
    ("order_count", "成交人数"),
    ("revenue", "成交金额"),
    ("main_product", "主推品类"),
    ("main_sizes", "主流尺码"),
    ("next_action", "下一步动作"),
    ("next_follow_up_time", "下次跟进时间"),
    ("notes", "备注"),
    ("created_at", "创建时间"),
    ("updated_at", "更新时间"),
]

UGC_CSV_FIELDS = [
    ("activity_name", "活动名称"),
    ("school_name", "对应学校"),
    ("activity_type", "活动类型"),
    ("status", "活动状态"),
    ("goal", "活动目标"),
    ("start_date", "活动开始日期"),
    ("end_date", "活动结束日期"),
    ("owner_name", "负责人"),
    ("budget", "预算"),
    ("signup_count", "报名人数"),
    ("submission_count", "投稿人数"),
    ("content_count", "产出内容数"),
    ("views_count", "总播放量"),
    ("likes_count", "总点赞量"),
    ("comments_count", "总评论量"),
    ("new_wechat_count", "新增企微人数"),
    ("order_count", "带来成交人数"),
    ("revenue", "带来成交金额"),
    ("current_issue", "当前问题"),
    ("next_action", "下一步动作"),
    ("next_follow_up_time", "下次跟进时间"),
    ("review_summary", "复盘结论"),
    ("created_at", "创建时间"),
    ("updated_at", "更新时间"),
]

STORE_CSV_FIELDS = [
    ("report_date", "日期"),
    ("store_name", "门店"),
    ("reporter_name", "填报人"),
    ("new_members", "新增会员"),
    ("online_inquiries", "线上询单"),
    ("offline_visits", "线下到店"),
    ("orders_count", "成交订单"),
    ("sales_amount", "今日销售额"),
    ("monthly_sales_target", "月度销售目标"),
    ("conversion_rate", "成交率"),
    ("month_sales_total", "本月累计销售额"),
    ("target_completion_rate", "月度目标完成率"),
    ("notes", "备注"),
    ("created_at", "创建时间"),
    ("updated_at", "更新时间"),
]

WORK_CSV_FIELDS = [
    ("work_date", "日期"),
    ("employee_name", "员工姓名"),
    ("completed_items", "今日完成事项"),
    ("followed_schools", "跟进学校"),
    ("follow_customer_count", "跟进客户数"),
    ("new_wechat_count", "新增企微数"),
    ("ugc_progress", "UGC推进情况"),
    ("issues", "遇到问题"),
    ("tomorrow_plan", "明日计划"),
    ("need_boss_support", "需要老板协调事项"),
    ("created_at", "创建时间"),
    ("updated_at", "更新时间"),
]


def now_string():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_string():
    return dt.date.today().strftime("%Y-%m-%d")


def month_string():
    return dt.date.today().strftime("%Y-%m")


def add_days(days):
    return (dt.date.today() + dt.timedelta(days=days)).strftime("%Y-%m-%d")


def month_bounds(month):
    month = text(month) or month_string()
    try:
        start = dt.date.fromisoformat(month + "-01")
    except ValueError:
        start = dt.date.today().replace(day=1)
    if start.month == 12:
        end = dt.date(start.year + 1, 1, 1)
    else:
        end = dt.date(start.year, start.month + 1, 1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), start.strftime("%Y-%m")


def lan_ips():
    found = set()
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        found.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = item[4][0]
            if ip and not ip.startswith("127."):
                found.add(ip)
    except OSError:
        pass
    return sorted(found)


def hash_password(password):
    salt = secrets.token_bytes(16)
    iterations = 180000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password, password_hash):
    try:
        scheme, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return secrets.compare_digest(expected, actual)
    except Exception:
        return False


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def dict_row(row):
    return dict(row) if row else None


def execute(sql, params=()):
    with db() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def query_one(sql, params=()):
    with db() as conn:
        return dict_row(conn.execute(sql, params).fetchone())


def query_all(sql, params=()):
    with db() as conn:
        return [dict_row(row) for row in conn.execute(sql, params).fetchall()]


def text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def number(value, default=0):
    if value in (None, ""):
        return default
    try:
        return max(0, float(value))
    except (TypeError, ValueError):
        return default


def integer(value, default=0):
    return int(round(number(value, default)))


def choice(value, options, default):
    value = text(value)
    return value if value in options else default


def ratio(numerator, denominator):
    denominator = float(denominator or 0)
    return 0 if denominator <= 0 else float(numerator or 0) / denominator


def get_user(user_id):
    if not user_id:
        return None
    return query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def owner_from_input(value, fallback_user=None):
    value = text(value)
    if value:
        if value.isdigit():
            user = query_one("SELECT id, name FROM users WHERE id = ?", (int(value),))
        else:
            user = query_one("SELECT id, name FROM users WHERE username = ? OR name = ? ORDER BY id LIMIT 1", (value, value))
        if user:
            return user["id"], user["name"]
    if fallback_user:
        return fallback_user["id"], fallback_user["name"]
    return None, ""


def school_from_input(value):
    value = text(value)
    if not value:
        return None, ""
    if value.isdigit():
        school = query_one("SELECT id, school_name FROM schools WHERE id = ?", (int(value),))
    else:
        school = query_one("SELECT id, school_name FROM schools WHERE school_name = ? LIMIT 1", (value,))
    if school:
        return school["id"], school["school_name"]
    return None, value


def row_count(table_name):
    return query_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]


def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                phone TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'enabled',
                password_hash TEXT NOT NULL,
                password_changed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            );

            CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_name TEXT NOT NULL,
                school_type TEXT NOT NULL,
                area TEXT DEFAULT '朝阳市',
                address TEXT DEFAULT '',
                student_count INTEGER DEFAULT 0,
                owner_id INTEGER,
                owner_name TEXT DEFAULT '',
                priority TEXT DEFAULT 'B级',
                status TEXT DEFAULT '未启动',
                wechat_count INTEGER DEFAULT 0,
                trial_count INTEGER DEFAULT 0,
                order_count INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                main_product TEXT DEFAULT '校服',
                main_sizes TEXT DEFAULT '',
                next_action TEXT DEFAULT '',
                next_follow_up_time TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ugc_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_name TEXT NOT NULL,
                school_id INTEGER,
                school_name TEXT DEFAULT '',
                activity_type TEXT NOT NULL,
                status TEXT NOT NULL,
                goal TEXT DEFAULT '',
                start_date TEXT DEFAULT '',
                end_date TEXT DEFAULT '',
                owner_id INTEGER,
                owner_name TEXT DEFAULT '',
                budget REAL DEFAULT 0,
                signup_count INTEGER DEFAULT 0,
                submission_count INTEGER DEFAULT 0,
                content_count INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                likes_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                new_wechat_count INTEGER DEFAULT 0,
                order_count INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                current_issue TEXT DEFAULT '',
                next_action TEXT DEFAULT '',
                next_follow_up_time TEXT DEFAULT '',
                review_summary TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS store_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date TEXT NOT NULL,
                store_name TEXT NOT NULL DEFAULT '本亦门店',
                reporter_id INTEGER,
                reporter_name TEXT DEFAULT '',
                new_members INTEGER DEFAULT 0,
                online_inquiries INTEGER DEFAULT 0,
                offline_visits INTEGER DEFAULT 0,
                orders_count INTEGER DEFAULT 0,
                sales_amount REAL DEFAULT 0,
                monthly_sales_target REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(report_date, store_name)
            );

            CREATE TABLE IF NOT EXISTS work_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_date TEXT NOT NULL,
                employee_id INTEGER,
                employee_name TEXT DEFAULT '',
                completed_items TEXT DEFAULT '',
                followed_schools TEXT DEFAULT '',
                follow_customer_count INTEGER DEFAULT 0,
                new_wechat_count INTEGER DEFAULT 0,
                ugc_progress TEXT DEFAULT '',
                issues TEXT DEFAULT '',
                tomorrow_plan TEXT DEFAULT '',
                need_boss_support TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(work_date, employee_id)
            );
            """
        )
        conn.commit()
    seed_defaults()


def seed_defaults():
    if row_count("users") == 0:
        admin_password = os.environ.get("BENYI_ADMIN_PASSWORD", "admin123")
        staff_password = os.environ.get("BENYI_DEFAULT_STAFF_PASSWORD", "123456")
        users = [
            ("老板", "admin", "admin", "", admin_password),
            ("轻松", "qingsong", "operation_manager", "", staff_password),
            ("王文芳", "wangwenfang", "school_owner", "", staff_password),
            ("谢秀平", "xiexiu-ping", "school_owner", "", staff_password),
            ("文员", "clerk", "clerk", "", staff_password),
        ]
        for name, username, role, phone, password in users:
            execute(
                "INSERT INTO users (name, username, role, phone, status, password_hash, password_changed, created_at) VALUES (?, ?, ?, ?, 'enabled', ?, 0, ?)",
                (name, username, role, phone, hash_password(password), now_string()),
            )

    users = {u["username"]: u for u in query_all("SELECT id, username, name FROM users")}

    if row_count("schools") == 0:
        samples = [
            ("朝阳示例小学一", "小学", "双塔区示例路 1 号", 860, "clerk", "A级", "未启动", 0, 0, 0, 0, "校服", "130-180", "整理学校基础信息，准备第一条校服内容", add_days(-3), "示例数据，可编辑。"),
            ("朝阳示例小学二", "小学", "龙城区示例街 18 号", 1120, "qingsong", "B级", "已发内容", 18, 0, 0, 0, "书皮", "130-170", "复盘评论区反馈，挑出 5 个家长继续私信", today_string(), "今天需要看内容反馈。"),
            ("朝阳示例初中一", "初中", "双塔区示例南街 6 号", 1500, "xiexiu-ping", "S级", "已加企微", 76, 12, 5, 6400, "校服", "150-185", "安排尺码表私域群发，推动到店试穿", add_days(2), "企微增长不错。"),
            ("朝阳示例初中二", "初中", "龙城区示例北路 9 号", 980, "wangwenfang", "A级", "已到店试穿", 54, 28, 13, 16800, "校服", "150-190", "给试穿未下单家长做二次提醒", add_days(6), "试穿转化率有提升空间。"),
            ("朝阳示例高中一", "高中", "朝阳县示例大道 11 号", 2100, "qingsong", "S级", "已成交", 132, 66, 39, 52800, "校服", "S-XXL", "重点追单高一新生家长，准备补货尺码", add_days(-1), "高价值学校。"),
            ("朝阳示例高中二", "高中", "北票示例路 22 号", 1750, "admin", "A级", "已成交", 96, 48, 44, 61200, "班服", "S-XXL", "维护复购关系，后续切入班服和演出服", add_days(10), "成交学校示例。"),
        ]
        for row in samples:
            owner = users[row[4]]
            execute(
                """
                INSERT INTO schools
                (school_name, school_type, area, address, student_count, owner_id, owner_name, priority, status, wechat_count,
                 trial_count, order_count, revenue, main_product, main_sizes, next_action, next_follow_up_time, notes, created_at, updated_at)
                VALUES (?, ?, '朝阳市', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row[0], row[1], row[2], row[3], owner["id"], owner["name"], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], now_string(), now_string()),
            )

    schools = {s["school_name"]: s for s in query_all("SELECT id, school_name FROM schools")}

    if row_count("ugc_activities") == 0:
        samples = [
            ("开学季校服试穿打卡", "朝阳示例初中一", "校服试穿", "进行中", "收集真实试穿反馈，导入企微", add_days(-5), add_days(10), "qingsong", 3000, 45, 18, 22, 12800, 460, 78, 36, 8, 9600, "投稿节奏不稳", "安排班级推荐官补拍短视频", add_days(1), ""),
            ("高中校服穿搭挑战", "朝阳示例高中一", "校服穿搭", "预热中", "带动高一新生家长咨询", today_string(), add_days(14), "wangwenfang", 1800, 20, 7, 9, 8600, 230, 41, 18, 4, 5200, "缺少男生版内容", "补一组男生尺码素材", add_days(3), ""),
            ("幼儿园文具包投稿", "朝阳示例小学二", "学生投稿", "策划中", "测试非校服品类互动", add_days(7), add_days(21), "xiexiu-ping", 900, 0, 0, 0, 0, 0, 0, 0, 0, 0, "规则未确定", "确认奖品和投稿模板", add_days(4), ""),
            ("旧衣交换公益日", "朝阳示例高中二", "旧衣交换", "复盘中", "沉淀公益口碑", add_days(-25), add_days(-10), "admin", 1200, 72, 31, 28, 22600, 940, 156, 52, 6, 7800, "复盘材料未整理", "整理活动照片和成交来源", add_days(-2), ""),
        ]
        for row in samples:
            owner = users[row[7]]
            school = schools.get(row[1])
            execute(
                """
                INSERT INTO ugc_activities
                (activity_name, school_id, school_name, activity_type, status, goal, start_date, end_date, owner_id, owner_name,
                 budget, signup_count, submission_count, content_count, views_count, likes_count, comments_count, new_wechat_count,
                 order_count, revenue, current_issue, next_action, next_follow_up_time, review_summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row[0], school["id"] if school else None, row[1], row[2], row[3], row[4], row[5], row[6], owner["id"], owner["name"], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], now_string(), now_string()),
            )

    if row_count("store_reports") == 0:
        reporter = users.get("xiexiu-ping") or users["admin"]
        for offset, sales in [(-2, 2860), (-1, 4120), (0, 3680)]:
            execute(
                """
                INSERT INTO store_reports
                (report_date, store_name, reporter_id, reporter_name, new_members, online_inquiries, offline_visits, orders_count,
                 sales_amount, monthly_sales_target, notes, created_at, updated_at)
                VALUES (?, '本亦门店', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (add_days(offset), reporter["id"], reporter["name"], 6 + offset + 2, 18 + offset + 2, 11 + offset + 2, 4 + offset + 2, sales, 120000, "示例门店日报", now_string(), now_string()),
            )

    if row_count("work_summaries") == 0:
        for username in ["qingsong", "wangwenfang", "xiexiu-ping", "clerk"]:
            user = users[username]
            execute(
                """
                INSERT INTO work_summaries
                (work_date, employee_id, employee_name, completed_items, followed_schools, follow_customer_count, new_wechat_count,
                 ugc_progress, issues, tomorrow_plan, need_boss_support, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (today_string(), user["id"], user["name"], "完成学校资料整理和家长跟进", "朝阳示例小学二、朝阳示例高中一", 12, 5, "推进 UGC 素材收集", "暂无", "继续跟进重点学校", "", now_string(), now_string()),
            )


def sanitize_user(user):
    if not user:
        return None
    return {
        "id": user["id"],
        "name": user["name"],
        "username": user["username"],
        "role": user["role"],
        "roleLabel": ROLES.get(user["role"], user["role"]),
        "phone": user.get("phone", ""),
        "status": user["status"],
        "passwordChanged": bool(user.get("password_changed")),
        "createdAt": user.get("created_at"),
        "lastLoginAt": user.get("last_login_at"),
    }


def can_create(user):
    return user["role"] in {"admin", "operation_manager", "clerk", "school_owner"}


def can_delete(user):
    return user["role"] == "admin"


def can_manage_users(user):
    return user["role"] == "admin"


def can_import(user):
    return user["role"] in {"admin", "operation_manager", "clerk"}


def can_view_finance(user):
    return user["role"] != "clerk"


def can_view_all_staff(user):
    return user["role"] in {"admin", "operation_manager", "viewer"}


def can_edit_owned(user, record, owner_id_key="owner_id", owner_name_key="owner_name"):
    if user["role"] in {"admin", "operation_manager"}:
        return True
    if user["role"] == "clerk":
        return True
    if user["role"] == "school_owner":
        return record and (record.get(owner_id_key) == user["id"] or record.get(owner_name_key) == user["name"])
    return False


def visible_schools(user):
    rows = query_all("SELECT * FROM schools ORDER BY updated_at DESC, id DESC")
    if user["role"] == "school_owner":
        rows = [row for row in rows if row.get("owner_id") == user["id"] or row.get("owner_name") == user["name"]]
    return rows


def visible_ugc(user):
    rows = query_all("SELECT * FROM ugc_activities ORDER BY updated_at DESC, id DESC")
    if user["role"] == "school_owner":
        rows = [row for row in rows if row.get("owner_id") == user["id"] or row.get("owner_name") == user["name"]]
    return rows


def visible_store_reports(user, filters=None):
    rows = query_all("SELECT * FROM store_reports ORDER BY report_date DESC, id DESC")
    filters = filters or {}
    if not can_view_all_staff(user) and user["role"] != "clerk":
        rows = [row for row in rows if row.get("reporter_id") == user["id"] or row.get("reporter_name") == user["name"]]
    if filters.get("date"):
        rows = [row for row in rows if row["report_date"] == filters["date"]]
    if filters.get("month"):
        rows = [row for row in rows if row["report_date"].startswith(filters["month"])]
    return rows


def visible_work_summaries(user, filters=None):
    rows = query_all("SELECT * FROM work_summaries ORDER BY work_date DESC, id DESC")
    filters = filters or {}
    if not can_view_all_staff(user):
        rows = [row for row in rows if row.get("employee_id") == user["id"] or row.get("employee_name") == user["name"]]
    if filters.get("employee_id"):
        rows = [row for row in rows if str(row["employee_id"]) == str(filters["employee_id"])]
    if filters.get("date"):
        rows = [row for row in rows if row["work_date"] == filters["date"]]
    if filters.get("month"):
        rows = [row for row in rows if row["work_date"].startswith(filters["month"])]
    return rows


def enrich_school(row, user):
    item = dict(row)
    item["conversion_rate"] = ratio(item["order_count"], item["wechat_count"])
    item["canEdit"] = can_edit_owned(user, item)
    item["canDelete"] = can_delete(user)
    if not can_view_finance(user):
        item["revenue"] = None
    return item


def enrich_ugc(row, user):
    item = dict(row)
    item["canEdit"] = can_edit_owned(user, item)
    item["canDelete"] = can_delete(user)
    if not can_view_finance(user):
        item["budget"] = None
        item["revenue"] = None
    return item


def enrich_store_report(row, user):
    item = dict(row)
    start, end, month = month_bounds(item["report_date"][:7])
    month_rows = query_all("SELECT * FROM store_reports WHERE report_date >= ? AND report_date < ? AND store_name = ?", (start, end, item["store_name"]))
    month_total = sum(row["sales_amount"] for row in month_rows)
    target = item["monthly_sales_target"] or 0
    item["conversion_rate"] = ratio(item["orders_count"], item["offline_visits"])
    item["month_sales_total"] = month_total
    item["target_completion_rate"] = ratio(month_total, target)
    item["canEdit"] = user["role"] in {"admin", "operation_manager", "clerk"} or item["reporter_id"] == user["id"]
    item["canDelete"] = can_delete(user)
    if not can_view_finance(user):
        item["sales_amount"] = None
        item["monthly_sales_target"] = None
        item["month_sales_total"] = None
        item["target_completion_rate"] = None
    return item


def enrich_work_summary(row, user):
    item = dict(row)
    item["canEdit"] = user["role"] in {"admin", "operation_manager"} or item["employee_id"] == user["id"]
    item["canDelete"] = can_delete(user)
    return item


def employee_rows():
    return query_all("SELECT * FROM users WHERE status = 'enabled' AND role != 'viewer' AND role != 'admin' ORDER BY id")


def dashboard(user):
    today = today_string()
    month = month_string()
    schools = visible_schools(user)
    ugc = visible_ugc(user)
    reports = visible_store_reports(user, {"month": month})
    today_reports = [row for row in reports if row["report_date"] == today]
    work_today = visible_work_summaries(user, {"date": today})
    employees = employee_rows()
    submitted_ids = {row["employee_id"] for row in work_today}
    active_school_statuses = set(SCHOOL_STATUSES) - {"暂停"}
    wechat_total = sum(row["wechat_count"] for row in schools)
    order_total = sum(row["order_count"] for row in schools)

    current_month_ugc = [row for row in ugc if text(row["start_date"]).startswith(month) or text(row["created_at"]).startswith(month)]
    store_sales = sum(row["sales_amount"] for row in reports)
    store_orders = sum(row["orders_count"] for row in reports)
    store_visits = sum(row["offline_visits"] for row in reports)
    latest_target = max([row["monthly_sales_target"] for row in reports], default=0)

    return {
        "school": {
            "schoolTotal": len(schools),
            "sLevelCount": sum(1 for row in schools if row["priority"] == "S级"),
            "wechatTotal": wechat_total,
            "orderTotal": order_total,
            "revenueTotal": sum(row["revenue"] for row in schools) if can_view_finance(user) else None,
            "averageConversion": ratio(order_total, wechat_total),
            "todayFollowups": sum(1 for row in schools if row["next_follow_up_time"] == today and row["status"] in active_school_statuses),
            "overdueFollowups": sum(1 for row in schools if row["next_follow_up_time"] and row["next_follow_up_time"] < today and row["status"] in active_school_statuses),
        },
        "ugc": {
            "activeCount": sum(1 for row in ugc if row["status"] == "进行中"),
            "planningCount": sum(1 for row in ugc if row["status"] == "策划中"),
            "monthSignup": sum(row["signup_count"] for row in current_month_ugc),
            "monthSubmission": sum(row["submission_count"] for row in current_month_ugc),
            "monthContent": sum(row["content_count"] for row in current_month_ugc),
            "monthViews": sum(row["views_count"] for row in current_month_ugc),
            "newWechat": sum(row["new_wechat_count"] for row in ugc),
            "revenue": sum(row["revenue"] for row in ugc) if can_view_finance(user) else None,
            "reviewOverdue": sum(1 for row in ugc if row["next_follow_up_time"] and row["next_follow_up_time"] < today and row["status"] in {"已结束", "复盘中"} and not text(row["review_summary"])),
        },
        "store": {
            "todayNewMembers": sum(row["new_members"] for row in today_reports),
            "todayOnlineInquiries": sum(row["online_inquiries"] for row in today_reports),
            "todayOfflineVisits": sum(row["offline_visits"] for row in today_reports),
            "todayOrders": sum(row["orders_count"] for row in today_reports),
            "todaySales": sum(row["sales_amount"] for row in today_reports) if can_view_finance(user) else None,
            "monthSales": store_sales if can_view_finance(user) else None,
            "monthOrders": store_orders,
            "monthOfflineVisits": store_visits,
            "monthConversion": ratio(store_orders, store_visits),
            "targetCompletion": ratio(store_sales, latest_target) if can_view_finance(user) else None,
        },
        "work": {
            "submitted": [row["employee_name"] for row in work_today],
            "notSubmitted": [row["name"] for row in employees if row["id"] not in submitted_ids],
        },
    }


def monthly_summary(user, month):
    start, end, month = month_bounds(month)
    reports = visible_store_reports(user, {"month": month})
    work = visible_work_summaries(user, {"month": month})
    ugc = [row for row in visible_ugc(user) if text(row["start_date"]).startswith(month) or text(row["created_at"]).startswith(month)]
    total_sales = sum(row["sales_amount"] for row in reports)
    total_orders = sum(row["orders_count"] for row in reports)
    total_visits = sum(row["offline_visits"] for row in reports)
    latest_target = max([row["monthly_sales_target"] for row in reports], default=0)

    employee_map = {}
    for row in work:
        key = row["employee_id"] or row["employee_name"]
        if key not in employee_map:
            employee_map[key] = {
                "employee_name": row["employee_name"],
                "submit_days": 0,
                "new_wechat_count": 0,
                "follow_customer_count": 0,
                "completed_items": [],
                "ugc_progress": [],
            }
        employee_map[key]["submit_days"] += 1
        employee_map[key]["new_wechat_count"] += row["new_wechat_count"]
        employee_map[key]["follow_customer_count"] += row["follow_customer_count"]
        if text(row["completed_items"]):
            employee_map[key]["completed_items"].append(row["completed_items"])
        if text(row["ugc_progress"]):
            employee_map[key]["ugc_progress"].append(row["ugc_progress"])

    return {
        "month": month,
        "store": {
            "totalSales": total_sales if can_view_finance(user) else None,
            "totalOrders": total_orders,
            "totalOfflineVisits": total_visits,
            "conversionRate": ratio(total_orders, total_visits),
            "targetCompletionRate": ratio(total_sales, latest_target) if can_view_finance(user) else None,
        },
        "employees": list(employee_map.values()),
        "ugc": {
            "activityCount": len(ugc),
            "activeCount": sum(1 for row in ugc if row["status"] == "进行中"),
            "submissionCount": sum(row["submission_count"] for row in ugc),
            "contentCount": sum(row["content_count"] for row in ugc),
            "viewsCount": sum(row["views_count"] for row in ugc),
            "newWechatCount": sum(row["new_wechat_count"] for row in ugc),
            "summary": [f"{row['activity_name']}：{row['status']}，下一步 {row['next_action'] or '未填写'}" for row in ugc[:12]],
        },
    }


def validate_school(data, user):
    owner_id, owner_name = owner_from_input(data.get("owner_id") or data.get("owner_name"), user)
    return {
        "school_name": text(data.get("school_name")) or "未命名学校",
        "school_type": choice(data.get("school_type"), SCHOOL_TYPES, "其他"),
        "area": text(data.get("area"), "朝阳市") or "朝阳市",
        "address": text(data.get("address")),
        "student_count": integer(data.get("student_count")),
        "owner_id": owner_id,
        "owner_name": owner_name,
        "priority": choice(data.get("priority"), SCHOOL_PRIORITIES, "B级"),
        "status": choice(data.get("status"), SCHOOL_STATUSES, "未启动"),
        "wechat_count": integer(data.get("wechat_count")),
        "trial_count": integer(data.get("trial_count")),
        "order_count": integer(data.get("order_count")),
        "revenue": number(data.get("revenue")),
        "main_product": choice(data.get("main_product"), MAIN_PRODUCTS, "校服"),
        "main_sizes": text(data.get("main_sizes")),
        "next_action": text(data.get("next_action")),
        "next_follow_up_time": text(data.get("next_follow_up_time")),
        "notes": text(data.get("notes")),
    }


def validate_ugc(data, user):
    owner_id, owner_name = owner_from_input(data.get("owner_id") or data.get("owner_name"), user)
    school_id, school_name = school_from_input(data.get("school_id") or data.get("school_name"))
    return {
        "activity_name": text(data.get("activity_name")) or "未命名活动",
        "school_id": school_id,
        "school_name": school_name,
        "activity_type": choice(data.get("activity_type"), UGC_TYPES, "其他"),
        "status": choice(data.get("status"), UGC_STATUSES, "策划中"),
        "goal": text(data.get("goal")),
        "start_date": text(data.get("start_date")),
        "end_date": text(data.get("end_date")),
        "owner_id": owner_id,
        "owner_name": owner_name,
        "budget": number(data.get("budget")),
        "signup_count": integer(data.get("signup_count")),
        "submission_count": integer(data.get("submission_count")),
        "content_count": integer(data.get("content_count")),
        "views_count": integer(data.get("views_count")),
        "likes_count": integer(data.get("likes_count")),
        "comments_count": integer(data.get("comments_count")),
        "new_wechat_count": integer(data.get("new_wechat_count")),
        "order_count": integer(data.get("order_count")),
        "revenue": number(data.get("revenue")),
        "current_issue": text(data.get("current_issue")),
        "next_action": text(data.get("next_action")),
        "next_follow_up_time": text(data.get("next_follow_up_time")),
        "review_summary": text(data.get("review_summary")),
    }


def validate_store(data, user):
    reporter_id, reporter_name = owner_from_input(data.get("reporter_id") or data.get("reporter_name"), user)
    if user["role"] == "school_owner":
        reporter_id, reporter_name = user["id"], user["name"]
    return {
        "report_date": text(data.get("report_date")) or today_string(),
        "store_name": text(data.get("store_name")) or "本亦门店",
        "reporter_id": reporter_id,
        "reporter_name": reporter_name,
        "new_members": integer(data.get("new_members")),
        "online_inquiries": integer(data.get("online_inquiries")),
        "offline_visits": integer(data.get("offline_visits")),
        "orders_count": integer(data.get("orders_count")),
        "sales_amount": number(data.get("sales_amount")),
        "monthly_sales_target": number(data.get("monthly_sales_target")),
        "notes": text(data.get("notes")),
    }


def validate_work(data, user):
    employee_id, employee_name = owner_from_input(data.get("employee_id") or data.get("employee_name"), user)
    if user["role"] not in {"admin", "operation_manager"}:
        employee_id, employee_name = user["id"], user["name"]
    return {
        "work_date": text(data.get("work_date")) or today_string(),
        "employee_id": employee_id,
        "employee_name": employee_name,
        "completed_items": text(data.get("completed_items")),
        "followed_schools": text(data.get("followed_schools")),
        "follow_customer_count": integer(data.get("follow_customer_count")),
        "new_wechat_count": integer(data.get("new_wechat_count")),
        "ugc_progress": text(data.get("ugc_progress")),
        "issues": text(data.get("issues")),
        "tomorrow_plan": text(data.get("tomorrow_plan")),
        "need_boss_support": text(data.get("need_boss_support")),
    }


def insert_row(table, payload):
    payload["created_at"] = now_string()
    payload["updated_at"] = now_string()
    keys = list(payload.keys())
    last_id = execute(
        f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
        tuple(payload[key] for key in keys),
    )
    return query_one(f"SELECT * FROM {table} WHERE id = ?", (last_id,))


def update_row(table, item_id, payload):
    payload["updated_at"] = now_string()
    keys = list(payload.keys())
    execute(
        f"UPDATE {table} SET {', '.join([key + ' = ?' for key in keys])} WHERE id = ?",
        tuple(payload[key] for key in keys) + (item_id,),
    )
    return query_one(f"SELECT * FROM {table} WHERE id = ?", (item_id,))


def csv_export(rows, fields):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([label for _, label in fields])
    for row in rows:
        writer.writerow([row.get(key, "") for key, _ in fields])
    return output.getvalue()


def csv_template(fields):
    output = StringIO()
    csv.writer(output).writerow([label for _, label in fields])
    return output.getvalue()


def csv_import(csv_text, fields, insert_func, user):
    reader = csv.DictReader(StringIO(csv_text))
    label_to_key = {label: key for key, label in fields}
    created = 0
    for row in reader:
        data = {key: row.get(label, "") for label, key in label_to_key.items()}
        if any(text(v) for v in data.values()):
            insert_func(data, user)
            created += 1
    return created


def followups(user):
    today = today_string()
    upcoming = add_days(7)
    items = []
    for row in visible_schools(user):
        if row["next_follow_up_time"] and row["status"] != "暂停":
            items.append({"kind": "学校", "name": row["school_name"], "owner_name": row["owner_name"], "status": row["status"], "next_action": row["next_action"], "next_follow_up_time": row["next_follow_up_time"]})
    for row in visible_ugc(user):
        if row["next_follow_up_time"] and row["status"] != "暂停":
            items.append({"kind": "UGC", "name": row["activity_name"], "owner_name": row["owner_name"], "status": row["status"], "next_action": row["next_action"], "next_follow_up_time": row["next_follow_up_time"]})
    for row in visible_store_reports(user):
        if row["report_date"] == today:
            continue
    return {
        "overdue": sorted([i for i in items if i["next_follow_up_time"] < today], key=lambda x: x["next_follow_up_time"]),
        "today": sorted([i for i in items if i["next_follow_up_time"] == today], key=lambda x: x["name"]),
        "upcoming": sorted([i for i in items if today < i["next_follow_up_time"] <= upcoming], key=lambda x: x["next_follow_up_time"]),
    }


class AppHandler(BaseHTTPRequestHandler):
    server_version = "BenyiV2/2.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        self.safe_handle("GET")

    def do_POST(self):
        self.safe_handle("POST")

    def do_PUT(self):
        self.safe_handle("PUT")

    def do_DELETE(self):
        self.safe_handle("DELETE")

    def safe_handle(self, method):
        try:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            if path.startswith("/api/"):
                self.api(method, path, query)
            else:
                self.static(path)
        except sqlite3.IntegrityError as exc:
            self.error_json(400, "保存失败：可能已经存在同一天的记录，或账号重复。")
        except PermissionError as exc:
            self.error_json(403, str(exc))
        except Exception as exc:
            self.error_json(500, f"服务错误：{exc}")

    def static(self, path):
        if path in ("", "/"):
            file_path = BASE_DIR / "index.html"
        else:
            safe = path.lstrip("/")
            if safe not in {"index.html", "styles.css", "app.js", "README.md"}:
                self.send_error(404)
                return
            file_path = BASE_DIR / safe
        if not file_path.exists():
            self.send_error(404)
            return
        mime = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".md": "text/plain; charset=utf-8"}.get(file_path.suffix, "application/octet-stream")
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def api(self, method, path, query):
        if path == "/api/health" and method == "GET":
            return self.json({"ok": True, "database": str(DB_PATH)})
        if path == "/api/login" and method == "POST":
            return self.login()
        if path == "/api/logout" and method == "POST":
            return self.logout()

        user = self.current_user()
        if not user:
            return self.error_json(401, "请先登录")
        if user["status"] != "enabled":
            return self.error_json(403, "账号已停用")

        if path == "/api/me" and method == "GET":
            return self.json({"user": sanitize_user(user), "permissions": self.permissions(user)})
        if path == "/api/options" and method == "GET":
            return self.options(user)
        if path == "/api/dashboard" and method == "GET":
            return self.json(dashboard(user))
        if path == "/api/monthly-summary" and method == "GET":
            return self.json(monthly_summary(user, query.get("month")))
        if path == "/api/followups" and method == "GET":
            return self.json(followups(user))
        if path == "/api/me/password" and method == "PUT":
            return self.change_password(user)

        if path == "/api/users":
            if method == "GET":
                self.require_user_admin(user)
                return self.json({"items": [sanitize_user(row) for row in query_all("SELECT * FROM users ORDER BY id")]})
            if method == "POST":
                self.require_user_admin(user)
                return self.create_user()
        if path.startswith("/api/users/"):
            self.require_user_admin(user)
            return self.user_detail(method, int(path.rsplit("/", 1)[-1]), user)

        if path == "/api/schools":
            if method == "GET":
                return self.json({"items": [enrich_school(row, user) for row in visible_schools(user)]})
            if method == "POST":
                if not can_create(user):
                    return self.error_json(403, "没有权限新增学校")
                item = insert_row("schools", validate_school(self.read_json(), user))
                return self.json({"item": enrich_school(item, user)}, 201)
        if path.startswith("/api/schools/"):
            return self.record_detail(method, path, user, "schools", validate_school, enrich_school)

        if path == "/api/ugc":
            if method == "GET":
                return self.json({"items": [enrich_ugc(row, user) for row in visible_ugc(user)]})
            if method == "POST":
                if not can_create(user):
                    return self.error_json(403, "没有权限新增 UGC 活动")
                item = insert_row("ugc_activities", validate_ugc(self.read_json(), user))
                return self.json({"item": enrich_ugc(item, user)}, 201)
        if path.startswith("/api/ugc/"):
            return self.record_detail(method, path, user, "ugc_activities", validate_ugc, enrich_ugc)

        if path == "/api/store-reports":
            if method == "GET":
                return self.json({"items": [enrich_store_report(row, user) for row in visible_store_reports(user, query)]})
            if method == "POST":
                if user["role"] == "viewer":
                    return self.error_json(403, "只读账号不能新增")
                item = insert_row("store_reports", validate_store(self.read_json(), user))
                return self.json({"item": enrich_store_report(item, user)}, 201)
        if path.startswith("/api/store-reports/"):
            return self.store_detail(method, int(path.rsplit("/", 1)[-1]), user)

        if path == "/api/work-summaries":
            if method == "GET":
                return self.json({"items": [enrich_work_summary(row, user) for row in visible_work_summaries(user, query)]})
            if method == "POST":
                if user["role"] == "viewer":
                    return self.error_json(403, "只读账号不能新增")
                item = insert_row("work_summaries", validate_work(self.read_json(), user))
                return self.json({"item": enrich_work_summary(item, user)}, 201)
        if path.startswith("/api/work-summaries/"):
            return self.work_detail(method, int(path.rsplit("/", 1)[-1]), user)

        if path.startswith("/api/export/") and method == "GET":
            return self.export_data(path, query, user)
        if path.startswith("/api/template/") and method == "GET":
            return self.template_data(path)
        if path.startswith("/api/import/") and method == "POST":
            return self.import_data(path, user)

        self.error_json(404, "接口不存在")

    def permissions(self, user):
        return {
            "canCreate": can_create(user),
            "canDelete": can_delete(user),
            "canManageUsers": can_manage_users(user),
            "canImport": can_import(user),
            "canViewFinance": can_view_finance(user),
            "canViewAllStaff": can_view_all_staff(user),
        }

    def options(self, user):
        users = query_all("SELECT * FROM users ORDER BY id")
        self.json(
            {
                "roles": [{"value": key, "label": label} for key, label in ROLES.items()],
                "schoolTypes": SCHOOL_TYPES,
                "schoolPriorities": SCHOOL_PRIORITIES,
                "schoolStatuses": SCHOOL_STATUSES,
                "mainProducts": MAIN_PRODUCTS,
                "ugcTypes": UGC_TYPES,
                "ugcStatuses": UGC_STATUSES,
                "users": [sanitize_user(row) for row in users],
                "owners": [sanitize_user(row) for row in users if row["status"] == "enabled"],
                "schools": [{"id": row["id"], "name": row["school_name"]} for row in visible_schools(user)],
                "today": today_string(),
                "month": month_string(),
                "dbPath": str(DB_PATH),
            }
        )

    def login(self):
        data = self.read_json()
        user = query_one("SELECT * FROM users WHERE username = ?", (text(data.get("username")),))
        if not user or not verify_password(text(data.get("password")), user["password_hash"]):
            return self.error_json(401, "账号或密码不正确")
        if user["status"] != "enabled":
            return self.error_json(403, "账号已停用，请联系老板")
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = user["id"]
        execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_string(), user["id"]))
        fresh = get_user(user["id"])
        self.json(
            {"user": sanitize_user(fresh), "permissions": self.permissions(fresh)},
            headers={"Set-Cookie": f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax"},
        )

    def logout(self):
        token = self.session_token()
        if token in SESSIONS:
            del SESSIONS[token]
        self.json({"ok": True}, headers={"Set-Cookie": f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"})

    def change_password(self, user):
        data = self.read_json()
        old_password = text(data.get("oldPassword"))
        new_password = text(data.get("newPassword"))
        if len(new_password) < 6:
            return self.error_json(400, "新密码至少 6 位")
        if not verify_password(old_password, user["password_hash"]):
            return self.error_json(400, "原密码不正确")
        execute("UPDATE users SET password_hash = ?, password_changed = 1 WHERE id = ?", (hash_password(new_password), user["id"]))
        self.json({"ok": True})

    def create_user(self):
        data = self.read_json()
        name = text(data.get("name"))
        username = text(data.get("username"))
        if not name or not username:
            return self.error_json(400, "姓名和账号不能为空")
        last_id = execute(
            "INSERT INTO users (name, username, role, phone, status, password_hash, password_changed, created_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
            (
                name,
                username,
                choice(data.get("role"), list(ROLES.keys()), "viewer"),
                text(data.get("phone")),
                "disabled" if data.get("status") == "disabled" else "enabled",
                hash_password(text(data.get("password")) or "123456"),
                now_string(),
            ),
        )
        self.json({"item": sanitize_user(get_user(last_id))}, 201)

    def user_detail(self, method, user_id, current_user):
        item = get_user(user_id)
        if not item:
            return self.error_json(404, "员工不存在")
        if method == "PUT":
            data = self.read_json()
            fields = {
                "name": text(data.get("name")) or item["name"],
                "role": choice(data.get("role"), list(ROLES.keys()), item["role"]),
                "phone": text(data.get("phone")),
                "status": "disabled" if data.get("status") == "disabled" else "enabled",
            }
            params = [fields["name"], fields["role"], fields["phone"], fields["status"]]
            sql = "UPDATE users SET name = ?, role = ?, phone = ?, status = ?"
            if text(data.get("password")):
                sql += ", password_hash = ?, password_changed = 0"
                params.append(hash_password(text(data.get("password"))))
            sql += " WHERE id = ?"
            params.append(user_id)
            execute(sql, tuple(params))
            self.json({"item": sanitize_user(get_user(user_id))})
        elif method == "DELETE":
            if user_id == current_user["id"]:
                return self.error_json(400, "不能删除当前登录账号")
            execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.json({"ok": True})
        else:
            self.error_json(405, "方法不支持")

    def record_detail(self, method, path, user, table, validator, enricher):
        item_id = int(path.rsplit("/", 1)[-1])
        item = query_one(f"SELECT * FROM {table} WHERE id = ?", (item_id,))
        if not item:
            return self.error_json(404, "记录不存在")
        if method == "PUT":
            if not can_edit_owned(user, item):
                return self.error_json(403, "没有权限编辑")
            updated = update_row(table, item_id, validator(self.read_json(), user))
            return self.json({"item": enricher(updated, user)})
        if method == "DELETE":
            if not can_delete(user):
                return self.error_json(403, "只有老板可以删除")
            execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
            return self.json({"ok": True})
        self.error_json(405, "方法不支持")

    def store_detail(self, method, item_id, user):
        item = query_one("SELECT * FROM store_reports WHERE id = ?", (item_id,))
        if not item:
            return self.error_json(404, "日报不存在")
        if method == "PUT":
            can_edit = user["role"] in {"admin", "operation_manager", "clerk"} or item["reporter_id"] == user["id"]
            if not can_edit:
                return self.error_json(403, "没有权限编辑这条门店日报")
            updated = update_row("store_reports", item_id, validate_store(self.read_json(), user))
            return self.json({"item": enrich_store_report(updated, user)})
        if method == "DELETE":
            if not can_delete(user):
                return self.error_json(403, "只有老板可以删除")
            execute("DELETE FROM store_reports WHERE id = ?", (item_id,))
            return self.json({"ok": True})
        self.error_json(405, "方法不支持")

    def work_detail(self, method, item_id, user):
        item = query_one("SELECT * FROM work_summaries WHERE id = ?", (item_id,))
        if not item:
            return self.error_json(404, "工作汇总不存在")
        if method == "PUT":
            can_edit = user["role"] in {"admin", "operation_manager"} or item["employee_id"] == user["id"]
            if not can_edit:
                return self.error_json(403, "没有权限编辑这条工作汇总")
            updated = update_row("work_summaries", item_id, validate_work(self.read_json(), user))
            return self.json({"item": enrich_work_summary(updated, user)})
        if method == "DELETE":
            if not can_delete(user):
                return self.error_json(403, "只有老板可以删除")
            execute("DELETE FROM work_summaries WHERE id = ?", (item_id,))
            return self.json({"ok": True})
        self.error_json(405, "方法不支持")

    def export_data(self, path, query, user):
        if path == "/api/export/schools":
            rows = [enrich_school(row, user) for row in visible_schools(user)]
            return self.csv(csv_export(rows, SCHOOL_CSV_FIELDS), "benyi-schools.csv")
        if path == "/api/export/ugc":
            rows = [enrich_ugc(row, user) for row in visible_ugc(user)]
            return self.csv(csv_export(rows, UGC_CSV_FIELDS), "benyi-ugc.csv")
        if path == "/api/export/store-reports":
            rows = [enrich_store_report(row, user) for row in visible_store_reports(user, query)]
            return self.csv(csv_export(rows, STORE_CSV_FIELDS), "benyi-store-reports.csv")
        if path == "/api/export/work-summaries":
            rows = [enrich_work_summary(row, user) for row in visible_work_summaries(user, query)]
            return self.csv(csv_export(rows, WORK_CSV_FIELDS), "benyi-work-summaries.csv")
        self.error_json(404, "导出类型不存在")

    def template_data(self, path):
        fields = {
            "/api/template/schools": SCHOOL_CSV_FIELDS,
            "/api/template/ugc": UGC_CSV_FIELDS,
            "/api/template/store-reports": STORE_CSV_FIELDS,
            "/api/template/work-summaries": WORK_CSV_FIELDS,
        }.get(path)
        if not fields:
            return self.error_json(404, "模板不存在")
        self.csv(csv_template(fields), "benyi-template.csv")

    def import_data(self, path, user):
        if not can_import(user):
            return self.error_json(403, "没有权限导入")
        payload = self.read_json()
        csv_text = payload.get("csv", "")
        mapping = {
            "/api/import/schools": (SCHOOL_CSV_FIELDS, lambda data, u: insert_row("schools", validate_school(data, u))),
            "/api/import/ugc": (UGC_CSV_FIELDS, lambda data, u: insert_row("ugc_activities", validate_ugc(data, u))),
            "/api/import/store-reports": (STORE_CSV_FIELDS, lambda data, u: insert_row("store_reports", validate_store(data, u))),
            "/api/import/work-summaries": (WORK_CSV_FIELDS, lambda data, u: insert_row("work_summaries", validate_work(data, u))),
        }
        if path not in mapping:
            return self.error_json(404, "导入类型不存在")
        fields, insert_func = mapping[path]
        created = csv_import(csv_text, fields, insert_func, user)
        self.json({"created": created})

    def require_user_admin(self, user):
        if not can_manage_users(user):
            raise PermissionError("只有老板可以管理员工账号")

    def session_token(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except cookies.CookieError:
            return None
        morsel = jar.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def current_user(self):
        return get_user(SESSIONS.get(self.session_token()))

    def read_json(self):
        size = int(self.headers.get("Content-Length", 0))
        if size == 0:
            return {}
        raw = self.rfile.read(size).decode("utf-8")
        return json.loads(raw or "{}")

    def json(self, payload, status=200, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def csv(self, content, filename):
        body = ("\ufeff" + content).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error_json(self, status, message):
        self.json({"error": message}, status)


def main():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print("本亦运营后台 V2 已启动")
    print(f"本机打开：http://127.0.0.1:{PORT}")
    if HOST == "0.0.0.0":
        ips = lan_ips()
        if ips:
            print("员工同 Wi-Fi 访问：")
            for ip in ips:
                print(f"  http://{ip}:{PORT}")
        else:
            print("员工同 Wi-Fi 访问：请查看本机 Wi-Fi IP 后使用 http://你的IP:8000")
    else:
        print(f"打开地址：http://{HOST}:{PORT}")
    print(f"数据库文件：{DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
