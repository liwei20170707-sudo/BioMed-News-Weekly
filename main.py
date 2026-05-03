"""
生物医药科技新闻自动摘要推送系统 - 阶段一 + 阶段二
功能：RSS抓取 + 阿里云百炼摘要 + 多渠道推送（微信+邮箱）+ 双人对话播客

使用方式：
  python main.py [--test] [--no-summary] [--podcast]
  
参数：
  --test      测试模式，只抓取不推送
  --no-summary 不生成AI摘要，直接推送原始标题
  --podcast   生成播客音频（阶段二功能）
"""

import os
import sys

# Windows控制台编码修复
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import json
import re
import time
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# 第三方库
try:
    import feedparser
    from openai import OpenAI
except ImportError:
    print("❌ 缺少依赖，请先安装: pip install feedparser openai")
    sys.exit(1)

# ========== 配置加载 ==========
CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        print(f"❌ 配置文件不存在: {CONFIG_FILE}")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 处理环境变量
    dashscope_key = os.environ.get('DASHSCOPE_API_KEY')
    if not dashscope_key:
        # 尝试从本地配置读取
        local_key_file = Path(__file__).parent / "dashscope_key.txt"
        if local_key_file.exists():
            dashscope_key = local_key_file.read_text(encoding='utf-8').strip()
    
    if not dashscope_key:
        print("⚠️ 未配置阿里云百炼API Key，将跳过AI摘要")
        config['dashscope']['api_key'] = None
    else:
        config['dashscope']['api_key'] = dashscope_key
    
    return config

