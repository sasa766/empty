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

# User-Agent 헤더 (브라우저 흉내 + 필수 헤더 추가)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://ticket.melon.com/",
    "Origin": "https://ticket.melon.com",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
}

START_DATE = datetime.date(2025, 9, 24)
END_DATE = datetime.date(2025, 11, 2)


def send_slack(msg: str):
    """슬랙으로 메시지 전송 (디버그 로그 포함)"""
    if not SLACK_WEBHOOK:
        print("⚠️ Slack Webhook 미설정 (환경변수 없음)")
        return
    try:
        print(f"📤 Slack 전송 시도 → {msg}")  # ✅ 보낼 메시지 출력
        resp = requests.post(SLACK_WEBHOOK, json={"text": msg})
        print(f"📥 Slack 응답 코드: {resp.status_code}")  # ✅ 응답 코드 출력
        print(f"📥 Slack 응답 본문: {resp.text}")         # ✅ 응답 내용 출력
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
        print(f"🔗 요청 URL: {url}")
        print(f"📥 응답 코드: {resp.status_code}")
        print(f"📥 응답 헤더: {resp.headers}")
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
        print(f"🔗 좌석 요청 URL: {url}")
        print(f"📥 좌석 응답 코드: {resp.status_code}")
        print(f"📥 좌석 응답 헤더: {resp.headers}")
        if resp.status_code != 200:
            return None
        data = resp.json()
        return sum(g.get("remainCnt", 0) for g in data.get("data", {}).get("seatGradelist", []))
    except Exception as e:
        print(f"⚠️ 좌석 조회 오류: {e}")
        return None


def main():
    # ✅ 시작 알람
    send_slack("🚨 Slack 알람 테스트 시작")

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

    # ✅ 종료 알람
    send_slack("🏁 Slack 알람 테스트 종료")


if __name__ == "__main__":
    main()
