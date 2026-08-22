# Helper / Macro（辅助函数 / 宏）规范

## 目标

把“已经成功重复的只读动作”从模型逐步规划变成可验证的复用单元。

## 两层复用

### Static Helper（静态辅助函数）

代码中明确维护的稳定函数：

```text
observe_once
scan_visible_cards
open_search_verified
search_account_verified
open_post_from_card
return_to_grid_verified
read_visible_metrics
```

### Learned Macro（学习宏）

运行中发现同一高层动作序列成功重复 >= 3 次后，保存声明式动作模板。

宏不是动态 Python 源码，不允许自动改写核心文件。

## 宏定义

```json
{
  "name": "xhs_open_post_from_grid",
  "platform": "xhs",
  "precondition": "profile_grid",
  "steps": [
    {"action": "scan_visible_cards"},
    {"action": "tap_card", "arg": "$card_key"},
    {"action": "wait_stable"},
    {"action": "verify_page", "arg": "post_detail"}
  ],
  "postcondition": "post_detail",
  "success_count": 8,
  "failure_count": 0,
  "status": "active"
}
```

## 自动失效

遇到：

- 连续失败 2 次
- 页面类型不匹配
- 关键锚点缺失
- 窗口尺寸改变导致定位失效

则：

```text
status = stale
→ 普通规划接管
→ 后续重新学习
```

## 安全边界

只有只读动作进入自动学习白名单。

永不自动学习/执行：

```text
like
favorite
follow
comment
reply
dm
publish
purchase
```
