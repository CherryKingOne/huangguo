"""黄果短剧爬虫包。

模块划分:
    config   : 全局配置(站点、频道、请求头、路径等)
    models   : 数据模型与 CSV 字段定义
    client   : HTTP 客户端(重试/限速/随机UA)
    parser   : 列表页与详情页解析
    storage  : CSV 增量落盘
    crawler  : 任务编排(频道分页 -> 详情 -> 作者粉丝数 -> CSV)
"""
