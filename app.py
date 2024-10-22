from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import time
import re

app = Flask(__name__)

# 프로젝트 안의 webdriver 폴더에 있는 ChromeDriver 경로 설정
WEBDRIVER_PATH = os.getenv('WEBDRIVER_PATH')

DEBUG_MODE = os.getenv('DEBUG', 'False').lower() in ['true', '1', 't']

# 기본 경로 '/'에서 index.html을 렌더링
@app.route('/')
def index():
    return render_template('index.html')

# Selenium을 사용하여 네이버 검색 결과에서 업체 ID 및 상호명을 크롤링하는 함수
def find_rank(keyword, target_place_id, target_place_name):
    # Chrome WebDriver 설정
    service = Service(executable_path=WEBDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(service=service, options=options)  # driver 변수를 이곳에서 초기화

    try:
        search_link = f"https://m.search.naver.com/search.naver?sm=mtp_hty.top&where=m&query={keyword}"
        driver.get(search_link)
        place_id_str = str(target_place_id)
        time.sleep(5)

        # 1. 리스트에서 더보기 없이 순위를 찾는 경우
        no_more_button_selector = "#loc-main-section-root > div > div.rdX0R > ul > li"
        list_items = driver.find_elements(By.CSS_SELECTOR, no_more_button_selector)
        if list_items:
            print(f"더보기 없이 리스트에서 {place_id_str}를 찾습니다.")
            rank = 1
            for item in list_items:
                try:
                    link = item.find_element(By.CSS_SELECTOR, "a")
                    href = link.get_attribute("href")
                    if place_id_str in href:
                        print(f"{place_id_str}를 포함한 링크 발견: {href}, 현재 순위: {rank}")
                        return rank  # 순위 반환
                except Exception as e:
                    print(f"리스트 항목에서 링크 찾기 오류: {e}")
                rank += 1

        # 2. 첫 번째 더보기 버튼 클릭 후 순위를 찾는 경우
        try:
            driver.execute_script("window.scrollBy(0, 400);")  # 400px 정도 아래로 스크롤
            print("스크롤을 400px 내렸습니다.")

            click_more_button(driver, "a.YORrF span.Jtn42")
            print("첫 번째 더보기 버튼 클릭됨 (a.YORrF span.Jtn42).")
            time.sleep(5)

            # 만약 첫 번째 선택자에서 버튼을 찾지 못하면 class="FtXwJ"로 시도
            if not driver.find_elements(By.CSS_SELECTOR, "a.YORrF span.Jtn42"):
                click_more_button(driver, "a.FtXwJ span.PNozS")
                print("첫 번째 더보기 버튼 클릭됨 (a.FtXwJ span.PNozS).")
                time.sleep(5)

            list_items = driver.find_elements(By.CSS_SELECTOR,
                                              "#place-main-section-root > div.place_section.Owktn > div.rdX0R.POx9H > ul > li")
            rank = 1
            for item in list_items:
                try:
                    link = item.find_element(By.CSS_SELECTOR, "a")
                    href = link.get_attribute("href")
                    if place_id_str in href:
                        print(f"{place_id_str}를 포함한 링크 발견: {href}, 현재 순위: {rank}")
                        return rank  # 순위 반환
                except Exception as e:
                    print(f"리스트 항목에서 링크 찾기 오류: {e}")
                rank += 1
        except Exception as e:
            print(f"첫 번째 더보기 버튼 없음 또는 클릭 실패: {e}")

        # 3. 두 번째 더보기 버튼 클릭 후 순위를 찾는 경우
        try:
            click_more_button(driver, "a.cf8PL")
            print("두 번째 더보기 버튼 클릭됨.")
            time.sleep(5)

            list_items = driver.find_elements(By.CSS_SELECTOR, "#_list_scroll_container > div > div > div.place_business_list_wrapper > ul > li")
            rank = 1
            for item in list_items:
                try:
                    link = item.find_element(By.CSS_SELECTOR, "a")
                    href = link.get_attribute("href")
                    if place_id_str in href:
                        print(f"{place_id_str}를 포함한 링크 발견: {href}, 현재 순위: {rank}")
                        return rank  # 순위 반환
                except Exception as e:
                    print(f"리스트 항목에서 링크 찾기 오류: {e}")
                rank += 1
        except Exception as e:
            print(f"두 번째 더보기 버튼 없음 또는 클릭 실패: {e}")

        print(f"{keyword}에서 {target_place_id}의 순위를 찾을 수 없습니다.")
        return None

    except Exception as e:
        print(f"오류 발생: {e}")
        return None

    finally:
        driver.quit()  # 크롤링이 끝난 후 브라우저 종료


# 더보기 버튼 클릭 함수
def click_more_button(driver, css_selector, timeout=30):
    try:
        # 스크롤하면서 버튼을 찾음
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            try:
                more_element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", more_element)
                time.sleep(10)  # 스크롤 후 대기
                driver.execute_script("arguments[0].click();", more_element)
                print(f"더보기 버튼 ({css_selector}) 클릭됨.")
                time.sleep(10)  # 클릭 후 페이지 로딩 대기
                break  # 버튼을 찾고 클릭했다면 루프 종료
            except Exception as e:
                # 페이지 스크롤을 내리면서 다시 시도
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(10)  # 스크롤 후 대기
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print(f"더보기 버튼 ({css_selector})을 찾을 수 없습니다.")
                    break  # 더 이상 스크롤이 되지 않으면 종료
                last_height = new_height
    except Exception as e:
        print(f"더보기 버튼 클릭 실패: {e}")

# POST 요청 처리, 키워드를 받아 네이버 검색을 진행
@app.route('/check-rank', methods=['POST'])
def check_rank_route():
    data = request.get_json()
    keyword = data.get('keyword')
    target_place_id = data.get('placeId')
    target_place_name = data.get('placeName')  # 상호명 추가

    # 네이버에서 검색 수행
    result = find_rank(keyword, target_place_id, target_place_name)

    # 결과를 JSON으로 반환
    return jsonify({'result': result})

if __name__ == '__main__':
    app.run(host="0.0.0.0")
    app.run(debug=DEBUG_MODE)
