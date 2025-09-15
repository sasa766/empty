import requests
import os
import json
from datetime import date, timedelta

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")

# 공연 product-id
PRODUCT_ID = 211942

# 시작일, 종료일
START_DATE = date(2024, 9, 26)
END_DATE   = date(2024, 11, 2)

# 첫 스케줄 ID
BASE_SCHEDULE_ID = 100023


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
    url = (
        f"https://ticket.melon.com/tktapi/product/seatStateInfo.json?"
        f"v=1&prodId={PRODUCT_ID}&scheduleId={schedule_id}&callback=jQuery123456"
    )
    resp = requests.get(url).text

    # 🔎 응답 원본 300자만 출력
    print(f"[DEBUG] {name} 응답: {resp[:300]}")

    # JSONP → JSON 추출
    if "(" in resp and resp.rfind(")") > 0:
        json_text = resp[resp.find("(") + 1 : resp.rfind(")")]
        try:
            data = json.loads(json_text)
            # 디버깅용 구조 출력
            print(f"[DEBUG] {name} JSON keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            print(f"[{name}] ❌ JSON 디코딩 실패: {e}")
            return None
    else:
        print(f"[{name}] ❌ JSONP 포맷 아님")
        return None

    # 좌석 필드 확인
    rmd_seat_cnt = data.get("rmdSeatCnt")
    print(f"[{name}] rmdSeatCnt 값: {rmd_seat_cnt}")
    return rmd_seat_cnt


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

    # 테스트 알림
    requests.post(SLACK_WEBHOOK, json={"text": "🎉 테스트 알림: 워크플로우 정상 동작!"})


if __name__ == "__main__":
    main()
