"""پیاده‌سازی ساده سیستم مدیریت پایان‌نامه"""

import os
import json
import uuid
import hashlib
import secrets
import base64
import shutil
from datetime import datetime, timedelta
from textwrap import dedent


DATA_DIR = "data"
FILES_DIR = "files"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
THESES_FILE = os.path.join(DATA_DIR, "theses.json")
REQUESTS_FILE = os.path.join(DATA_DIR, "requests.json")
DEFENSES_FILE = os.path.join(DATA_DIR, "defenses.json")


def ensure_dirs():
    """کمک فن‌ها برای خواندن/نوشتن JSON"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_password_hash(password: str):
    """هش کردن رمز"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str):
    try:
        salt_b64, dk_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64.encode())
        dk = base64.b64decode(dk_b64.encode())
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return secrets.compare_digest(check, dk)
    except Exception:
        return False


def init_db():
    """چند نمونه مقدار دهی اولیه"""
    ensure_dirs()
    users = load_json(USERS_FILE)
    if not users:
        # نمونه کاربرها
        users = [
            # دانشجوی نمونه
            {
                "id": "S1001",
                "role": "student",
                "name": "علی رضایی",
                "password": make_password_hash("student123"),
                "email": "ali@example.com",
            },
            {
                "id": "S1002",
                "role": "student",
                "name": "سارا محمدی",
                "password": make_password_hash("student123"),
                "email": "sara@example.com",
            },
            # اساتید نمونه
            {
                "id": "P2001",
                "role": "professor",
                "name": "دکتر وحید حسینی",
                "password": make_password_hash("prof123"),
                "email": "vahid@example.com",
                "courses": [
                    {"course_id": "T001", "title": "پایان‌نامه - مهندسی نرم‌افزار"}
                ],
                "max_supervise": 10,
                "current_supervise": 0,
            },
            {
                "id": "P2002",
                "role": "professor",
                "name": "دکتر نسرین موسوی",
                "password": make_password_hash("prof123"),
                "email": "nasrin@example.com",
                "courses": [
                    {"course_id": "T002", "title": "پایان‌نامه - شبکه‌های کامپیوتری"}
                ],
                "max_supervise": 10,
                "current_supervise": 0,
            },
        ]
        save_json(USERS_FILE, users)

    # بقیه فایل‌ها را اگر نیست بساز
    for path in (THESES_FILE, REQUESTS_FILE, DEFENSES_FILE):
        if not os.path.exists(path):
            save_json(path, [])


def find_user_by_id(uid):
    """تابع پیدا کردن شناسه"""
    users = load_json(USERS_FILE)
    for u in users:
        if u["id"] == uid:
            return u
    return None


def update_user(user):
    users = load_json(USERS_FILE)
    for i, u in enumerate(users):
        if u["id"] == user["id"]:
            users[i] = user
            save_json(USERS_FILE, users)
            return
    users.append(user)
    save_json(USERS_FILE, users)


def create_request(student_id, professor_id, course_id):
    """درخواست اخذ پایان‌نامه"""
    requests = load_json(REQUESTS_FILE)
    req = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "professor_id": professor_id,
        "course_id": course_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "approved_at": None,
        "rejection_reason": None,
    }
    requests.append(req)
    save_json(REQUESTS_FILE, requests)
    return req


def list_requests_for_student(student_id):
    requests = load_json(REQUESTS_FILE)
    return [r for r in requests if r["student_id"] == student_id]


def list_requests_for_professor(prof_id, status_filter=None):
    requests = load_json(REQUESTS_FILE)
    out = [r for r in requests if r["professor_id"] == prof_id]
    if status_filter:
        out = [r for r in out if r["status"] == status_filter]
    return out


def update_request(req):
    requests = load_json(REQUESTS_FILE)
    for i, r in enumerate(requests):
        if r["id"] == req["id"]:
            requests[i] = req
            save_json(REQUESTS_FILE, requests)
            return
    requests.append(req)
    save_json(REQUESTS_FILE, requests)


