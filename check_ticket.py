import requests
import json
import os
from datetime import date, timedelta

# 슬랙 웹훅 (GitHub Secrets 에서 설정 권장)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
PRODUCT_ID = 211942

# 기간 설정
START_DATE = date(2025, 9, 26)  # 공연 시작일
END_DATE   = date(2025, 11, 2)  # 공연 종료일

# 공통 헤더 (브라우저 흉내)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Referer": f"https://ticket.melon.com/performance/index.htm?prodId={PRODUCT_ID}",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

def fetch_schedules(day: str):
    """특정 날짜의 회차 리스트 가져오기"""
    url = f"https://tktapi.melon.com/api/product/schedule/timelist.json?prodId={PRODUCT_ID}&perfDay={day}&pocCode=SC0002&perfTypeCode=GN0006&sellTypeCode=ST0001&seatCntDisplayYn=N&requestservicetype=P"
    resp = requests.get(url, headers=HEADERS)

    try:
        data = resp.json()
        return data.get("data", {}).get("perfTimelist", [])
    except Exception:
        print(f"[ERROR] 일정 조회 JSON 파싱 실패 ({day})")
        print("응답 앞부분:", resp.text[:200])
        return []

def check_seat(schedule_no: str):
    """해당 회차(scheduleNo)의 잔여좌석 확인"""
    url = f"https://ticket.melon.com/tktapi/product/seatStateInfo.json?v=1&prodId={PRODUCT_ID}&scheduleId={schedule_no}&callback=jQuery123456"
    resp = requests.get(url, headers=HEADERS).text

    # JSONP → JSON 변환
    start = resp.find("(")
    end = resp.rfind(")")
    if start == -1 or end == -1:
        print(f"[ERROR] JSONP 파싱 실패 (schedule {schedule_no})")
        print("응답 앞부분:", resp[:200])
        return None

    try:
        data = json.loads(resp[start+1:end])
        return data.get("rmdSeatCnt", 0)
    except Exception:
        print(f"[ERROR] JSON 로드 실패 (schedule {schedule_no})")
        print("응답 앞부분:", resp[start+1:start+200])
        return None

def send_slack(msg: str):
    """슬랙으로 메시지 전송"""
    if not SLACK_WEBHOOK:
        print("⚠️ SLACK_WEBHOOK_URL 환경변수가 없습니다.")
        return
    payload = {"text": msg}
    requests.post(SLACK_WEBHOOK, json=payload)

def main():
    # ✅ 테스트 알람 (무조건 발송)
    send_slack("✅ 테스트 알람: 스크립트 정상 실행됨!")

    cur = START_DATE
    messages = []

    while cur <= END_DATE:
        perf_day = cur.strftime("%Y%m%d")
        schedules = fetch_schedules(perf_day)

        for s in schedules:
            name = f"{s['perfDay']} {s['perfTime'][:2]}시"
            seat_cnt = check_seat(s["scheduleNo"])
            print(f"[{name}] 잔여좌석: {seat_cnt}")

            if seat_cnt and seat_cnt > 0:
                messages.append(f"🎫 {name} → {seat_cnt}석 남음")

        cur += timedelta(days=1)

    # 빈자리 알림
    if messages:
        send_slack("\n".join(messages))

if __name__ == "__main__":
    main()
