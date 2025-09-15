import requests
import re
import json
import os
from datetime import date, timedelta, datetime

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")

# 공연 product-id
PRODUCT_ID = 211942

# 시작일, 종료일
START_DATE = date(2024, 9, 26)
END_DATE   = date(2024, 11, 2)

# 첫 스케줄 ID
BASE_SCHEDULE_ID = 100023

# 하루에 11회차 (11시 ~ 21시)
SESSIONS_PER_DAY = 11

def build_schedules():
    schedules = {}
    schedule_id = BASE_SCHEDULE_ID
    cur = START_DATE

    while cur <= END_DATE:
        for h in range(11, 22):  # 11시 ~ 21시
            label = f"{cur.strftime('%m월 %d일')} {h}시"
            schedules[label] = schedule_id
            schedule_id += 1
        cur += timedelta(days=1)

    return schedules

def check_schedule(name, schedule_id):
    url = f"https://ticket.melon.com/tktapi/product/seatStateInfo.json?v=1&prodId={PRODUCT_ID}&scheduleId={schedule_id}&callback=jQuery123456"
    resp = requests.get(url).text

    match = re.search(r"\((.*)\)", resp, re.S)
    if not match:
        print(f"[{name}] ❌ JSONP 파싱 실패")
        return None

    data = json.loads(match.group(1))
    rmd_seat_cnt = data.get("rmdSeatCnt", 0)
    print(f"[{name}] 잔여 수량: {rmd_seat_cnt}")
    return rmd_seat_cnt

def main():
    schedules = build_schedules()
    messages = []

    for name, sid in schedules.items():
        cnt = check_schedule(name, sid)
        if cnt and cnt > 0:
            messages.append(f"🎫 {name} → {cnt}장 남음")

    if messages:
        payload = { "text": "\n".join(messages) }
        requests.post(SLACK_WEBHOOK, json=payload)

 # 🧪 테스트용 알림 (1회성)
    requests.post(SLACK_WEBHOOK, json={"text": "🎉 테스트 알림: 워크플로우가 정상 동작합니다!"})


if __name__ == "__main__":
    main()
