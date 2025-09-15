import requests
import re
import json
import os
from datetime import date, timedelta

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")

PRODUCT_ID = 211942
START_DATE = date(2024, 9, 26)
END_DATE   = date(2024, 11, 2)
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


def parse_jsonp(resp_text, name):
    """JSONP 또는 JSON 응답 파싱"""
    # 1) JSONP → 괄호 안만 추출
    match = re.search(r"\((\{.*\})\)", resp_text, re.S)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            print(f"[{name}] ❌ JSON 디코딩 실패 (JSONP): {e}")
            return None

    # 2) JSON → 그대로 파싱 시도
    try:
        return json.loads(resp_text)
    except Exception:
        print(f"[{name}] ❌ JSON 포맷 아님")
        print(f"[DEBUG] 응답 일부: {resp_text[:300]}")
        return None


def check_schedule(name, schedule_id):
    url = f"https://ticket.melon.com/tktapi/product/seatStateInfo.json?v=1&prodId={PRODUCT_ID}&scheduleId={schedule_id}&callback=jQuery123456"
    resp = requests.get(url).text

    data = parse_jsonp(resp, name)
    if not data:
        return None

    # 디버그 출력 (앞부분만)
    print(f"[DEBUG] {name} 응답 데이터: {json.dumps(data, ensure_ascii=False)[:300]}")

    # 좌석 수 확인
    rmd_seat_cnt = data.get("rmdSeatCnt")
    if rmd_seat_cnt is not None:
        print(f"[{name}] 잔여 좌석: {rmd_seat_cnt}")
        return rmd_seat_cnt
    else:
        print(f"[{name}] ⚠️ rmdSeatCnt 없음 → 키 확인 필요")
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

    requests.post(SLACK_WEBHOOK, json={"text": "🎉 테스트 알림: 워크플로우 정상 동작"})


if __name__ == "__main__":
    main()
