import json
import logging
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class PpomppuScraper:
    def __init__(self, target_url="https://www.ppomppu.co.kr/hot.php", post_limit=5, filters=None):
        self.target_url = target_url
        self.post_limit = post_limit
        self.filters = filters or {}
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.base_domain = "https://www.ppomppu.co.kr"

    def fetch_page(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            # 뽐뿌는 euc-kr 인코딩을 사용하는 경우가 많으므로 설정 (최근 utf-8로 바뀌는 추세지만 확인 필요)
            response.encoding = 'euc-kr' 
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_post_list(self, html):
        """뽐뿌 HOT 게시글 리스트에서 게시글 메타데이터를 파싱합니다."""
        soup = BeautifulSoup(html, 'html.parser')
        
        posts = []
        # 뽐뿌 hot.php 최신 구조 (tr class="baseList")
        table_rows = soup.select('tr.baseList')
        
        logger.info(f"Found {len(table_rows)} rows on the page.")

        for row in table_rows:
            try:
                # 제목 추출
                title_elem = row.select_one('.baseList-title')
                if not title_elem:
                    continue

                # img 태그 같은 쓰레기값 제거를 위해 내부 텍스트만
                title = title_elem.get_text(strip=True)
                
                # 댓글수 추출
                reply_count_elem = title_elem.parent.select_one('.list_comment2')
                if reply_count_elem:
                    reply_count_text = reply_count_elem.get_text(strip=True)
                    title = title.replace(reply_count_text, '').strip()

                link = title_elem.get('href')
                if link and link.startswith('/'):
                    link = f"{self.base_domain}{link}"
                elif not link:
                    link = ""

                author_elem = row.select_one('.list_name')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"

                # 시간, 추천수, 조회수 (보통 순서대로 board_date 3개)
                date_tds = row.select('td.board_date')
                post_time = ""
                views = "0"
                recommendations = "0"
                
                if len(date_tds) >= 3:
                    post_time = date_tds[0].get_text(strip=True)
                    
                    raw_rec = date_tds[1].get_text(strip=True)
                    if '-' in raw_rec:
                        recommendations = raw_rec.split('-')[0].strip()
                    else:
                        recommendations = raw_rec
                        
                    views = date_tds[2].get_text(strip=True)

                post_data = {
                    'title': title,
                    'link': link,
                    'author': author,
                    'time': post_time,
                    'views': views,
                    'recommendations': recommendations,
                    'source': 'ppomppu'
                }
                
                posts.append(post_data)
                
                if len(posts) >= self.post_limit:
                    break
                    
            except Exception as e:
                logger.warning(f"Error parsing a row: {e}")
                continue
                
        return posts

    def scrape(self):
        logger.info(f"Starting to scrape: {self.target_url}")
        
        html = self.fetch_page(self.target_url)
        if not html:
            return []
            
        posts = self.parse_post_list(html)
        logger.info(f"Successfully scraped {len(posts)} posts from Ppomppu.")
        return posts


if __name__ == "__main__":
    target_url = "https://www.ppomppu.co.kr/hot.php"
    scraper = PpomppuScraper(target_url, post_limit=5)
    
    print(f"--- Fetching top 5 trending posts from {target_url} ---")
    results = scraper.scrape()
    
    print(json.dumps(results, ensure_ascii=False, indent=2))
