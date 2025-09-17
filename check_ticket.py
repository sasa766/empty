import requests
import datetime
import concurrent.futures

# 티켓 정보
PROD_ID = "211942"
POC_CODE = "SC0002"
PERF_TYPE_CODE = "GN0006"
SELL_TYPE_CODE = "ST0001"

# Slack Webhook URL
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/XXXX/XXXX/XXXX"  # 실제 값 넣으세요

# User-Agent 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/117.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://ticket.melon.com/",
    "Origin": "https://ticket.melon.com",
    "Connection": "keep-alive"
}


def send_slack_message(text: str):
    """슬랙으로 메시지 전송"""
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
    except Exception as e:
        print(f"⚠️ Slack 전송 실패: {e}")


def check_schedule(date_str, schedule):
    """특정 날짜+회차 잔여석 체크"""
    perf_dt_seq = schedule.get("perfDtSeq")
    perf_time = schedule.get("perfTime", "시간 미정")

    url = (
        f"https://tktapi.melon.com/api/product/schedule/gradelist.json?"
        f"prodId={PROD_ID}&pocCode={POC_CODE}&perfDtSeq={perf_dt_seq}"
        f"&sellTypeCode={SELL_TYPE_CODE}&seatCntDisplayYn=N"
    )

    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            grades = res.json().get("seatGradeList", [])
            for g in grades:
                grade = g.get("seatGradeName", "등급미정")
                remain = g.get("remainCnt", 0)
                if remain > 0:
                    msg = f"🎟️ {date_str} {perf_time} - {grade} 잔여석 {remain}석"
                    print(msg)
                    send_slack_message(msg)
        else:
            print(f"❌ gradelist 실패 ({date_str}, {perf_time}, code={res.status_code})")
    except Exception as e:
        print(f"⚠️ Exception: {e} ({date_str} {perf_time})")


def fetch_schedules(date_str):
    """특정 날짜의 회차 목록 가져오기"""
    url = (
        f"https://tktapi.melon.com/api/product/schedule/timelist.json?"
        f"prodId={PROD_ID}&perfDay={date_str}&pocCode={POC_CODE}"
        f"&perfTypeCode={PERF_TYPE_CODE}&sellTypeCode={SELL_TYPE_CODE}"
        f"&seatCntDisplayYn=N&interlockTypeCode=&corpCodeNo=&reflashYn=N"
        f"&requestservicetype=P"
    )

    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            return res.json().get("scheduleList", [])
        else:
            print(f"❌ timelist 실패 ({date_str}, code={res.status_code})")
            return []
    except Exception as e:
        print(f"⚠️ Exception: {e} ({date_str})")
        return []


def check_tickets():
    start_date = datetime.date(2025, 9, 24)
    end_date = datetime.date(2025, 11, 2)
    dates_to_check = [(start_date + datetime.timedelta(days=i)).strftime("%Y%m%d")
                      for i in range((end_date - start_date).days + 1)]

    # 날짜별로 스케줄 모으기 (직렬 1회)
    tasks = []
    for d in dates_to_check:
        schedules = fetch_schedules(d)
        for s in schedules:
            tasks.append((d, s))

    # 스케줄+날짜 병렬 실행 (풀 병렬)
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(check_schedule, d, s) for d, s in tasks]
        concurrent.futures.wait(futures)


if __name__ == "__main__":
    check_tickets()
