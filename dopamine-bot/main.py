import argparse
import json
import logging
import os

import yaml

from scrapers.fmkorea import FMKoreaScraper

logger = logging.getLogger(__name__)

def load_config(config_path="config.yaml"):
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_fmkorea_scraper(config):
    fmkorea_conf = config.get('dopamine_bot', {}).get('scrapers', {}).get('fmkorea', {})
    if not fmkorea_conf.get('enabled', False):
        logger.info("FMKorea scraper is disabled in config.")
        return []

    target_url = fmkorea_conf.get('target_url')
    post_limit = fmkorea_conf.get('post_limit', 5)
    filters = fmkorea_conf.get('filters', {})

    scraper = FMKoreaScraper(target_url=target_url, post_limit=post_limit, filters=filters)
    results = scraper.scrape()
    
    # 여기서 필터 로직 적용 가능 (조회수/추천수 파싱된 값이 문자열이므로 변환 필요)
    # 현재는 기본 결과물만 리턴합니다.
    return results

def run_ppomppu_scraper(config):
    from scrapers.ppomppu import PpomppuScraper
    ppomppu_conf = config.get('dopamine_bot', {}).get('scrapers', {}).get('ppomppu', {})
    if not ppomppu_conf.get('enabled', False):
        logger.info("Ppomppu scraper is disabled in config.")
        return []

    # config.yaml의 target_url은 무시하고 스크래퍼의 기본 url을 사용할 수도 있고, 
    # 일단 config 설정을 넘기도록 구현가능하지만 현재 PpomppuScraper init은 기본값이 있음
    # 필요시 인자 추가
    scraper = PpomppuScraper()
    # post_limit 덮어쓰기
    scraper.post_limit = ppomppu_conf.get('post_limit', 5)
    
    results = scraper.scrape()
    return results

def main():
    parser = argparse.ArgumentParser(description="Dopamine Bot Scraper Entrypoint")
    parser.add_argument("--test-scraper", type=str, help="Test a specific scraper (e.g., fmkorea, ppomppu)")
    args = parser.parse_args()

    config = load_config()
    if not config:
        return

    if args.test_scraper == "fmkorea":
        logger.info("Running FMKorea Scraper in test mode...")
        results = run_fmkorea_scraper(config)
        print(f"\n--- Top {len(results)} Posts from FMKorea ---")
        print(json.dumps(results, ensure_ascii=False, indent=2))
        with open("fmkorea_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif args.test_scraper == "ppomppu":
        logger.info("Running Ppomppu Scraper in test mode...")
        results = run_ppomppu_scraper(config)
        print(f"\n--- Top {len(results)} Posts from Ppomppu ---")
        print(json.dumps(results, ensure_ascii=False, indent=2))
        with open("ppomppu_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    else:
        logger.info("Please specify a scraper to test using --test-scraper")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
