import os
import requests
import datetime

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_message(message: str):
    if not SLACK_WEBHOOK_URL:
        print("[경고] SLACK_WEBHOOK_URL 환경변수가 없습니다.")
        return
    try:
        res = requests.post(
            SLACK_WEBHOOK_URL,
            json={"text": message},
            headers={"Content-Type": "application/json"},
        )
        if res.status_code != 200:
            print(f"[ERROR] Slack 전송 실패: {res.status_code}, {res.text}")
    except Exception as e:
        print(f"[ERROR] Slack 예외 발생: {e}")

def check_ticket():
    base_url = "https://tktapi.melon.com/api/product/schedule/timelist.json"
    prod_id = "211942"
    poc_code = "SC0002"
    perf_type_code = "GN0006"
    sell_type_code = "ST0001"

    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=50)  # 최대 50일 확인

    for single_date in (today + datetime.timedelta(days=n) for n in range((end_date - today).days + 1)):
        perf_day = single_date.strftime("%Y%m%d")
        print(f"=== {perf_day} 날짜 체크 시작 ===")

        url = (
            f"{base_url}?prodId={prod_id}"
            f"&perfDay={perf_day}"
            f"&pocCode={poc_code}"
            f"&perfTypeCode={perf_type_code}"
            f"&sellTypeCode={sell_type_code}"
            f"&seatCntDisplayYn=N"
            f"&interlockTypeCode=&corpCodeNo=&reflashYn=N"
            f"&requestservicetype=P"
        )
        print(f"🔗 요청 URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"[ERROR] 상태코드 {response.status_code}")
                continue

            data = response.json()
            schedules = data.get("scheduleList", [])
            print(f"→ 스케줄 개수: {len(schedules)}")

            for schedule in schedules:
                seat_cnt = schedule.get("seatCnt", 0)
                time_info = schedule.get("perfTime", "시간미정")

                print(f"[{perf_day} {time_info}] 잔여좌석: {seat_cnt}")
                if seat_cnt and seat_cnt > 0:
                    send_slack_message(f"🎟️ {perf_day} {time_info} 잔여좌석 발견! → {seat_cnt}석")
        except Exception as e:
            print(f"[ERROR] 요청 실패: {e}")

if __name__ == "__main__":
    # ✅ Slack 알림 테스트
    send_slack_message("🔔 테스트 알림: GitHub Actions + Slack 연동이 잘 작동합니다!")

    # ✅ 실제 티켓 확인 실행
    check_ticket()
