# -*- coding: utf-8 -*-
"""
智联招聘 Selenium 爬虫（配置驱动版）
✅ 模拟浏览器操作 | ✅ 自动等待 | ✅ 与 Flask 接口字段对齐
"""
import time
import random
import pandas as pd
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config_selenium import CITY_CODES, POSITION_CODES, CRAWL_STRATEGY, OUTPUT_CONFIG


class ZhaopinSeleniumCrawler:
    """智联招聘 Selenium 定向爬虫"""
    
    def __init__(self, headless=True):
        """
        初始化浏览器驱动
        :param headless: 是否无头模式（True=后台运行，False=可见浏览器便于调试）
        """
        # ✅ 配置 Chrome 选项
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-blink-features=AutomationControlled')  # 隐藏自动化特征
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # ✅ 自动管理 ChromeDriver（无需手动下载）
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
            """
        })
        
        self.base_url = "https://www.zhaopin.com/"
        self.all_jobs = []
        self.wait = WebDriverWait(self.driver, 15)  # 显式等待超时15秒
    
    def search_by_keyword_city(self, keyword, city_name):
        """
        模拟用户操作：输入关键词 + 选择城市
        :param keyword: 职位关键词（如 "Python"）
        :param city_name: 城市名称（如 "北京"）
        """
        print(f"🔍 搜索: {city_name} - {keyword}")
        
        # 1. 打开首页
        self.driver.get(self.base_url)
        time.sleep(random.uniform(2, 4))
        
        # 2. 输入关键词
        try:
            search_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='职位'], input[placeholder*='公司']"))
            )
            search_input.clear()
            search_input.send_keys(keyword)
            time.sleep(1)
        except Exception as e:
            print(f"⚠️  输入关键词失败: {e}")
            return False
        
        # 3. 选择城市（智联招聘的城市选择器较复杂，这里用简化方案）
        try:
            # 方案A：如果城市在搜索框下方有下拉选项
            city_dropdown = self.driver.find_elements(By.CSS_SELECTOR, ".city-select li, .location-list a")
            for city_elem in city_dropdown:
                if city_name in city_elem.text:
                    city_elem.click()
                    time.sleep(1)
                    break
            else:
                # 方案B：直接在URL中拼接城市编码（更可靠）
                city_code = CITY_CODES.get(city_name)
                if city_code:
                    self.driver.get(f"https://www.zhaopin.com/sou/jl{city_code}/p1?kw={keyword}")
                    time.sleep(2)
        except Exception as e:
            print(f"⚠️  选择城市失败，尝试URL直连: {e}")
            city_code = CITY_CODES.get(city_name, "530")  # 默认北京
            self.driver.get(f"https://www.zhaopin.com/sou/jl{city_code}/p1?kw={keyword}")
            time.sleep(2)
        
        return True
    
    def parse_job_card(self, card_elem):
        """
        解析单个职位卡片（基于你提供的真实HTML结构）
        :param card_elem: Selenium WebElement
        :return: dict 职位数据
        """
        try:
            # 🔧 辅助函数：安全提取文本
            def get_text(selector, parent=None):
                try:
                    elem = parent.find_element(By.CSS_SELECTOR, selector) if parent else card_elem.find_element(By.CSS_SELECTOR, selector)
                    return elem.text.strip()
                except:
                    return ""
            
            # 🔧 辅助函数：提取多个标签
            def get_tags(selector, parent=None):
                try:
                    elems = parent.find_elements(By.CSS_SELECTOR, selector) if parent else card_elem.find_elements(By.CSS_SELECTOR, selector)
                    return [el.text.strip() for el in elems if el.text.strip()]
                except:
                    return []
            
            # ✅ 提取职位信息（.jobinfo 内）
            job_name = get_text('.jobinfo__name')
            job_salary = get_text('.jobinfo__salary')
            
            # 地点：.jobinfo__other-info-item 下的 <span>
            location_span = card_elem.find_elements(By.CSS_SELECTOR, '.jobinfo__other-info-item span')
            job_area = location_span[0].text.strip() if location_span else ""
            
            # 经验/学历：按文本内容判断
            other_items = card_elem.find_elements(By.CSS_SELECTOR, '.jobinfo__other-info-item')
            work_year, education = "", ""
            for item in other_items:
                text = item.text.strip()
                if not text or '·' in text:  # 跳过地点
                    continue
                if any(kw in text for kw in ['经验不限', '应届', '1-3年', '3-5年', '5-10年', '10年以上']):
                    work_year = text
                elif any(kw in text for kw in ['学历不限', '初中', '高中', '中专', '大专', '本科', '硕士', '博士']):
                    education = text
            
            # 技能标签：限定在 .jobinfo__tag 内
            job_benefits = ", ".join(get_tags('.jobinfo__tag .joblist-box__item-tag'))
            
            # ✅ 提取公司信息（.companyinfo 是兄弟元素，需找父容器）
            parent = card_elem.find_element(By.XPATH, "./..")  # 向上找一层
            com_name = get_text('.companyinfo__name', parent)
            
            # 公司标签：类型/规模/行业
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
                "category_path": "",  # 后续填充
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"⚠️  解析单条失败: {e}")
            return None
    
    def crawl_page(self, category, subcategory, position):
        """
        爬取当前页职位列表
        :return: list 职位数据
        """
        jobs = []
        
        try:
            # ✅ 等待职位列表加载（显式等待）
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".jobinfo, .joblist-box__iteminfo"))
            )
            time.sleep(random.uniform(1, 2))  # 额外缓冲
            
            # 🔍 尝试两种可能的卡片选择器
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".jobinfo")
            if not job_cards:
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".joblist-box__iteminfo")
            
            if not job_cards:
                print("⚠️  未找到职位卡片，可能页面结构变化或需要登录")
                return []
            
            print(f"📦 当前页找到 {len(job_cards)} 个职位卡片")
            
            for i, card in enumerate(job_cards, 1):
                job = self.parse_job_card(card)
                if job and job["job_name"] and job["com_name"]:
                    job["category_path"] = f"{category}-{subcategory}-{position}"
                    jobs.append(job)
            
            print(f"✅ 解析成功 {len(jobs)}/{len(job_cards)} 条")
            
        except Exception as e:
            print(f"❌ 爬取页面失败: {e}")
            # 调试：保存当前页面源码
            # with open(f"debug_page_{datetime.now().strftime('%H%M%S')}.html", "w", encoding="utf-8") as f:
            #     f.write(self.driver.page_source)
        
        return jobs
    
    def next_page(self):
        """
        点击"下一页"按钮
        :return: bool 是否还有下一页
        """
        try:
            # 查找下一页按钮（多种可能的选择器）
            next_btn = None
            selectors = [
                "a[souid='soul_next']",      # 智联常见下一页标识
                ".soupager a:last-child",    # 分页最后一个
                "a:contains('下一页')",      # 文本包含（需JS执行）
            ]
            
            for selector in selectors:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                        break
                except:
                    continue
            
            if next_btn:
                # 滚动到可见区域再点击（避免元素被遮挡）
                self.driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(0.5)
                next_btn.click()
                time.sleep(random.uniform(2, 4))  # 等待新页面加载
                return True
            else:
                print("📌 未找到下一页按钮，可能已是最后一页")
                return False
                
        except Exception as e:
            print(f"⚠️  翻页失败: {e}")
            return False
    
    def crawl_all(self):
        """主爬取流程"""
        print(f"🚀 开始 Selenium 爬取，配置: 城市={CRAWL_STRATEGY['cities']}, 页数={CRAWL_STRATEGY['max_pages']}")
        
        for category, subcategory, positions in CRAWL_STRATEGY["enabled_combinations"]:
            for city in CRAWL_STRATEGY["cities"]:
                for position in positions:
                    print(f"\n{'='*60}")
                    print(f"📍 爬取: {city} - {category}→{subcategory}→{position}")
                    print(f"{'='*60}")
                    
                    # 1. 搜索关键词+城市
                    if not self.search_by_keyword_city(position, city):
                        continue
                    
                    # 2. 分页爬取
                    for page in range(1, CRAWL_STRATEGY["max_pages"] + 1):
                        print(f"📄 第 {page} 页")
                        
                        jobs = self.crawl_page(category, subcategory, position)
                        if not jobs:
                            print(f"⚠️  第{page}页无有效数据")
                            break
                        
                        self.all_jobs.extend(jobs)
                        print(f"📦 累计: {len(self.all_jobs)} 条")
                        
                        # 3. 翻页（最后一页不翻）
                        if page < CRAWL_STRATEGY["max_pages"]:
                            if not self.next_page():
                                break
                        
                        # 友好延迟
                        time.sleep(random.uniform(*CRAWL_STRATEGY["delay_range"]))
        
        return self.all_jobs
    
    def save_to_csv(self, filename):
        """保存数据到CSV"""
        if not self.all_jobs:
            print("⚠️  无数据可保存")
            return
        
        # ✅ 自动创建目录
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        
        # 转为DataFrame并保存
        df = pd.DataFrame(self.all_jobs)
        df = df[OUTPUT_CONFIG["fields"]]
        df.to_csv(filename, index=False, encoding=OUTPUT_CONFIG["encoding"])
        
        print(f"\n🎉 保存完成！共 {len(df)} 条数据 → {filename}")
        print(f"📊 数据预览:\n{df.head(3).to_markdown(index=False)}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("🔚 浏览器已关闭")


# ==================== 主程序入口 ====================
if __name__ == "__main__":
    crawler = None
    try:
        # ✅ 建议：首次调试用 headless=False，可见浏览器便于排查问题
        crawler = ZhaopinSeleniumCrawler(headless=True)
        crawler.crawl_all()
        crawler.save_to_csv(OUTPUT_CONFIG["filename"])
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，正在清理...")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
    finally:
        if crawler:
            crawler.close()
        
        print(f"\n✅ 爬虫结束！下一步:")
        print(f"   1. 用Excel打开 {OUTPUT_CONFIG['filename']} 检查数据")
        print(f"   2. 启动Flask: python app.py")
        print(f"   3. 访问 http://127.0.0.1:5000 查看可视化")