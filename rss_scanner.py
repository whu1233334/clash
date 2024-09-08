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
KEYWORDS = ["白嫖", "免费", "抽"]

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 已推送帖子的记录文件
SENT_POSTS_FILE = 'sent_posts.json'

def load_sent_posts():
    if os.path.exists(SENT_POSTS_FILE):
        try:
            with open(SENT_POSTS_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    print("sent_posts.json 文件为空，将使用空字典")
                    return {}
        except json.JSONDecodeError as e:
            print(f"解析 sent_posts.json 时出错: {e}")
            print("将使用空字典并覆盖损坏的文件")
            return {}
    else:
        print("sent_posts.json 文件不存在，将创建新文件")
        return {}

def save_sent_posts(sent_posts):
    try:
        with open(SENT_POSTS_FILE, 'w') as f:
            json.dump(sent_posts, f, indent=2)
        print(f"成功保存 {len(sent_posts)} 条记录到 {SENT_POSTS_FILE}")
    except Exception as e:
        print(f"保存到 {SENT_POSTS_FILE} 时出错: {e}")

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
    new_posts_found = False
    
    for rss_url in RSS_URLS:
        print(f"正在解析 RSS 源: {rss_url}")
        feed = feedparser.parse(rss_url)
        if feed.entries:
            print(f"从 {rss_url} 获取到 {len(feed.entries)} 个条目")
        else:
            print(f"警告: 从 {rss_url} 没有获取到任何条目")
            continue
        
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
                    new_posts_found = True
                else:
                    print(f"消息发送失败: {response.get('description')}")
    
    if new_posts_found:
        print(f"发现新的匹配帖子，正在更新 {SENT_POSTS_FILE}")
        save_sent_posts(sent_posts)
    else:
        print("没有发现新的匹配帖子，不更新缓存文件")

if __name__ == "__main__":
    print("开始检查 RSS 源")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"SENT_POSTS_FILE 路径: {os.path.abspath(SENT_POSTS_FILE)}")
    check_rss_feeds()
    print("RSS 检查完成")