def submit_thesis(
    student_id, professor_id, title, abstract, keywords, pdf_path, year, semester
):
    """ثبت پایان‌نامه"""
    theses = load_json(THESES_FILE)
    # کپی فایل به پوشه files
    if not os.path.exists(pdf_path):
        raise FileNotFoundError("فایل داده‌شده پیدا نشد.")
    dest_name = f"{uuid.uuid4()}_{os.path.basename(pdf_path)}"
    dest_path = os.path.join(FILES_DIR, dest_name)
    shutil.copy(pdf_path, dest_path)
    th = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "professor_id": professor_id,
        "title": title,
        "abstract": abstract,
        "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
        "file_path": dest_path,
        "year": year,
        "semester": semester,
        "submitted_at": datetime.utcnow().isoformat(),
        "defense": None,  # will hold defense info later
        "grade_numeric": None,
        "grade_letter": None,
    }
    theses.append(th)
    save_json(THESES_FILE, theses)
    return th


def list_theses():
    return load_json(THESES_FILE)


def find_thesis_by_id(tid):
    for t in load_json(THESES_FILE):
        if t["id"] == tid:
            return t
    return None


def update_thesis(th):
    theses = load_json(THESES_FILE)
    for i, t in enumerate(theses):
        if t["id"] == th["id"]:
            theses[i] = th
            save_json(THESES_FILE, theses)
            return
    theses.append(th)
    save_json(THESES_FILE, theses)


def create_defense_request(
    thesis_id, requested_date_iso, internal_judge, external_judge
):
    """درخواست دفاع"""
    defenses = load_json(DEFENSES_FILE)
    d = {
        "id": str(uuid.uuid4()),
        "thesis_id": thesis_id,
        "requested_date": requested_date_iso,
        "internal_judge": internal_judge,
        "external_judge": external_judge,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "approved_at": None,
        "result": None,
        "scores": None,
    }
    defenses.append(d)
    save_json(DEFENSES_FILE, defenses)
    return d


def list_defense_requests_for_prof(prof_id):
    defenses = load_json(DEFENSES_FILE)
    # return those where professor is guide of thesis
    theses = load_json(THESES_FILE)
    prof_thesis_ids = [t["id"] for t in theses if t["professor_id"] == prof_id]
    return [d for d in defenses if d["thesis_id"] in prof_thesis_ids]


def update_defense(d):
    defs_list = load_json(DEFENSES_FILE)
    for i, dd in enumerate(defs_list):
        if dd["id"] == d["id"]:
            defs_list[i] = d
            save_json(DEFENSES_FILE, defs_list)
            return
    defs_list.append(d)
    save_json(DEFENSES_FILE, defs_list)


def numeric_to_letter(score):
    """تعیین نمره به صورت الفبا"""
    try:
        s = float(score)
    except Exception:
        return None
    if s >= 17:
        return "الف"
    if 13 <= s < 17:
        return "ب"
    if 10 <= s < 13:
        return "ج"
    return "د"


