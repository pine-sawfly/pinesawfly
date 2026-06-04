# {{ title }}

{{ color_logo }}

作者：{{ author }}

单位：{{ unit }}

项目路径：{{ project_path }}

生成时间：{{ generated_at }}

-------------------------------------------

{{ overview }}

## 审计发现

{{# findings }}
### {{ finding_id }}

- **规则 ID**: {{ rule_id }}
- **风险等级**: {{ risk_level }}
- **问题概述**: {{ issue_summary }}

{{ highlighted_code }}

{{/ findings }}
