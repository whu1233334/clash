import feedparser
import os
import requests
import json
from datetime import datetime, timedelta

# RSS 源列表
RSS_URLS = [
    "https://linux.do/latest.rss",
    "https://www.v2ex.com/index.xml",
    "https://www.nodeseek.com/rss.xml",
    "https://hostloc.com/forum.php?mod=rss"
]

# 关键词列表
KEYWORDS = ["白嫖", "免费", "抽", "羊毛", "奖", "送"]

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 已推送帖子的记录文件
SENT_POSTS_FILE = 'sent_posts.json'

def load_sent_posts():
    if os.path.exists(SENT_POSTS_FILE):
        with open(SENT_POSTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_sent_posts(sent_posts):
    with open(SENT_POSTS_FILE, 'w') as f:
        json.dump(sent_posts, f)

def send_telegram_message(title, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    message = f"*{title}*\n\n[点击查看详情]({link})"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    response = requests.post(url, json=payload)
    return response.json()

def check_rss_feeds():
    sent_posts = load_sent_posts()
    current_time = datetime.utcnow()
    
    for rss_url in RSS_URLS:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            # 使用链接作为唯一标识符
            post_id = entry.link
            
            # 如果帖子已经发送过，跳过
            if post_id in sent_posts:
                continue
            
            # 检查帖子是否在过去24小时内发布
            if 'published_parsed' in entry:
                publish_time = datetime(*entry.published_parsed[:6])
                if current_time - publish_time > timedelta(hours=24):
                    continue
            
            title = entry.title
            link = entry.link
            
            # 检查标题是否包含关键词
            if any(keyword in title.lower() for keyword in KEYWORDS):
                print(f"发现匹配的帖子: {title}")
                response = send_telegram_message(title, link)
                if response.get('ok'):
                    print("消息发送成功")
                    # 记录已发送的帖子
                    sent_posts[post_id] = current_time.isoformat()
                else:
                    print(f"消息发送失败: {response.get('description')}")
    
    # 保存更新后的已发送帖子记录
    save_sent_posts(sent_posts)

if __name__ == "__main__":
    check_rss_feeds()
