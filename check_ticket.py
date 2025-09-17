import requests
import json
import os
from datetime import date, timedelta
from colorama import Fore, Style, init

# colorama 초기화 (윈도우 호환)
init(autoreset=True)

# 슬랙 웹훅 (GitHub Secrets 에서 설정 권장)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
PRODUCT_ID = 211942

# 기간 설정 (원하는 공연 기간으로 수정)
START_DATE = date(2025, 9, 26)  # 공연 시작일
END_DATE   = date(2025, 11, 2)  # 공연 종료일

# 브라우저 흉내 헤더 (실제 브라우저 요청과 동일하게 세팅)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Referer": f"https://ticket.melon.com/performance/index.htm?prodId={PRODUCT_ID}",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
}

def fetch_schedules(day: str):
    """특정 날짜의 회차 리스트 가져오기"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/timelist.json"
        f"?prodId={PRODUCT_ID}"
        f"&perfDay={day}"
        f"&pocCode=SC0002"
        f"&perfTypeCode=GN0006"
        f"&sellTypeCode=ST0001"
        f"&seatCntDisplayYn=N"
        f"&interlockTypeCode="
        f"&corpCodeNo="
        f"&reflashYn=N"
        f"&requestservicetype=P"
    )

    resp = requests.get(url, headers=HEADERS)

    print(Fore.CYAN + f"🔗 요청 URL: {url}")
    print("응답 상태코드:", resp.status_code)

    if resp.status_code != 200:
        print(Fore.RED + f"[Error] timelist {day} 조회 실패 (code {resp.status_code})")
        return []

    try:
        data = resp.json()
        timelist = data.get("data", {}).get("perfTimelist", [])
        print(Fore.GREEN + f"→ 스케줄 개수: {len(timelist)}")
        return timelist
    except Exception:
        print(Fore.RED + "[ERROR] 일정 JSON 파싱 실패")
        print("응답 앞부분:", resp.text[:200])
        return []

def check_seat(schedule):
    """회차별 잔여좌석 확인 (gradelist.json 활용)"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/gradelist.json"
        f"?prodId={PRODUCT_ID}"
        f"&pocCode=SC0002"
        f"&perfDay={schedule['perfDay']}"
        f"&scheduleNoArray={schedule['scheduleNo']}"
        f"&sellTypeCodeArray=ST0001"
        f"&seatCntDisplayYn=N"
        f"&perfTypeCode=GN0006"
        f"&seatPoc=1"
        f"&cancelCloseDt={schedule['cancelCloseDt']}"
        f"&corpCodeNo="
        f"&interlockTypeCode="
        f"&reflashYn=N"
        f"&requestservicetype=P"
    )

    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(Fore.RED + f"[ERROR] gradelist 조회 실패 (schedule {schedule['scheduleNo']}) (code {resp.status_code})")
        return None

    try:
        data = resp.json()
        total_cnt = 0
        for g in data.get("data", {}).get("seatGradelist", []):
            total_cnt += g.get("remainCnt", 0)
        return total_cnt
    except Exception:
        print(Fore.RED + f"[ERROR] gradelist JSON 파싱 실패 (schedule {schedule['scheduleNo']})")
        print("응답 앞부분:", resp.text[:200])
        return None

def send_slack(msg: str):
    """슬랙으로 메시지 전송"""
    if not SLACK_WEBHOOK:
        print(Fore.YELLOW + "⚠️ SLACK_WEBHOOK_URL 환경변수가 없습니다.")
        return
    payload = {"text": msg}
    requests.post(SLACK_WEBHOOK, json=payload)

def main():
    # ✅ 테스트 알람 (무조건 발송)
    send_slack("✅ 테스트 알람: 스크립트 정상 실행됨!")

    cur = START_DATE
    messages = []

    while cur <= END_DATE:
        print(Style.BRIGHT + Fore.MAGENTA + f"\n=== {cur} 날짜 체크 시작 ===")
        perf_day = cur.strftime("%Y%m%d")
        schedules = fetch_schedules(perf_day)

        for s in schedules:
            name = f"{s['perfDay']} {s['perfTime'][:2]}시"
            seat_cnt = check_seat(s)
            print(Fore.WHITE + f"[{name}] 잔여좌석: {seat_cnt}")

            if seat_cnt and seat_cnt > 0:
                messages.append(f"🎫 {name} → {seat_cnt}석 남음")

        cur += timedelta(days=1)

    # 빈자리 알림
    if messages:
        send_slack("\n".join(messages))

if __name__ == "__main__":
    main()
