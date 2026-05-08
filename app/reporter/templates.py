REPORT_TEMPLATES = {
    "daily": """# 📋 日结报告 - {date}

## 项目：{project_name}

### 提交概览
- 总提交数：{commit_count}
- 涉及作者：{authors}
- 变更文件数：{file_count}

### 代码审核摘要
{review_summary}

### 主要问题
{issues}

### 日结总结
{summary}
""",
    "weekly": """# 📊 周结报告 - {week_range}

## 项目：{project_name}

### 本周数据
- 总提交数：{commit_count}
- 活跃作者：{authors}
- 代码审核次数：{review_count}

### 代码质量趋势
{quality_trend}

### 遗留问题
{pending_issues}

### 下周建议
{suggestions}
""",
    "monthly": """# 📈 月结报告 - {month}

## 项目：{project_name}

### 本月里程碑
{milestones}

### 数据统计
- 总提交数：{commit_count}
- 总代码审核数：{review_count}
- 活跃作者数：{author_count}

### 技术债务分析
{tech_debt}

### 下月规划建议
{next_month_plan}
""",
}