def generate_minutes(thesis):
    """تولید صورت‌ جلسهٔ نهایی"""
    text = dedent(
        f"""
    صورت‌جلسه نهایی دفاع پایان‌نامه
    --------------------------------
    عنوان: {thesis['title']}
    نویسنده: {thesis['student_id']}
    استاد راهنما: {thesis['professor_id']}
    تاریخ ارسال: {thesis.get('submitted_at')}
    
    نمرات و نتیجه:
    عددی: {thesis.get('grade_numeric')}
    حرفی: {thesis.get('grade_letter')}
    
    فایل پایان‌نامه: {thesis.get('file_path')}
    """
    ).strip()

    fname = f"minutes_{thesis['id']}.txt"
    path = os.path.join(FILES_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def login_prompt_with_role(role):
    """ورود به حساب کاربری"""
    print("\n\n***********************************************")
    print("***********************************************\n\n")
    print("-----------------------------------------------")
    print(f"\t   ورود به سامانه ({'دانشجویان' if role == 'student' else 'اساتید'})")
    print("-----------------------------------------------\n")
    print("برای بازگشت به منو اصلی 0 وارد کنید")
    print("برخی کاربر نمونه ایجاد شده‌، تا سریع تست کنید:\n")

    if role == "student":
        print("S1001 / رمز: student123")
        print("S1002 / رمز: student123\n")

    else:
        print("استاد نمونه: P2001 / رمز: prof123")
        print("استاد نمونه: P2002 / رمز: prof123\n")

    while True:
        uid = input("شناسه: ").strip()
        if uid == "0":
            return None

        pwd = input("رمز: ")
        if pwd == "0":
            return None

        user = find_user_by_id(uid)
        if user and user["role"] == role and verify_password(pwd, user["password"]):
            # ورود موفق
            return user
        else:
            print("شناسه یا رمز عبور اشتباه است، دوباره تلاش کنید.")
            print("\n-----------------------------------------------")


def change_password(user):
    """تابع مربوط به تغییر رمز کاربر"""
    print("تغییر رمز")
    old = input("رمز فعلی: ")
    if not verify_password(old, user["password"]):
        print("رمز فعلی اشتباه است.")
        return
    new = input("رمز جدید: ")
    new2 = input("تکرار رمز جدید: ")
    if new != new2:
        print("تکرار رمز یکی نیست.")
        return
    user["password"] = make_password_hash(new)
    update_user(user)
    print("رمز با موفقیت تغییر کرد.")


def student_menu(user):
    """تابع مربوط به تمام دسترسی های دانشجویان"""
    while True:
        print("\n\n***********************************************")
        print("***********************************************\n\n")
        print("-----------------------------------------------")
        print(f"\tخوش آمدید {user['name']} ({user['role']})")
        print("-----------------------------------------------\n")
        print("1) درخواست اخذ پایان‌نامه")
        print("2) مشاهده وضعیت درخواست‌ها")
        print("3) ارسال مجدد درخواست (در صورت رد)")
        print("4) ثبت/ارسال پایان‌نامه (آپلود فایل)")
        print("5) درخواست دفاع (پس از تایید و گذشت 3 ماه)")
        print("6) جستجوی پایان‌نامه‌ها")
        print("7) تغییر رمز")
        print("0) خروج از حساب کاربری")
        choice = input("\nانتخاب: ").strip()
        if choice == "1":
            # لیست اساتید و دروس
            users = load_json(USERS_FILE)
            profs = [u for u in users if u["role"] == "professor"]
            print("\n-----------------------------------------------")
            print("اساتید موجود:\n")
            for p in profs:
                print(f"{p['id']} - {p['name']}")
                for c in p.get("courses", []):
                    print(f"   course: {c['course_id']} - {c['title']}")
            pid = input("\nشناسه استاد مورد نظر را وارد کنید: ").strip()
            p = find_user_by_id(pid)
            if not p or p["role"] != "professor":
                print("\nشناسه استاد نامعتبر!!!")
                continue
            # انتخاب درس از آن استاد
            if not p.get("courses"):
                print("\nاین استاد درسی برای راهنمایی ندارد.")
                continue
            print("\n-----------------------------------------------")
            print("دروس استاد:")
            for c in p["courses"]:
                print(f"{c['course_id']} - {c['title']}")
            cid = input("\nکد درس (course_id) را وارد کنید: ").strip()
            if not any(c["course_id"] == cid for c in p["courses"]):
                print("\nکد درس نامعتبر.")
                continue
            req = create_request(user["id"], pid, cid)
            print("درخواست ثبت شد. وضعیت: pending")
            print("ID درخواست:", req["id"])
        elif choice == "2":
            reqs = list_requests_for_student(user["id"])
            print("\n-----------------------------------------------")
            if not reqs:
                print("درخواستی ثبت نشده.")
            for r in reqs:
                print("-" * 30)
                print("ID:", r["id"])
                print("استاد:", r["professor_id"])
                print("درس:", r["course_id"])
                print("وضعیت:", r["status"])
                if r["status"] == "approved":
                    print("تاریخ تایید:", r.get("approved_at"))
                if r["status"] == "rejected":
                    print("علت رد:", r.get("rejection_reason"))
        elif choice == "3":
            reqs = [
                r
                for r in list_requests_for_student(user["id"])
                if r["status"] == "rejected"
            ]
            print("\n-----------------------------------------------")
            if not reqs:
                print("درخواستی که رد شده باشد وجود ندارد.")
                continue
            print("درخواست‌های رد شده:")
            for r in reqs:
                print(
                    r["id"],
                    "استاد:",
                    r["professor_id"],
                    "علت:",
                    r.get("rejection_reason"),
                )
            rid = input("ID درخواستی که می‌خواهی مجدداً ارسال شود: ").strip()
            sel = next((r for r in reqs if r["id"] == rid), None)
            if not sel:
                print("انتخاب نامعتبر.")
                continue
            sel["status"] = "pending"
            sel["created_at"] = datetime.utcnow().isoformat()
            sel["rejection_reason"] = None
            update_request(sel)
            print("درخواست مجدداً ارسال شد.")
        elif choice == "4":
            print("\n-----------------------------------------------")
            # ثبت پایان‌نامه
            print("ثبت پایان‌نامه — اطلاعات را وارد کنید.")
            # باید یک درخواست approved وجود داشته باشد و استاد مشخص باشد
            reqs = [
                r
                for r in list_requests_for_student(user["id"])
                if r["status"] == "approved"
            ]
            if not reqs:
                print(
                    "هیچ درخواست تاییدشده‌ای برای شما وجود ندارد. ابتدا باید درخواست اخذ مورد تایید قرار گیرد."
                )
                continue
            # اگر چند درخواست تایید شده باشد، اجازه انتخاب
            print("درخواست‌های تاییدشده:")
            for r in reqs:
                print(
                    r["id"],
                    "استاد:",
                    r["professor_id"],
                    "درس:",
                    r["course_id"],
                    "تاریخ تایید:",
                    r.get("approved_at"),
                )
            rid = input(
                "کدام درخواست را مرتبط با پایان‌نامه قرار می‌دهید؟ (ID): "
            ).strip()
            sel = next((r for r in reqs if r["id"] == rid), None)
            if not sel:
                print("انتخاب نامعتبر.")
                continue
            prof_id = sel["professor_id"]
            title = input("عنوان پایان‌نامه: ").strip()
            abstract = input("چکیده: ").strip()
            keywords = input("کلمات کلیدی (با کاما جدا کنید): ").strip()
            pdf_path = input("مسیر فایل PDF پایان‌نامه روی سیستم شما: ").strip()
            year = input("سال (مثال 1404): ").strip()
            semester = input("نیمسال (مثال اول/دوم): ").strip()
            try:
                th = submit_thesis(
                    user["id"],
                    prof_id,
                    title,
                    abstract,
                    keywords,
                    pdf_path,
                    year,
                    semester,
                )
                print("پایان‌نامه با موفقیت ثبت شد. ID:", th["id"])
            except FileNotFoundError as e:
                print("خطا:", e)

        elif choice == "5":
            # ثبت درخواست دفاع
            # شرط: باید درخواست اخذ قبلاً approved بوده و حداقل 90 روز از approved_at گذشته باشد
            reqs = [
                r
                for r in list_requests_for_student(user["id"])
                if r["status"] == "approved"
            ]
            print("\n-----------------------------------------------")
            if not reqs:
                print("هیچ درخواست تاییدشده‌ای ندارید.")
                continue
            # پیدا کردن پایان‌نامه مرتبط
            theses = [
                t for t in load_json(THESES_FILE) if t["student_id"] == user["id"]
            ]
            if not theses:
                print("هیچ پایان‌نامه‌ای ثبت نکرده‌اید. ابتدا باید پایان‌نامه را ثبت کنید.")
                continue
            print("پایان‌نامه‌های شما:")
            for t in theses:
                print(t["id"], "-", t["title"], "ارسال‌شده:", t.get("submitted_at"))
            tid = input("ID پایان‌نامه‌ای که می‌خواهی برایش دفاع درخواست دهی: ").strip()
            th = next((x for x in theses if x["id"] == tid), None)
            if not th:
                print("ID نامعتبر.")
                continue
            # پیدا کردن request مربوطه و approved_at
            req = next(
                (r for r in reqs if r["professor_id"] == th["professor_id"]), None
            )
            if not req or not req.get("approved_at"):
                print("پیش‌نیاز تایید استاد کامل نیست.")
                continue
            approved_at = datetime.fromisoformat(req["approved_at"])
            if datetime.utcnow() < approved_at + timedelta(days=90):
                print(
                    "حداقل 90 روز از تاریخ تایید نگذشته است. فعلاً امکان درخواست دفاع نیست."
                )
                print("تاریخ تایید:", req["approved_at"])
                continue
            # ثبت درخواست دفاع
            print("درخواست دفاع — تاریخ پیشنهادی را به صورت YYYY-MM-DD وارد کنید.")
            date_str = input("تاریخ پیشنهادی: ").strip()
            try:
                dt = datetime.fromisoformat(date_str)
            except Exception:
                print("فرمت تاریخ نامعتبر.")
                continue
            internal = input("نام یا شناسه داور داخلی: ").strip()
            external = input("نام یا شناسه داور خارجی: ").strip()
            dreq = create_defense_request(th["id"], dt.isoformat(), internal, external)
            print("درخواست دفاع ثبت شد. ID:", dreq["id"])
        elif choice == "6":
            print("\n-----------------------------------------------")
            # جستجوی پایان‌نامه‌ها
            query = input("عبارت جستجو (عنوان/نویسنده/کلیدواژه/سال): ").strip().lower()
            results = []
            for t in load_json(THESES_FILE):
                if (
                    query in t["title"].lower()
                    or query in " ".join(t.get("keywords", [])).lower()
                    or query in t.get("student_id", "").lower()
                    or query in str(t.get("year", "")).lower()
                ):
                    results.append(t)
            if not results:
                print("نتیجه‌ای یافت نشد.")
            for r in results:
                print("-" * 40)
                print("ID:", r["id"])
                print("عنوان:", r["title"])
                print("نویسنده:", r["student_id"])
                print(
                    "چکیده:",
                    r["abstract"][:200] + ("..." if len(r["abstract"]) > 200 else ""),
                )
                print("کلمات کلیدی:", ", ".join(r.get("keywords", [])))
                print("فایل:", r["file_path"])
                print(
                    "نمره عددی:",
                    r.get("grade_numeric"),
                    "نمره حرفی:",
                    r.get("grade_letter"),
                )
        elif choice == "7":
            print("\n-----------------------------------------------")
            change_password(user)
        elif choice == "0":
            print("\n-----------------------------------------------")
            print("خروج از حساب دانشجو.")
            break
        else:
            print("\n-----------------------------------------------")
            print("انتخاب نامعتبر.")


def professor_menu(user):
    """تابع مربوط به تمام دسترسی های اساتید"""
    while True:
        print("\n\n***********************************************")
        print("***********************************************\n\n")
        print("-----------------------------------------------")
        print(f"    خوش آمدید {user['name']} ({user['role']})")
        print("-----------------------------------------------\n")
        print("1) مشاهده درخواست‌های اخذ پایان‌نامه (pending)")
        print("2) مدیریت درخواست‌های دفاع")
        print("3) ثبت نمره دفاع")
        print("4) جستجوی پایان‌نامه‌ها")
        print("5) تغییر رمز")
        print("0) خروج")
        ch = input("\nانتخاب: ").strip()
        print("-----------------------------------------------\n")
        if ch == "1":
            pend = list_requests_for_professor(user["id"], status_filter="pending")
            if not pend:
                print("درخواست pending برای بررسی وجود ندارد.")
                continue
            for r in pend:
                print("-" * 30)
                print("ID:", r["id"])
                print("دانشجو:", r["student_id"])
                print("درس:", r["course_id"])
                print("تاریخ ارسال:", r["created_at"])
            rid = input(
                "اگر می‌خواهید درخواستی را بررسی کنید، ID را وارد کنید (یا Enter برای بازگشت): "
            ).strip()
            if not rid:
                continue
            sel = next((x for x in pend if x["id"] == rid), None)
            if not sel:
                print("ID نامعتبر.")
                continue
            print("1) تایید  2) رد")
            act = input("انتخاب: ").strip()
            if act == "1":
                sel["status"] = "approved"
                sel["approved_at"] = datetime.utcnow().isoformat()
                update_request(sel)
                print("درخواست تایید شد.")
            elif act == "2":
                reason = input("علت رد را وارد کنید: ").strip()
                sel["status"] = "rejected"
                sel["rejection_reason"] = reason
                update_request(sel)
                print("درخواست رد شد.")
            else:
                print("بازگشت.")
        elif ch == "2":
            defs = list_defense_requests_for_prof(user["id"])
            if not defs:
                print("درخواست دفاعی یافت نشد.")
                continue
            for d in defs:
                print("-" * 30)
                print("ID:", d["id"])
                print("پایان‌نامه:", d["thesis_id"])
                print("تاریخ پیشنهادی:", d["requested_date"])
                print("داور داخلی:", d["internal_judge"])
                print("داور خارجی:", d["external_judge"])
                print("وضعیت:", d["status"])
            did = input("ID درخواستی برای عمل (یا Enter جهت بازگشت): ").strip()
            if not did:
                continue
            sel = next((x for x in defs if x["id"] == did), None)
            if not sel:
                print("ID نامعتبر.")
                continue
            print("1) تایید  2) رد")
            a = input("انتخاب: ").strip()
            if a == "1":
                sel["status"] = "approved"
                sel["approved_at"] = datetime.utcnow().isoformat()
                update_defense(sel)
                print("درخواست دفاع تایید شد.")
            elif a == "2":
                sel["status"] = "rejected"
                update_defense(sel)
                print("درخواست دفاع رد شد.")
            else:
                print("بازگشت.")
        elif ch == "3":
            # ثبت نمره برای دفاعی که برگزار شده (یا مورد تایید)
            defs = list_defense_requests_for_prof(user["id"])
            done = [d for d in defs if d["status"] == "approved"]
            if not done:
                print("هیچ درخواست دفاع تاییدشده‌ای وجود ندارد.")
                continue
            for d in done:
                print("-" * 30)
                print(
                    "ID:",
                    d["id"],
                    "پایان‌نامه:",
                    d["thesis_id"],
                    "تاریخ:",
                    d["requested_date"],
                )
            did = input("ID درخواستی برای ثبت نمره: ").strip()
            sel = next((x for x in done if x["id"] == did), None)
            if not sel:
                print("انتخاب نامعتبر.")
                continue
            # ثبت نمرات سه نفر: راهنما، داور داخلی، داور خارجی
            try:
                g1 = float(input("نمره استاد راهنما (0-20): ").strip())
                g2 = float(input("نمره داور داخلی (0-20): ").strip())
                g3 = float(input("نمره داور خارجی (0-20): ").strip())
            except ValueError:
                print("نمره نامعتبر.")
                continue
            avg = (g1 + g2 + g3) / 3.0
            letter = numeric_to_letter(avg)
            sel["scores"] = {
                "guide": g1,
                "internal": g2,
                "external": g3,
                "avg": avg,
                "letter": letter,
            }
            sel["result"] = "defended" if avg >= 10 else "re-defend"
            update_defense(sel)
            # بروزرسانی پایان‌نامه
            th = find_thesis_by_id(sel["thesis_id"])
            if th:
                th["grade_numeric"] = round(avg, 2)
                th["grade_letter"] = letter
                update_thesis(th)
                # تولید صورت جلسه
                minutes_path = generate_minutes(th)
                print("نمره ثبت شد. میانگین:", avg, "حرفی:", letter)
                print("صورت‌جلسه تولید شد:", minutes_path)
            else:
                print("پایان‌نامه مرتبط پیدا نشد.")
        elif ch == "4":
            query = input("عبارت جستجو (عنوان/نویسنده/کلیدواژه/سال): ").strip().lower()
            results = []
            for t in load_json(THESES_FILE):
                if (
                    query in t["title"].lower()
                    or query in " ".join(t.get("keywords", [])).lower()
                    or query in t.get("student_id", "").lower()
                    or query in str(t.get("year", "")).lower()
                ):
                    results.append(t)
            if not results:
                print("نتیجه‌ای یافت نشد.")
            for r in results:
                print("-" * 40)
                print("ID:", r["id"])
                print("عنوان:", r["title"])
                print("نویسنده:", r["student_id"])
                print(
                    "چکیده:",
                    r["abstract"][:200] + ("..." if len(r["abstract"]) > 200 else ""),
                )
                print("کلمات کلیدی:", ", ".join(r.get("keywords", [])))
                print("فایل:", r["file_path"])
                print(
                    "نمره عددی:",
                    r.get("grade_numeric"),
                    "نمره حرفی:",
                    r.get("grade_letter"),
                )
        elif ch == "5":
            change_password(user)
        elif ch == "0":
            print("خروج از حساب استاد.")
            break
        else:
            print("انتخاب نامعتبر.")


def main():
    """تابع اصلی شروع کننده برنامه"""
    init_db()
    while True:
        print("\n-----------------------------------------------")
        print("      <==== سامانه مدیریت پایان‌نامه====>")
        print("-----------------------------------------------")
        print("\n1) ورود اساتید")
        print("2) ورود دانشجویان")
        print("0) خروج از برنامه")
        choice = input("\nانتخاب: ").strip()
        if choice == "1":
            user = login_prompt_with_role("professor")
            if user:
                professor_menu(user)
            print("\n\n***********************************************")
            print("***********************************************\n\n")
        elif choice == "2":
            user = login_prompt_with_role("student")
            if user:
                student_menu(user)
            print("\n\n***********************************************")
            print("***********************************************\n\n")
        elif choice == "0":
            print("\n\n***********************************************")
            print("خداحافظ!!!")
            print("***********************************************\n\n")
            break
        else:
            print("انتخاب نامعتبر.")


if __name__ == "__main__":
    main()
