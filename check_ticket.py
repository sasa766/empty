import requests
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Slack Webhook URL (환경변수에서 가져오기)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")

print(f"🔍 환경변수 SLACK_WEBHOOK_URL = {SLACK_WEBHOOK}")  # ✅ 환경변수 확인 로그

# 티켓 정보
PROD_ID = "211942"
POC_CODE = "SC0002"
PERF_TYPE_CODE = "GN0006"
SELL_TYPE_CODE = "ST0001"

# User-Agent 헤더 (브라우저 흉내)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/117.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://ticket.melon.com/",
    "Origin": "https://ticket.melon.com",
    "Connection": "keep-alive"
}

START_DATE = datetime.date(2025, 9, 24)
END_DATE = datetime.date(2025, 11, 2)

def send_slack(msg: str):
    """슬랙으로 메시지 전송"""
    if not SLACK_WEBHOOK:
        print("⚠️ Slack Webhook 미설정 (환경변수 없음)")
        return
    try:
        resp = requests.post(SLACK_WEBHOOK, json={"text": msg})
        print(f"📤 Slack 전송: {msg} (응답 {resp.status_code})")
    except Exception as e:
        print(f"⚠️ Slack 전송 오류: {e}")

def fetch_and_check(day: datetime.date):
    """특정 날짜의 공연 회차와 잔여석 확인"""
    perf_day = day.strftime("%Y%m%d")
    url = (
        f"https://tktapi.melon.com/api/product/schedule/timelist.json?"
        f"prodId={PROD_ID}&perfDay={perf_day}&pocCode={POC_CODE}"
        f"&perfTypeCode={PERF_TYPE_CODE}&sellTypeCode={SELL_TYPE_CODE}"
        f"&seatCntDisplayYn=N&interlockTypeCode=&corpCodeNo=&reflashYn=N"
        f"&requestservicetype=P"
    )

    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"[{perf_day}] ❌ 일정 조회 실패 (code {resp.status_code})")
            return

        data = resp.json()
        schedules = data.get("data", {}).get("perfTimelist", [])
        if not schedules:
            print(f"[{perf_day}] ℹ️ 일정 없음")
            return

        for s in schedules:
            seat_cnt = fetch_seat_count(s)
            perf_time = s.get("perfTime", "????")
            if seat_cnt is None:
                print(f"[{perf_day} - {perf_time}] ⚠️ 좌석 응답 없음/에러")
            else:
                log_line = f"[{perf_day} - {perf_time}] 잔여좌석 : {seat_cnt}"
                print(log_line)
                if seat_cnt > 0:
                    send_slack(f"🎫 {perf_day} {perf_time} → 잔여좌석 {seat_cnt}석")

    except Exception as e:
        print(f"[{perf_day}] ⚠️ 일정 처리 오류: {e}")

def fetch_seat_count(schedule):
    """좌석 잔여수 확인"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/gradelist.json"
        f"?prodId={PROD_ID}&pocCode={POC_CODE}&perfDay={schedule['perfDay']}"
        f"&scheduleNoArray={schedule['scheduleNo']}&sellTypeCodeArray={SELL_TYPE_CODE}"
        f"&seatCntDisplayYn=N&perfTypeCode={PERF_TYPE_CODE}&seatPoc=1"
        f"&cancelCloseDt={schedule['cancelCloseDt']}&corpCodeNo=&interlockTypeCode="
        f"&reflashYn=N&requestservicetype=P"
    )
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"  ↳ ❌ 좌석 조회 실패 (code {resp.status_code}) URL={url}")
            return None
        data = resp.json()
        return sum(g.get("remainCnt", 0) for g in data.get("data", {}).get("seatGradelist", []))
    except Exception as e:
        print(f"  ↳ ⚠️ 좌석 조회 오류: {e}")
        return None

def main():
    cur = START_DATE
    dates = []
    while cur <= END_DATE:
        dates.append(cur)
        cur += datetime.timedelta(days=1)

    # 병렬 실행
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_and_check, d): d for d in dates}
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()
