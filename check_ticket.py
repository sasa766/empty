import requests
import re
import json
import os
from datetime import date, timedelta

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


def parse_jsonp(resp_text, name):
    match = re.search(r"\((.*)\)", resp_text, re.S)
    if not match:
        print(f"[{name}] ❌ JSONP 파싱 실패")
        return None

    try:
        return json.loads(match.group(1))
    except Exception as e:
        print(f"[{name}] ❌ JSON 파싱 오류: {e}")
        return None


def check_schedule(name, schedule_id):
    url = f"https://ticket.melon.com/tktapi/product/seatStateInfo.json?v=1&prodId={PRODUCT_ID}&scheduleId={schedule_id}&callback=jQuery123456"
    resp = requests.get(url)

    # 응답 상태 확인용 DEBUG 로그
    print(f"[DEBUG] {name} 응답 상태코드: {resp.status_code}")
    print(f"[DEBUG] {name} 응답 헤더: {dict(resp.headers)}")
    print(f"[DEBUG] {name} 응답 길이: {len(resp.text)}")
    print(f"[DEBUG] {name} 응답 전문(앞부분 500자): {resp.text[:500]}")

    if not resp.text.strip():
        print(f"[{name}] ❌ 응답이 비어있음")
        return None

    data = parse_jsonp(resp.text, name)
    if not data:
        return None

    print(f"[DEBUG] {name} 응답 JSON 키: {list(data.keys())}")
    rmd_seat_cnt = data.get("rmdSeatCnt")
    if rmd_seat_cnt is not None:
        print(f"[{name}] 잔여 좌석: {rmd_seat_cnt}")
        return rmd_seat_cnt
    else:
        print(f"[{name}] ⚠️ rmdSeatCnt 없음")
        return None


def main():
    schedules = build_schedules()
    messages = []

    for name, sid in schedules.items():
        cnt = check_schedule(name, sid)
        if cnt and cnt > 0:
            messages.append(f"🎫 {name} → {cnt}장 남음")

    if messages:
        payload = {"text": "\n".join(messages)}
        requests.post(SLACK_WEBHOOK, json=payload)

    # 테스트용 알림 (1회성)
    requests.post(SLACK_WEBHOOK, json={"text": "🧪 테스트 알림: 워크플로우가 정상 동작 중입니다!"})


if __name__ == "__main__":
    main()
