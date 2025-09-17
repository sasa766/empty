import requests
import os
from datetime import date, timedelta

# 🎫 공연 정보
PRODUCT_ID = "211942"
POC_CODE = "SC0002"
PERF_TYPE_CODE = "GN0006"
SELL_TYPE_CODE = "ST0001"

# 🔔 Slack Webhook URL (환경변수에서 가져오기)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")

# 📅 공연 기간
START_DATE = date(2025, 9, 17)   # 시작일
END_DATE   = date(2025, 11, 2)   # 종료일

# 🌐 브라우저 흉내 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/117.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"https://ticket.melon.com/performance/index.htm?prodId={PRODUCT_ID}",
    "Origin": "https://ticket.melon.com",
    "Connection": "keep-alive"
}


def fetch_schedules(day: str):
    """특정 날짜의 timelist.json 불러오기"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/timelist.json"
        f"?prodId={PRODUCT_ID}&perfDay={day}&pocCode={POC_CODE}"
        f"&perfTypeCode={PERF_TYPE_CODE}&sellTypeCode={SELL_TYPE_CODE}"
        f"&seatCntDisplayYn=N&interlockTypeCode=&corpCodeNo=&reflashYn=N"
        f"&requestservicetype=P"
    )

    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"❌ timelist 조회 실패 ({day}, code {resp.status_code})")
        return []

    try:
        data = resp.json()
        return data.get("data", {}).get("perfTimelist", [])
    except Exception:
        print(f"⚠️ JSON 파싱 실패 ({day})")
        return []


def check_seat(schedule):
    """gradelist.json 으로 잔여석 확인"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/gradelist.json"
        f"?prodId={PRODUCT_ID}&pocCode={POC_CODE}&perfDay={schedule['perfDay']}"
        f"&scheduleNoArray={schedule['scheduleNo']}&sellTypeCodeArray={SELL_TYPE_CODE}"
        f"&seatCntDisplayYn=N&perfTypeCode={PERF_TYPE_CODE}&seatPoc=1"
        f"&cancelCloseDt={schedule['cancelCloseDt']}&corpCodeNo=&interlockTypeCode="
        f"&reflashYn=N&requestservicetype=P"
    )

    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"❌ gradelist 조회 실패 (schedule {schedule['scheduleNo']})")
        return None

    try:
        data = resp.json()
        total_cnt = 0
        for g in data.get("data", {}).get("seatGradelist", []):
            total_cnt += g.get("remainCnt", 0)
        return total_cnt
    except Exception:
        print(f"⚠️ gradelist JSON 파싱 실패 (schedule {schedule['scheduleNo']})")
        return None


def send_slack(msg: str):
    """슬랙 알람 전송"""
    if not SLACK_WEBHOOK:
        print("⚠️ SLACK_WEBHOOK_URL 환경변수가 없음 → 메시지 콘솔에 출력")
        print(msg)
        return
    try:
        requests.post(SLACK_WEBHOOK, json={"text": msg})
    except Exception as e:
        print(f"⚠️ Slack 전송 실패: {e}")


def main():
    cur = START_DATE

    while cur <= END_DATE:
        perf_day = cur.strftime("%Y%m%d")
        print(f"\n=== {perf_day} 날짜 체크 시작 ===")

        schedules = fetch_schedules(perf_day)

        for s in schedules:
            name = f"{s['perfDay']} {s['perfTime'][:2]}시"
            seat_cnt = check_seat(s)

            if seat_cnt is not None:
                print(f"[{name}] 잔여석: {seat_cnt}")
                if seat_cnt > 0:
                    msg = f"🎫 {name} → {seat_cnt}석 남음"
                    send_slack(msg)  # ✅ 즉시 알림 전송

        cur += timedelta(days=1)


if __name__ == "__main__":
    main()