# ========== 大模型摘要 ==========
def create_summary_client(config):
    """创建阿里云百炼客户端"""
    if not config['dashscope']['api_key']:
        return None
    
    return OpenAI(
        api_key=config['dashscope']['api_key'],
        base_url=config['dashscope'].get('base_url', "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    )

def summarize_news(client, title, snippet, model="qwen-turbo"):
    """调用阿里云百炼生成一句话摘要"""
    if not client:
        return snippet[:80] if snippet else "暂无摘要"
    
    prompt = f"""你是一位生物医药领域的资深编辑。请用一句话总结下面新闻，要求：
- 点出技术/医学本质（如：基因编辑、免疫疗法、新药研发等）
- 说明对患者/医疗行业/科研人员的实际影响
- 使用专业但易懂的语言
- 不超过80字

标题：{title}
内容：{snippet[:350]}
一句话总结："""
    
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ 摘要生成失败: {e}")
        return snippet[:80] if snippet else "摘要生成失败"

# ========== RSS抓取 ==========
def fetch_rss_feed(url, max_items=10):
    """抓取RSS源"""
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            title = entry.get('title', '无标题')
            link = entry.get('link', '#')
            # 清理HTML标签
            desc = entry.get('description', '') or entry.get('summary', '')
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()
            
            items.append({
                'title': title,
                'link': link,
                'desc': desc[:500]
            })
        return items
    except Exception as e:
        print(f"⚠️ 抓取失败 {url}: {e}")
        return []

def fetch_all_feeds(config, use_backup=False):
    """抓取所有RSS源"""
    feeds = config['feeds'] if not use_backup else config.get('feeds_backup', [])
    all_items = []
    
    for feed in feeds:
        print(f"📡 抓取: {feed['name']}")
        items = fetch_rss_feed(feed['url'], feed['max_items'])
        for item in items:
            item['source'] = feed['name']
        all_items.extend(items)
        print(f"   ✅ 获取 {len(items)} 条")
    
    # 去重（按标题）
    seen = set()
    unique = []
    for item in all_items:
        key = item['title'][:50]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    return unique[:40]  # 限制总数

# ========== 内容生成 ==========
def build_markdown_report(news_list, date_str):
    """生成Markdown格式报告（完整版，用于邮件）"""
    lines = [
        f"# 🧬 生物医疗科技周刊 - {date_str}",
        "",
        f"📅 {datetime.now().strftime('%Y年%m月%d日')} | 共 {len(news_list)} 条精选",
        "",
        "---",
        ""
    ]
    
    for idx, item in enumerate(news_list, 1):
        lines.append(f"## {idx}. {item['title']}")
        lines.append(f"> 📌 {item.get('summary', item['desc'][:80])}")
        lines.append(f"🔗 [阅读原文]({item['link']}) | 📡 {item['source']}")
        lines.append("")
    
    lines.append("---")
    lines.append("🧬 生物医疗科技新闻自动推送系统 | 阿里云百炼智能摘要")
    
    return "\n".join(lines)

def build_serverchan_content(news_list, date_str, max_items=10):
    """生成Server酱精简版内容（免费版限制长度）"""
    lines = [
        f"**🧬 生物医疗科技周刊**",
        f"",
        f"📅 {date_str} | 精选{min(len(news_list), max_items)}条",
        f"",
    ]
    
    for idx, item in enumerate(news_list[:max_items], 1):
        # 精简格式：标题 + 链接
        title_short = item['title'][:50] if len(item['title']) > 50 else item['title']
        lines.append(f"**{idx}. {title_short}**")
        lines.append(f"[阅读原文]({item['link']})")
        lines.append("")
    
    lines.append("---")
    lines.append("💡 完整版已发送至邮箱，更多详情请查看邮件")
    
    return "\n".join(lines)

def build_html_report(news_list, date_str):
    """生成HTML格式报告（用于邮件）"""
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                   background: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; 
                         padding: 30px; border-radius: 10px; }}
            h1 {{ color: #1a1a1a; border-bottom: 2px solid #4a90d9; padding-bottom: 10px; }}
            h2 {{ color: #333; margin-top: 25px; font-size: 18px; }}
            .summary {{ background: #f0f7ff; padding: 10px 15px; border-radius: 5px; 
                       margin: 10px 0; color: #555; }}
            .meta {{ color: #888; font-size: 14px; margin-top: 5px; }}
            a {{ color: #4a90d9; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; 
                      color: #999; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧬 生物医疗科技周刊 - {date_str}</h1>
            <p>📅 {datetime.now().strftime('%Y年%m月%d日')} | 共 {len(news_list)} 条精选</p>
    """
    
    for idx, item in enumerate(news_list, 1):
        html += f"""
            <h2>{idx}. {item['title']}</h2>
            <div class="summary">📌 {item.get('summary', item['desc'][:80])}</div>
            <div class="meta">📡 来源：{item['source']} | <a href="{item['link']}">阅读原文</a></div>
        """
    
    html += """
            <div class="footer">
                🧬 生物医疗科技新闻自动推送系统 | 阿里云百炼智能摘要
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

# ========== 推送渠道 ==========

def push_dingtalk(config, title, content):
    """钉钉群机器人推送"""
    webhook_url = config['push'].get('dingtalk_webhook')
    if not webhook_url:
        print("⚠️ 钉钉Webhook未配置")
        return False
    
    # 钉钉消息格式（Markdown）
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content
        }
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = resp.read().decode('utf-8')
        
        if '"errcode":0' in result:
            print("✅ 钉钉推送成功")
            return True
        else:
            print(f"⚠️ 钉钉推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 钉钉推送失败: {e}")
        return False

def push_serverchan(config, title, content):
    """Server酱微信推送"""
    send_key = config['push']['serverchan_key']
    if not send_key:
        print("⚠️ Server酱SendKey未配置")
        return False
    
    url = f"https://sctapi.ftqq.com/{send_key}.send"
    data = urllib.parse.urlencode({
        "title": title,
        "desp": content
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # 增加超时时间
            result = resp.read().decode('utf-8')
        if '"code":0' in result or '"errno":0' in result:
            print("✅ Server酱推送成功")
            return True
        else:
            print(f"⚠️ Server酱推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ Server酱推送失败: {e}")
        return False

def push_smtp_email(config, title, html_content):
    """SMTP直接发送邮件（备用方案）"""
    # 使用项目已有的126邮箱配置
    smtp_host = "smtp.126.com"
    smtp_port = 465
    smtp_user = "david_lw2012@126.com"
    smtp_pass = "YYVBJ4F8cGBrGCXQ"
    
    emails = config['push']['emails']
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = title
        msg['From'] = f"AI助手 <{smtp_user}>"
        msg['To'] = ", ".join(emails)
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        import ssl
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, emails, msg.as_string())
        
        print(f"✅ SMTP邮件发送成功: {emails}")
        return True
    except Exception as e:
        print(f"❌ SMTP邮件发送失败: {e}")
        return False

def push_workbuddy(config, title, content):
    """腾讯WorkBuddy推送（通过本地推送接口）"""
    # 检查是否有本地推送脚本
    push_script = Path(__file__).parent.parent / "serverchan_push.py"
    message_file = Path(__file__).parent.parent / "message.txt"
    
    if push_script.exists() and message_file.exists():
        # 写入消息文件
        message_file.write_text(content, encoding='utf-8')
        print("✅ 已写入本地消息文件，可通过WorkBuddy推送")
        return True
    else:
        print("⚠️ 本地推送脚本不存在，跳过WorkBuddy推送")
        return False

# ========== 主流程 ==========
def main():
    """主流程"""
    print("=" * 50)
    print("🧬 生物医疗科技新闻自动推送系统 - 阶段一")
    print("=" * 50)
    
    # 解析参数
    test_mode = '--test' in sys.argv
    no_summary = '--no-summary' in sys.argv
    
    # 加载配置
    config = load_config()
    
    # 抓取新闻
    print("\n📡 开始抓取RSS源...")
    news_list = fetch_all_feeds(config)
    
    if not news_list:
        print("❌ 未获取到任何新闻")
        return
    
    print(f"\n✅ 共抓取 {len(news_list)} 条新闻")
    
    # 生成摘要
    if not no_summary and config['dashscope']['api_key']:
        print("\n🧠 正在生成AI摘要...")
        client = create_summary_client(config)
        
        for i, news in enumerate(news_list):
            print(f"  [{i+1}/{len(news_list)}] {news['title'][:40]}...")
            news['summary'] = summarize_news(client, news['title'], news['desc'])
            time.sleep(0.5)  # 避免API限流
    else:
        # 使用原始描述作为摘要
        for news in news_list:
            news['summary'] = news['desc'][:80] if news['desc'] else "暂无摘要"
    
    # 生成报告
    date_str = datetime.now().strftime('%Y年%m月%d日')
    title = f"🧬 生物医疗科技周刊 - {date_str}"
    
    markdown_report = build_markdown_report(news_list, date_str)  # 完整版
    serverchan_content = build_serverchan_content(news_list, date_str, max_items=10)  # 精简版
    html_report = build_html_report(news_list, date_str)
    
    # 保存报告
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    
    report_file = report_dir / f"生物医疗周刊_{datetime.now().strftime('%Y%m%d')}.md"
    report_file.write_text(markdown_report, encoding='utf-8')
    print(f"\n📄 报告已保存: {report_file}")
    
    # 测试模式不推送
    if test_mode:
        print("\n⚠️ 测试模式，跳过推送")
        print("\n--- 报告预览 ---")
        print(markdown_report[:500])
        return
    
    # 推送
    print("\n📤 开始推送...")
    
    # 1. 钉钉推送（优先，无次数限制）
    push_dingtalk(config, title, serverchan_content)
    
    # 2. Server酱推送（使用精简版）
    push_serverchan(config, title, serverchan_content)
    
    # 3. SMTP邮箱推送（备用）
    push_smtp_email(config, title, html_report)
    
    # 4. WorkBuddy推送
    push_workbuddy(config, title, markdown_report)
    
    # ========== 阶段二：播客生成 ==========
    podcast_mode = '--podcast' in sys.argv
    
    if podcast_mode and config['dashscope']['api_key']:
        print("\n" + "=" * 50)
        print("🎙️ 阶段二：生成播客音频")
        print("=" * 50)
        
        try:
            import asyncio
            from podcast_generator import generate_podcast
            
            client = create_summary_client(config)
            result = asyncio.run(generate_podcast(client, news_list, date_str))
            
            if result:
                print(f"\n✅ 播客生成成功！")
                print(f"   时长: {result['duration'] // 60}分{result['duration'] % 60}秒")
                print(f"   文件: {result['audio_file']}")
        except ImportError as e:
            print(f"⚠️ 播客模块未安装: {e}")
            print("   请运行: pip install edge-tts pydub")
        except Exception as e:
            print(f"❌ 播客生成失败: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 任务完成！")
    print("=" * 50)

if __name__ == "__main__":
    main()