import requests
import datetime
import time

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

def check_tickets():
    today = datetime.date.today()
    dates_to_check = [(today + datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(20)]

    for cur in dates_to_check:
        print(f"\n=== {cur} 날짜 체크 시작 ===")

        url = (
            f"https://tktapi.melon.com/api/product/schedule/timelist.json?"
            f"prodId={PROD_ID}&perfDay={cur}&pocCode={POC_CODE}"
            f"&perfTypeCode={PERF_TYPE_CODE}&sellTypeCode={SELL_TYPE_CODE}"
            f"&seatCntDisplayYn=N&interlockTypeCode=&corpCodeNo=&reflashYn=N"
            f"&requestservicetype=P"
        )

        print(f"🔗 요청 URL: {url}")

        try:
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                schedules = data.get("scheduleList", [])
                if schedules:
                    print(f"✅ {cur} 일정 있음 ({len(schedules)}건)")
                else:
                    print(f"ℹ️ {cur} 일정 없음")
            else:
                print(f"❌ Error: timelist {cur} 조회 실패 (code {response.status_code})")

        except Exception as e:
            print(f"⚠️ Exception 발생: {e}")

if __name__ == "__main__":
    check_tickets()
