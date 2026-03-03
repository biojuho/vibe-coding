import json
import logging
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class FMKoreaScraper:
    def __init__(self, target_url, post_limit=5, filters=None):
        self.target_url = target_url
        self.post_limit = post_limit
        self.filters = filters or {}
        
        # Cloudflare 방어 등을 우회하기 위해 적절한 User-Agent 사용
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.base_domain = "https://www.fmkorea.com"

    def fetch_page(self, url):
        """지정된 URL의 HTML 페이지를 가져옵니다."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_post_list(self, html):
        """포텐 터짐 게시판 리스트에서 게시글 메타데이터를 파싱합니다."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 에펨코리아 베스트 게시판 리스트 테이블 요소 찾기 (클래스명 등은 실제 DOM 구조에 맞추어 조정 필요)
        # 2024년 기준 대략적인 구조: <table class="bd_lst bd_tb_lst bd_tb"> <tbody> <tr> ...
        # 여기서는 가장 보편적인 구조를 우선 가정하여 파싱합니다. 실제 DOM과 다르면 수정할 것.
        # listStyle=list 형태 기준
        
        posts = []
        table_rows = soup.select('.bd_lst.bd_tb_lst.bd_tb tbody tr')
        
        if not table_rows:
            # 모바일 뷰나 다른 구조일 경우 대비 
            table_rows = soup.select('.fm_best_widget_list .li')
            
        logger.info(f"Found {len(table_rows)} rows on the page.")

        for row in table_rows:
            # 공지사항(Notice) 스킵
            if row.get('class') and 'notice' in row.get('class'):
                continue
                
            try:
                title_elem = row.select_one('.title a')
                if not title_elem:
                    continue
                    
                # 공백 및 카테고리 태그 정리
                title = title_elem.get_text(strip=True)
                
                # 가끔 "[분류]" 가 a 태그 바깥이나 안쪽에 텍스트로 있을 수 있음
                # 제목에서 "[123]" 같은 댓글수 부분을 제거하는 로직 추가
                reply_count_elem = title_elem.select_one('.replyNum')
                if reply_count_elem:
                    reply_count_text = reply_count_elem.get_text(strip=True)
                    title = title.replace(reply_count_text, '').strip()

                link = title_elem.get('href')
                if link and not link.startswith('http'):
                    link = f"{self.base_domain}{link}"
                elif not link:
                    link = ""
                    
                author_elem = row.select_one('.author')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"

                time_elem = row.select_one('.time')
                post_time = time_elem.get_text(strip=True) if time_elem else ""
                
                # 조회수 및 추천수 파싱 (추후 필터링에 사용)
                # 에펨코리아의 베스트 리스트에서 m_no_voted는 추천수, 기본 m_no는 조회수를 의미함
                voted_elem = row.select_one('.m_no_voted')
                recommendations = voted_elem.get_text(strip=True) if voted_elem else "0"
                
                # m_no 클래스를 가진 td 중 m_no_voted가 아닌 것이 조회수
                views = "0"
                for m_no_elem in row.select('.m_no'):
                    if 'm_no_voted' not in m_no_elem.get('class', []):
                        views = m_no_elem.get_text(strip=True)
                        break
                
                post_data = {
                    'title': title,
                    'link': link,
                    'author': author,
                    'time': post_time,
                    'views': views,
                    'recommendations': recommendations,
                    'source': 'fmkorea'
                }
                
                posts.append(post_data)
                
                if len(posts) >= self.post_limit:
                    break
                    
            except Exception as e:
                logger.warning(f"Error parsing a row: {e}")
                continue
                
        return posts

    def scrape(self):
        """메인 스크래핑 파이프라인 메서드"""
        logger.info(f"Starting to scrape: {self.target_url}")
        
        html = self.fetch_page(self.target_url)
        if not html:
            return []
            
        posts = self.parse_post_list(html)
        logger.info(f"Successfully scraped {len(posts)} posts from FMKorea.")
        return posts


if __name__ == "__main__":
    # 단독 테스트 코드
    target_url = "https://www.fmkorea.com/index.php?mid=best&listStyle=list"
    scraper = FMKoreaScraper(target_url, post_limit=5)
    
    print(f"--- Fetching top 5 trending posts from {target_url} ---")
    results = scraper.scrape()
    
    print(json.dumps(results, ensure_ascii=False, indent=2))
