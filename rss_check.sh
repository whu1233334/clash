#!/bin/bash

# RSS 订阅地址
RSS_URL="https://linux.do/latest.rss"
# 本地缓存文件，名字可随便改
CACHE_FILE="./rss_cache.txt"
# Telegram Bot API Key
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
# Telegram chat ID，可以是私人或群组的 chat ID
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID}"
# 关键词数组，只要其中一个出现就推送
KEYWORDS=("白嫖" "免费" "薅羊毛")

# 函数：下载 RSS 并检查新条目
check_new_posts() {
  # 下载最新的 RSS 数据
  curl -s "$RSS_URL" > latest_rss.xml

  # 为了确保正确处理特殊字符，先转换 XML
  xmlstarlet fo --recover latest_rss.xml 2>/dev/null > formatted_rss.xml

  # 检查是否有缓存文件，如果没有，则创建一个空的
  if [ ! -f "$CACHE_FILE" ]; then
    touch "$CACHE_FILE"
  fi

  # 解析新条目并检查新帖子
  IFS=$'\n' # 设置内部字段分隔符为换行符，以正确读取每条记录
  readarray -t links < <(xmlstarlet sel -t -m "//item" -v "link" -n formatted_rss.xml)
  for link in "${links[@]}"; do
    # 检查 link 是否已存在于缓存中
    if ! grep -qF -- "$link" "$CACHE_FILE"; then
      # 如果这是一个新帖子，提取详细信息并发送通知
      title=$(xmlstarlet sel -t -m "//item[link='$link']" -v "title" formatted_rss.xml)
      description=$(xmlstarlet sel -t -m "//item[link='$link']" -v "description" formatted_rss.xml)

      # 清理描述中的 HTML 标签
      description=$(echo "$description" | sed 's/<[^>]*>//g')
      # 截断描述到 200 字符
      description=$(echo "$description" | cut -c 1-200)"..."

      # 检查标题和简述是否包含任何关键词
      for KEYWORD in "${KEYWORDS[@]}"; do
          if ((echo "$title" | grep -iq "$KEYWORD") || (echo "$description" | grep -iq "$KEYWORD")); then
            # 确保提取的字段不为空
            description=${description:-No description available.}
    
            # 格式化消息
            message=$(jq -n \
              --arg title "$title" \
              --arg description "$description" \
              --arg link "$link" \
              --arg chatid "$TELEGRAM_CHAT_ID" \
              '{
                chat_id: $chatid,
                text: "*标题*: \($title)\n*简述*: \($description)",
                parse_mode: "Markdown",
                reply_markup: {
                  inline_keyboard: [
                    [
                      {
                        text: "链接",
                        url: $link
                      }
                    ]
                  ]
                }
              }')

            # 发送通知到 Telegram
            response=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
              -H "Content-Type: application/json" \
              -d "$message")

            # 检查 Telegram API 响应
            if echo "$response" | jq -e '.ok == true' > /dev/null; then
              echo "成功发送通知: $title"
            else
              echo "发送通知失败: $title"
              echo "Telegram API 错误: $(echo "$response" | jq -r '.description')"
            fi

            # 将 link 添加到缓存中
            echo "$link" >> "$CACHE_FILE"
            
            # 跳至下一个帖子
            break
          fi
      done
    fi
  done
}

check_new_posts
