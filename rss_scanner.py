import os
import json
import feedparser
import requests
import re
from datetime import datetime, timezone, timedelta

# 配置
RSS_FEEDS = [
    'https://linux.do/latest.rss',
    'https://www.v2ex.com/index.xml',
    'https://www.nodeseek.com/rss.xml',
    'https://hostloc.com/forum.php?mod=rss'
]
KEYWORDS = ['白嫖', '优惠', '免费', '折扣', '推广', '抽奖', "送", "抽", "羊毛"]
SENT_POSTS_FILE = os.path.join(os.getcwd(), 'sent_posts.json')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def load_sent_posts():
    if os.path.exists(SENT_POSTS_FILE):
        try:
            with open(SENT_POSTS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"警告：{SENT_POSTS_FILE} 文件内容无效，将使用空字典")
    else:
        print(f"{SENT_POSTS_FILE} 文件不存在，将创建新文件")
    return {}

def save_sent_posts(sent_posts):
    try:
        with open(SENT_POSTS_FILE, 'w') as f:
            json.dump(sent_posts, f, indent=2)
        print(f"成功保存 {len(sent_posts)} 条记录到 {SENT_POSTS_FILE}")
        # 添加文件检查
        if os.path.exists(SENT_POSTS_FILE):
            with open(SENT_POSTS_FILE, 'r') as f:
                content = f.read()
            print(f"文件内容:\n{content}")
        else:
            print(f"错误：文件 {SENT_POSTS_FILE} 不存在")
    except Exception as e:
        print(f"保存到 {SENT_POSTS_FILE} 时出错: {e}")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("消息发送成功")
    else:
        print(f"消息发送失败，状态码：{response.status_code}，响应：{response.text}")

def check_rss_feeds():
    sent_posts = load_sent_posts()
    current_time = datetime.now(timezone.utc)
    time_threshold = current_time - timedelta(hours=24)  # 24小时前的时间

    new_posts = False

    print("开始检查 RSS 源")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"SENT_POSTS_FILE 路径: {SENT_POSTS_FILE}")

    for feed_url in RSS_FEEDS:
        print(f"正在解析 RSS 源: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"警告: 从 {feed_url} 没有获取到任何条目")
                continue
            print(f"从 {feed_url} 获取到 {len(feed.entries)} 个条目")

            for entry in feed.entries:
                title = entry.get('title', '')
                link = entry.get('link', '')
                published_time = entry.get('published_parsed')
                
                if published_time:
                    entry_time = datetime(*published_time[:6], tzinfo=timezone.utc)
                else:
                    entry_time = current_time

                print(f"检查条目: {title} - {link}")
                print(f"发布时间: {entry_time}")

                # 只处理最近24小时内的帖子
                if entry_time > time_threshold:
                    if any(keyword.lower() in title.lower() for keyword in KEYWORDS) and link not in sent_posts:
                        print(f"发现匹配的帖子: {title}")
                        message = f"{title}\n{link}"
                        send_telegram_message(message)
                        sent_posts[link] = entry_time.isoformat()
                        new_posts = True
                    else:
                        if link in sent_posts:
                            print(f"帖子已经发送过: {title}")
                        else:
                            print(f"帖子不匹配关键词: {title}")
                else:
                    print(f"帖子超出时间范围: {title}")

        except Exception as e:
            print(f"解析 {feed_url} 时出错: {e}")

    if new_posts:
        print("发现新的匹配帖子，正在更新 sent_posts.json")
        save_sent_posts(sent_posts)
    else:
        print("没有发现新的匹配帖子")

    print("RSS 检查完成")



if __name__ == "__main__":
    # 强制创建文件（如果不存在）
    if not os.path.exists(SENT_POSTS_FILE):
        with open(SENT_POSTS_FILE, 'w') as f:
            json.dump({}, f)
        print(f"创建了新的 {SENT_POSTS_FILE} 文件")

    check_rss_feeds()
