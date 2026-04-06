# 生物医药科技新闻自动推送系统

## 📋 系统概述

每周自动抓取生物医药科技新闻，生成智能摘要，推送到微信和邮箱，并生成双人对话播客。

**推送频率**：每周2次（周四 + 周日，北京时间08:00）

---

## 🎯 功能特性

### 阶段一：文字周刊
- ✅ RSS自动抓取（学术期刊 + RSSHub国际源）
- ✅ AI智能摘要（阿里云百炼qwen-turbo）
- ✅ 多渠道推送（Server酱微信 + 钉钉 + SMTP邮箱）
- ✅ GitHub Actions定时执行

### 阶段二：双人对话播客
- ✅ 对话脚本生成（大模型改写）
- ✅ 分角色音频生成（男声云希 + 女声晓晓）
- ✅ 音频合并导出（MP3格式）
- ✅ GitHub Pages托管（支持播客App订阅）

---

## 🚀 快速开始

### 本地测试

```bash
cd biomed_news_weekly

# 安装依赖
pip install feedparser requests openai edge-tts pydub

# 测试运行（仅抓取不推送）
python main.py --test

# 立即推送
python main.py

# 生成播客
python main.py --podcast
```

### GitHub Actions部署

1. Fork 或 Clone 本仓库
2. 在 Settings → Secrets 中添加：
   - `DASHSCOPE_API_KEY`：阿里云百炼API Key
3. 进入 Actions → "BioMed News Weekly Push" → Run workflow

---

## 📁 文件结构

```
biomed_news_weekly/
├── .github/workflows/
│   └── weekly.yml              # GitHub Actions工作流
├── config.json                 # RSS源和推送配置
├── main.py                     # 主脚本
├── podcast_generator.py        # 播客生成器
├── dashscope_key.txt           # 阿里云百炼API Key（本地）
├── requirements.txt            # Python依赖
├── README.md                   # 本文件
├── reports/                    # 生成的周刊
└── podcasts/                   # 生成的播客音频
```

---

## 🔧 配置说明

### config.json

```json
{
  "feeds": [
    {"name": "China CDC Weekly", "url": "https://weekly.chinacdc.cn/rss/current.xml", "max_items": 5},
    {"name": "北京大学学报医学版", "url": "http://xuebao.bjmu.edu.cn/CN/rss_lm_5_1671-167X.xml", "max_items": 5},
    {"name": "现代药物与临床", "url": "http://www.tiprpress.com/rss/", "max_items": 4},
    {"name": "中国心血管病研究", "url": "http://xxgzz.ijournals.cn/rss/", "max_items": 4}
  ],
  "feeds_backup": [
    {"name": "PubMed最新论文", "url": "https://rsshub.app/pubmed/recent", "max_items": 6},
    {"name": "FDA新闻", "url": "https://rsshub.app/fda/news", "max_items": 5},
    {"name": "Nature中文精选", "url": "https://rsshub.app/nature/chinese", "max_items": 5},
    {"name": "ScienceDaily生物学", "url": "https://rsshub.app/sciencedaily/biology", "max_items": 5}
  ],
  "push": {
    "serverchan_key": "你的Server酱SendKey",
    "dingtalk_webhook": "你的钉钉Webhook",
    "emails": ["your@email.com"]
  }
}
```

---

## 📤 推送渠道

| 渠道 | 说明 | 状态 |
|------|------|------|
| Server酱 | 微信公众号推送 | ✅ |
| 钉钉机器人 | 群消息推送 | ✅ |
| SMTP邮箱 | 邮件推送 | ✅ |
| GitHub Pages | 播客RSS托管 | ✅ |

---

## 📊 数据源

### 学术期刊RSS（已验证可用）
| 期刊 | 内容特色 |
|------|---------|
| China CDC Weekly | 公共卫生动态 |
| 北京大学学报医学版 | 综合医学研究 |
| 现代药物与临床 | 新药研发 |
| 中国心血管病研究 | 心血管专业 |

### RSSHub国际源
| 来源 | 内容特色 |
|------|---------|
| PubMed最新论文 | 生物医学研究 |
| FDA新闻 | 药监动态 |
| Nature中文精选 | 顶级期刊 |
| ScienceDaily生物学 | 科普资讯 |

---

## ⏰ 定时任务

- **执行时间**：北京时间每周四、周日 08:00
- **执行方式**：GitHub Actions云端运行
- **无需本地开机**：完全自动化

---

## 💰 成本分析

| 服务 | 免费额度 | 实际成本 |
|------|----------|----------|
| GitHub Actions | 2000分钟/月 | 0元 |
| 阿里云百炼 | 新用户10万tokens | 0元 |
| Server酱 | 每日5条 | 0元 |
| GitHub Pages | 无限流量 | 0元 |
| edge-tts | 完全免费 | 0元 |

**总成本：0元/月**

---

## 📝 更新日志

### 2026-04-06
- ✅ 项目初始化
- ✅ 完成数据源验证
- ✅ 配置学术期刊RSS + RSSHub国际源
- ✅ GitHub Actions定时任务配置
- ✅ 定制化AI摘要Prompt（生物医疗领域）

---

## 🔗 相关链接

- AI科技新闻项目（参考）：`C:\Users\lw\WorkBuddy\Claw\ai_news_daily`
- 数据源调研报告：见项目规划文档

---

_由 生物医药科技新闻自动推送系统 生成_