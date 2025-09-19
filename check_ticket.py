import requests
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Slack Webhook URL (환경변수에서 가져오기)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")

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
        print("⚠️ Slack Webhook 미설정")
        return
    try:
        requests.post(SLACK_WEBHOOK, json={"text": msg})
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
            return f"❌ {perf_day} 일정 조회 실패 (code {resp.status_code})"

        data = resp.json()
        schedules = data.get("data", {}).get("perfTimelist", [])
        if not schedules:
            return f"ℹ️ {perf_day} 일정 없음"

        messages = [f"✅ {perf_day} 일정 {len(schedules)}건 확인"]

        # 각 스케줄별 좌석 확인
        for s in schedules:
            seat_cnt = fetch_seat_count(s)
            if seat_cnt and seat_cnt > 0:
                msg = f"🎫 {perf_day} {s['perfTime'][:2]}시 → {seat_cnt}석 남음"
                messages.append(msg)
                send_slack(msg)

        return "\n".join(messages)

    except Exception as e:
        return f"⚠️ {perf_day} 처리 오류: {e}"

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
            return None
        data = resp.json()
        return sum(g.get("remainCnt", 0) for g in data.get("data", {}).get("seatGradelist", []))
    except:
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
            result = future.result()
            if result:
                print(result)

if __name__ == "__main__":
    # ✅ 실행 시작 알림
    send_slack("🚀 티켓체커 실행 시작!")

    # ✅ 테스트 알람 (무조건 발송)
    send_slack("🧪 [TEST] Slack 알람 정상 동작 확인!")

    # 실제 티켓 체크 실행
    main()

    # ✅ 실행 종료 알림
    send_slack("🏁 티켓체커 실행 종료!")
