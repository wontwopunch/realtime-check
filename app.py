from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import time
import re
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)

load_dotenv()  # .env 파일 로드

# .env 파일에 저장된 설정 값 불러오기
VALID_USERNAME = os.getenv('VALID_USERNAME')
VALID_PASSWORD = os.getenv('VALID_PASSWORD')
WEBDRIVER_PATH = os.getenv('WEBDRIVER_PATH')
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() in ['true', '1', 't']

# 로그인 페이지 라우트
@app.route('/')
def login_page():
    return render_template('login.html')

# 로그인 처리 라우트
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        session['user'] = username  # 세션에 사용자 정보 저장
        return redirect(url_for('index_page'))  # 로그인 후 index.html로 이동
    else:
        flash('아이디 또는 비밀번호가 올바르지 않습니다.')
        return render_template('login.html', error='아이디 또는 비밀번호가 잘못되었습니다.')

# index.html로 이동하는 라우트
@app.route('/index')
def index_page():
    if 'user' in session:
        return render_template('index.html')  # 로그인 후 index.html 렌더링
    else:
        return redirect(url_for('login_page'))

# 로그아웃 처리
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

# Selenium을 사용하여 네이버 검색 결과에서 업체 ID 및 상호명을 크롤링하는 함수
def find_rank(keyword, target_place_id, target_place_name):
    # Chrome WebDriver 설정
    # service = Service(executable_path=WEBDRIVER_PATH)
    service = Service('/home/ubuntu/rank/realtime-check/webdriver')

    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')  # 크롬을 헤드리스 모드로 실행
    driver = webdriver.Chrome(service=service, options=options)


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

        # 2. 첫 번째 더보기 버튼 처리
        click_more_button(driver, "a.YORrF span.Jtn42")
        print("첫 번째 더보기 버튼 클릭됨 (a.YORrF span.Jtn42).")
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

        # 3. 두 번째 더보기 버튼 처리
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
        for _ in range(10):  # 최대 10번 시도 후 종료
            try:
                more_element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", more_element)
                time.sleep(5)
                driver.execute_script("arguments[0].click();", more_element)
                print(f"더보기 버튼 ({css_selector}) 클릭됨.")
                time.sleep(5)
                break  # 버튼을 찾고 클릭했다면 루프 종료
            except Exception as e:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(5)
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

    result = find_rank(keyword, target_place_id, target_place_name)
    return jsonify({'result': result})

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=DEBUG_MODE)
