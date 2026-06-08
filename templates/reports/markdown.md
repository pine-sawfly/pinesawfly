# {{ title }}

{{ color_logo }}

作者：{{ author }}

单位：{{ unit }}

项目路径：{{ project_path }}

日期：{{ date }}

-------------------------------------------

## 执行摘要

{{ overview }}

## 审计发现

{{# findings }}
### Finding {{ finding_id }}

- **规则 ID**: {{ rule_id }}  **风险等级**: {{ risk_level }}
- **问题概述**: {{ issue_summary }}
- **漏洞位置**: {{ vulnerability_location }}
- **传递链路**: {{ data_flow }}

{{ highlighted_code }}

{{/ findings }}
