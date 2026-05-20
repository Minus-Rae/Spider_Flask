# spider.py
# -*- coding: utf-8 -*-
"""
智联招聘 Selenium 爬虫主程序
"""
import time
import random
import pandas as pd
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ✅ 注意这里：从外部的 config.py 导入全量配置
from config import CITY_CODES, POSITION_CODES, CRAWL_STRATEGY, OUTPUT_CONFIG

class ZhaopinSeleniumCrawler:
    """智联招聘 Selenium 定向爬虫"""
    
    def __init__(self, headless=True):
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
            """
        })
        
        self.base_url = "https://www.zhaopin.com/"
        self.all_jobs = []
        self.wait = WebDriverWait(self.driver, 15)
    
    def search_by_keyword_city(self, keyword, city_name):
        """
        优先使用 URL 直连方案。如果直连失败或超时，再回退到模拟首页搜索。
        """
        print(f"尝试 URL 直连搜索: {city_name} - {keyword}")
        
        # 1. 获取城市编码，默认兜底为北京(530)
        city_code = CITY_CODES.get(city_name, "530")
        direct_url = f"https://www.zhaopin.com/sou/jl{city_code}/p1?kw={keyword}"
        
        try:
            # 2. 优先执行 URL 直连
            self.driver.get(direct_url)
            
            # 验证页面是否成功加载：等待出现职位卡片，或者“未找到职位”的空页面提示
            self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    ".jobinfo, .joblist-box__iteminfo, .empty-box, .search-empty-content"
                ))
            )
            time.sleep(random.uniform(1.5, 3.0))  # 给一点缓冲时间让页面 JS 完全渲染
            print("URL 直连加载成功")
            return True
            
        except Exception as e:
            print(f"URL 直连加载超时或无响应，启动首页模拟点击备用方案...")
            
            # 3. 备用兜底方案：退回到模拟用户首页操作
            try:
                self.driver.get(self.base_url)
                time.sleep(random.uniform(2, 4))
                
                # 寻找搜索框并输入关键词
                search_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='职位'], input[placeholder*='公司']"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(1)
                
                # 直接回车搜索，比点击搜索按钮更稳定
                search_input.send_keys(Keys.ENTER)
                
                # 等待新页面加载
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".jobinfo, .joblist-box__iteminfo"))
                )
                time.sleep(random.uniform(2, 3))
                print("备用方案执行成功")
                return True
                
            except Exception as backup_e:
                print(f"备用方案执行失败，跳过该岗位: {backup_e}")
                return False
    
    def parse_job_card(self, card_elem):
        try:
            def get_text(selector, parent=None):
                try:
                    elem = parent.find_element(By.CSS_SELECTOR, selector) if parent else card_elem.find_element(By.CSS_SELECTOR, selector)
                    return elem.text.strip()
                except:
                    return ""
            
            def get_tags(selector, parent=None):
                try:
                    elems = parent.find_elements(By.CSS_SELECTOR, selector) if parent else card_elem.find_elements(By.CSS_SELECTOR, selector)
                    return [el.text.strip() for el in elems if el.text.strip()]
                except:
                    return []
            
            job_name = get_text('.jobinfo__name')
            job_salary = get_text('.jobinfo__salary')
            
            location_span = card_elem.find_elements(By.CSS_SELECTOR, '.jobinfo__other-info-item span')
            job_area = location_span[0].text.strip() if location_span else ""
            
            other_items = card_elem.find_elements(By.CSS_SELECTOR, '.jobinfo__other-info-item')
            work_year, education = "", ""
            for item in other_items:
                text = item.text.strip()
                if not text or '·' in text:
                    continue
                if any(kw in text for kw in ['经验不限', '应届', '1-3年', '3-5年', '5-10年', '10年以上']):
                    work_year = text
                elif any(kw in text for kw in ['学历不限', '初中', '高中', '中专', '大专', '本科', '硕士', '博士']):
                    education = text
            
            job_benefits = ", ".join(get_tags('.jobinfo__tag .joblist-box__item-tag'))
            
            parent = card_elem.find_element(By.XPATH, "./..")
            com_name = get_text('.companyinfo__name', parent)
            
            company_tags = get_tags('.companyinfo .joblist-box__item-tag', parent)
            com_type = company_tags[0] if len(company_tags) > 0 else ""
            com_size = company_tags[1] if len(company_tags) > 1 else ""
            
            return {
                "job_name": job_name,
                "job_salary": job_salary,
                "job_area": job_area,
                "com_name": com_name,
                "com_type": com_type,
                "com_size": com_size,
                "education": education,
                "work_year": work_year,
                "job_benefits": job_benefits,
                "category_path": "", 
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            return None
    
    def crawl_page(self, category, subcategory, position):
        jobs = []
        try:
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".jobinfo, .joblist-box__iteminfo"))
            )
            time.sleep(random.uniform(1, 2))
            
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".jobinfo")
            if not job_cards:
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".joblist-box__iteminfo")
            
            if not job_cards:
                print("未找到职位卡片")
                return []
            
            for i, card in enumerate(job_cards, 1):
                job = self.parse_job_card(card)
                if job and job["job_name"] and job["com_name"]:
                    job["category_path"] = f"{category}-{subcategory}-{position}"
                    jobs.append(job)
            
            print(f"解析成功 {len(jobs)}/{len(job_cards)} 条")
        except Exception as e:
            print(f"爬取页面失败: {e}")
        return jobs
    
    def next_page(self):
        try:
            next_btn_selector = "a.btn.soupager__btn"
            next_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, next_btn_selector))
            )
            
            if "disabled" in next_btn.get_attribute("class") or not next_btn.is_enabled():
                print("已是最后一页")
                return False
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", next_btn)
            
            WebDriverWait(self.driver, 15).until(
                lambda d: d.current_url != self.driver.current_url or 
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jobinfo"))(d)
            )
            time.sleep(random.uniform(1, 2))
            return True
        except Exception as e:
            return False
    
    def crawl_all(self):
        total_cities = len(CRAWL_STRATEGY['cities'])
        print(f"开始全量爬取，共 {total_cities} 个城市，每个岗位爬取 {CRAWL_STRATEGY['max_pages']} 页")
        
        for category, subcategory, positions in CRAWL_STRATEGY["enabled_combinations"]:
            for city in CRAWL_STRATEGY["cities"]:
                for position in positions:
                    print(f"\n{'='*60}")
                    print(f"爬取: {city} - {category}→{subcategory}→{position}")
                    print(f"{'='*60}")
                    
                    if not self.search_by_keyword_city(position, city):
                        continue
                    
                    for page in range(1, CRAWL_STRATEGY["max_pages"] + 1):
                        print(f"第 {page} 页")
                        jobs = self.crawl_page(category, subcategory, position)
                        if not jobs:
                            break
                        
                        self.all_jobs.extend(jobs)
                        print(f"累计: {len(self.all_jobs)} 条")
                        
                        if page < CRAWL_STRATEGY["max_pages"]:
                            if not self.next_page():
                                break
                        
                        time.sleep(random.uniform(*CRAWL_STRATEGY["delay_range"]))
        
        return self.all_jobs
    
    def save_to_csv(self, filename):
        if not self.all_jobs:
            print("无数据可保存")
            return
        
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        df = pd.DataFrame(self.all_jobs)
        df = df[OUTPUT_CONFIG["fields"]]
        df.to_csv(filename, index=False, encoding=OUTPUT_CONFIG["encoding"])
        
        print(f"\n保存完成！共 {len(df)} 条数据 → {filename}")
    
    def close(self):
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    crawler = None
    try:
        # 大批量爬取建议开启无头模式 headless=True
        crawler = ZhaopinSeleniumCrawler(headless=True)
        crawler.crawl_all()
        crawler.save_to_csv(OUTPUT_CONFIG["filename"])
        
    except KeyboardInterrupt:
        print("\n用户中断，正在保存已抓取数据...")
        if crawler and crawler.all_jobs:
            crawler.save_to_csv(OUTPUT_CONFIG["filename"])
    except Exception as e:
        print(f"\n程序异常: {e}")
    finally:
        if crawler:
            crawler.close()