# 黄果短剧爬虫

针对 `https://7e1be.uc41p53k.cc/` 的视频爬虫。**只需提供首页地址**，程序会自动发现所有视频频道、遍历分页、抓取每个视频详情，并将结果保存为 **XLSX** 文件。

## 抓取字段

| 字段 | 说明 | 数据来源 |
|------|------|----------|
| 网站网址 | 视频详情页 URL | 列表卡片 `/video/{id}/` |
| 视频名称 | 标题 `title` | 详情页 JSON |
| 视频集数 | 剧集数量 | 详情页 `epPlaySrcs` 集数 |
| 视频的地址 | 第 1 集 m3u8 播放地址 | 详情页 `epPlaySrcs` |
| 视频封面url | 封面图片 URL | 详情页 `coverSrc` |
| 视频介绍 | 简介/描述 | 详情页 `description` |
| 点赞数量 | 点赞数 | 详情页 `likesNum` |
| 关注数量 | 作者粉丝数 | 作者页 `data-author-followers` |

另外附带辅助字段：视频ID（卡片ID）、分类、播放量、收藏数量、评分、作者、作者ID、标签、发布时间、详情页URL、全部剧集地址。

## 自动发现频道

程序从首页顶部导航自动识别视频类频道（`data-nav-key` 以 `ai-` 开头的项），当前可自动发现：

- `ai-duanju`：AI成人短剧
- `ai-manju`：AI成人漫剧
- `ai-huanlian`：AI换脸
- `ai-mogai`：AI魔改

若首页结构变化导致自动发现失败，会回退到 `spider/config.py` 中的 `FALLBACK_CHANNELS`。你也可以手动增删该列表。

分页通过列表页的 `data-pages="N"` 属性确定最大页数（例如 `/ai-duanju/` 共 50 页），再用 for 循环逐页请求 `/ai-duanju/{n}/`。

## 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)（依赖管理）

## 安装与运行

```bash
# 安装依赖
uv sync

# 仅提供首页地址即可自动爬取全部频道，写入 output/huangguo_videos.xlsx
uv run main.py

# 指定站点首页
uv run main.py --url https://7e1be.uc41p53k.cc/

# 调试：每个频道只抓前 1 页，输出到自定义文件
uv run main.py --max-pages 1 -o output/sample.xlsx

# 不抓取作者粉丝数（更快，约省一半请求）
uv run main.py --no-followers

# 查看全部参数
uv run main.py -h
```

## 项目结构

```
huangguo/
├── main.py               # 入口/CLI
├── spider/
│   ├── config.py         # 站点、频道发现、请求头、路径等配置
│   ├── models.py         # VideoItem 数据模型 + XLSX 列定义
│   ├── client.py         # HTTP 客户端（重试/限速/随机UA）
│   ├── parser.py         # 列表页/详情页/作者页/频道发现解析
│   ├── storage.py        # XLSX 增量落盘（断点续抓）
│   └── crawler.py        # 任务编排
└── output/               # XLSX 输出目录
```

## 特性

- **纯 `requests` 实现**：目标站可直接访问，无需浏览器渲染。
- **一键爬取**：只给首页地址，自动发现频道并分页遍历。
- **数据准确**：核心字段取自详情页内嵌的 `videoInitialData` JSON；每集 m3u8 地址、集数齐全。
- **断点续抓**：XLSX 记录已抓取的卡片ID（视频ID），重复运行自动跳过。
- **限速与重试**：随机 UA + 请求间隔 + 指数退避，降低被限流概率。
- **粉丝数缓存**：同一作者的粉丝数只请求一次。

## 输出说明

- 输出为 `.xlsx`（Excel 原生格式），中文无需担心编码问题。
- 卡片ID（视频ID）单独作为一列写入，便于定位与去重。
- 采用"内存累积 + 定期落盘"策略：每 20 条或结束时保存，兼顾速度与崩溃时的数据保留。

## 免责声明

本项目仅用于学习与技术研究，请遵守目标网站的使用条款与当地法律法规，合理控制抓取频率。

