#!/bin/bash

# 创建临时目录
TEMP_DIR=$(mktemp -d)
CACHE_FILE="rss_cache.txt"

# 定义 RSS 源数组
RSS_FEEDS=(
  "https://linux.do/latest.rss"
  "https://www.v2ex.com/index.xml"
  "https://www.nodeseek.com/rss.xml"
  "https://hostloc.com/forum.php?mod=rss"
)

# 函数：检查单个 RSS 源
check_rss() {
  local rss_url="$$1"
  local LATEST_RSS="$TEMP_DIR/latest_rss.xml"
  local FORMATTED_RSS="$TEMP_DIR/formatted_rss.xml"

  # 下载最新的 RSS feed
  if ! curl -s "$rss_url" > "$LATEST_RSS"; then
    echo "Failed to download RSS feed from $rss_url"
    return
  fi

  # 使用 xmlstarlet 格式化 RSS feed
  if ! xmlstarlet fo -R "$LATEST_RSS" > "$FORMATTED_RSS" 2>/dev/null; then
    echo "Failed to parse RSS feed from $rss_url"
    return
  fi

  # 解析 RSS feed 并发送 Telegram 通知
  while IFS= read -r line; do
    title=$(echo "$line" | cut -f1)
    link=$(echo "$line" | cut -f2)
    guid=$(echo "$line" | cut -f3)
    date=$(echo "$line" | cut -f4)

    # 检查这个 GUID 是否已经在缓存中
    if ! grep -q "^$guid:" "$CACHE_FILE"; then
      # 构造消息：只包含标题
      message="$title"
      # 准备 JSON 格式的 reply_markup
      reply_markup=$(jq -n --arg url "$link" \
        '{"inline_keyboard":[[{"text":"查看原文","url":$$url}]]}')
      # 发送消息，包含链接预览
      curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -H "Content-Type: application/json" \
        -d "$$(jq -n \
          --arg chat_id "$TELEGRAM_CHAT_ID" \
          --arg text "$message" \
          --argjson reply_markup "$reply_markup" \
          '{
            chat_id: $chat_id,
            text: $text,
            parse_mode: "HTML",
            disable_web_page_preview: false,
            reply_markup: $reply_markup
          }'
        )"
      # 将新的 GUID 添加到缓存文件
      echo "$guid:$$date" >> "$CACHE_FILE"
    fi
  done < <(xmlstarlet sel -T -t -m "//item" -v "concat(title, '&#9;', link, '&#9;', guid, '&#9;', pubDate)" -n "$FORMATTED_RSS")
}

# 主循环：检查每个 RSS 源
for feed in "${RSS_FEEDS[@]}"; do
  check_rss "$feed"
done

# 清理临时文件
trap 'rm -rf "$TEMP_DIR"' EXIT

# 清理旧的缓存条目（可选，保留最近30天的条目）
sed -i -e :a -e '$q;N;30,$D;ba' "$CACHE_FILE"
