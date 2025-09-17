import requests
import os
from datetime import date, timedelta

# 슬랙 웹훅 (GitHub Secrets -> SLACK_WEBHOOK_URL 등록)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
PRODUCT_ID = 211942

# 공연 기간 설정
START_DATE = date(2025, 9, 26)
END_DATE   = date(2025, 11, 2)

# 브라우저 흉내 헤더 (406 방지)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Referer": f"https://ticket.melon.com/performance/index.htm?prodId={PRODUCT_ID}",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
}

def send_slack(msg: str):
    """슬랙 알림"""
    if not SLACK_WEBHOOK:
        print("⚠️ SLACK_WEBHOOK_URL 환경변수가 없습니다.")
        return
    requests.post(SLACK_WEBHOOK, json={"text": msg})

def fetch_schedules(day: str):
    """특정 날짜 회차 리스트 조회"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/timelist.json"
        f"?prodId={PRODUCT_ID}&perfDay={day}&pocCode=SC0002"
        f"&perfTypeCode=GN0006&sellTypeCode=ST0001"
        f"&seatCntDisplayYn=N&requestservicetype=P"
    )

    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"[ERROR] timelist {day} 조회 실패 (code {resp.status_code})")
        return []

    try:
        data = resp.json()
        return data.get("data", {}).get("perfTimelist", [])
    except Exception:
        print("[ERROR] timelist JSON 파싱 실패")
        return []

def check_seat(schedule):
    """잔여 좌석 확인"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/gradelist.json"
        f"?prodId={PRODUCT_ID}&pocCode=SC0002&perfDay={schedule['perfDay']}"
        f"&scheduleNoArray={schedule['scheduleNo']}&sellTypeCodeArray=ST0001"
        f"&seatCntDisplayYn=N&perfTypeCode=GN0006&seatPoc=1"
        f"&cancelCloseDt={schedule['cancelCloseDt']}"
        f"&requestservicetype=P"
    )

    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"[ERROR] gradelist 조회 실패 ({schedule['scheduleNo']})")
        return None

    try:
        total_cnt = sum(g.get("remainCnt", 0) for g in resp.json().get("data", {}).get("seatGradelist", []))
        return total_cnt
    except Exception:
        print("[ERROR] gradelist JSON 파싱 실패")
        return None

def main():
    cur = START_DATE
    messages = []

    while cur <= END_DATE:
        perf_day = cur.strftime("%Y%m%d")
        schedules = fetch_schedules(perf_day)

        for s in schedules:
            name = f"{s['perfDay']} {s['perfTime'][:2]}시"
            seat_cnt = check_seat(s)
            print(f"[{name}] 잔여좌석: {seat_cnt}")

            if seat_cnt and seat_cnt > 0:
                messages.append(f"🎫 {name} → {seat_cnt}석 남음")

        cur += timedelta(days=1)

    if messages:
        send_slack("\n".join(messages))
    else:
        print("빈자리 없음")

if __name__ == "__main__":
    main()
