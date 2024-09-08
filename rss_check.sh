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
  readarray -t guids < <(xmlstarlet sel -t -m "//item" -v "guid" -n formatted_rss.xml)
  
  for guid in "${guids[@]}"; do
    # 检查 guid 是否已存在于缓存中
    if ! grep -qF -- "$guid" "$CACHE_FILE"; then
      # 如果这是一个新帖子，提取详细信息并发送通知
      title=$(xmlstarlet sel -t -m "//item[guid='$guid']" -v "title" formatted_rss.xml)
      description=$(xmlstarlet sel -t -m "//item[guid='$guid']" -v "description" formatted_rss.xml)
      link=$(xmlstarlet sel -t -m "//item[guid='$guid']" -v "link" formatted_rss.xml)
      category=$(xmlstarlet sel -t -m "//item[guid='$guid']" -v "category" formatted_rss.xml)

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
              --arg category "$category" \
              --arg chatid "$TELEGRAM_CHAT_ID" \
              '{
                chat_id: "\($chatid)\n",
                text: "*标题*: \($title)\n*简述*: \($description)\n*分类*: \($category)",
                parse_mode: "Markdown",
                reply_markup: {
                  inline_keyboard: [
                    [
                      {
                        text: "链接",
                        url: "\($link)\n"
                      }
                    ]
                  ]
                }
              }')
            # 打印调试信息
            #echo "Generated JSON message:"
            #echo "$message"
            # 发送通知到 Telegram
            curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
              -H "Content-Type: application/json" \
              -d "$message"
            # 打印响应调试信息
            echo "Telegram API response:"
            echo "$response"
            echo $'\n'
            # 将 guid 添加到缓存中
            echo "$guid" >> "$CACHE_FILE"
            echo "New post detected and notified: $title"
            echo $'\n'
            # 跳至下一个帖子
            break
          fi
      done
    fi
  done
}

check_new_posts
