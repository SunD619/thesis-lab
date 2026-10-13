# 接口联调记录

测试日期：2026-10-13（Asia/Shanghai）。在开发电脑上测试；尚未验证云部署网络与稳定性。

## 接入结论

- 扶摇鉴权成功；行情快照、利润表、现金流量表、资产负债表和财务指标均返回 HTTP 200、业务 code=0。
- 测试标的 600519.SH。三张报表均实际返回 2023、2024、2025 三个年度；指标测试 report=2025-4。数据仅验证接口返回和局部一致性，尚未逐字段对照公司原始年报。
- 腾讯云 TokenHub 鉴权成功；模型列表包含 hy3，状态 online。
- Hy3 两次非流式 JSON 调用及一次流式调用成功；本轮均使用 reasoning_effort=none，不代表深度思考模式评估。
- iFinD 暂未提供密钥，未测试。

## 本次耗时与用量

| 测试 | 结果 | 本次耗时 |
|---|---|---|
| 扶摇行情快照 | 成功 | 186 ms |
| 扶摇利润表 | 成功，3 个年度 | 154 ms |
| 扶摇现金流量表 | 成功，3 个年度 | 61 ms |
| 扶摇资产负债表 | 成功，3 个年度 | 65 ms |
| 扶摇财务指标 | 成功，含真实 null | 62 ms |
| TokenHub 模型列表 | 成功，hy3 online | 877 ms |
| Hy3 初版证据分析 | JSON 可解析，存在归因问题 | 2779 ms |
| Hy3 修订提示词 | 结构与引用编号检查通过，归因措辞仍需约束 | 3635 ms |
| Hy3 真实数据流式分析 | 成功，引用 E1/E2，边界正确 | 总计 1938 ms，首个内容约 1008 ms |
| 扶摇缺少报告期 | 正确返回业务错误 code=1001，HTTP 仍为 200 | 268 ms |

三次模型调用共 971 tokens（接口 usage 汇总）；未核验账户免费额度余额与账单。耗时为单次观测，不是性能保证。

## 对产品实现的影响

1. 不能只检查 HTTP 状态：扶摇业务错误通过响应 code 判断。本次漏传 report 得到 HTTP 200 / code=1001。
2. 财务指标与文档有差异：实际出现 calculate_operating_income_yoy_growth_ratio、calculate_operating_profit_yoy_growth_ratio、calculate_parent_holder_net_profit_yoy_growth_ratio。需要字段映射和缺字段检测，不能依靠文档名称硬编码后把空值当零。
3. 计算交给程序：本次程序算出的 2025 营收同比 -1.2060035021% 与接口指标 -1.206004% 在 0.0001 个百分点内一致。
4. 披露时间有待核验：不同年度、不同报表可能返回相同或较晚的 report_date_ms；不能未经原公告核实就作为首次披露日。
5. 初版模型把净利润增长当成主营改善的支持证据。修订后保留重要反证和缺失项，但仍有把扣非利润变化过度映射到主营业务盈利的倾向。接口可用不等于金融归因可靠。正式链路须限制归因结论，对缺少分部/非经常性损益明细的情况提示无法完整验证，并评估更严格提示词或推理模式。
6. 简单事实验证已跑通：真实财务字段 → 程序计算同比 → 模型引用证据说明收入增长 → 明确不能推出主营利润改善。E2 是由 E1 计算得到的派生证据，不是第二个独立数据来源。
7. JSON 输出仅为基础结构检查；正式服务仍需服务端 schema 校验、引用存在性校验、超时和失败处理。

## 配置与证据保存

- 凭证保存在本地 .env，已写入 .gitignore；.env.example 只有字段名，无密钥。
- 本地原始接口响应保存在 .local/integration-responses.json，整个 .local 目录忽略提交；未公开发布数据。
- 尚未部署网站，未调用 iFinD，未验证公告原文检索。

## 官方接口文档

- https://fuyao.aicubes.cn/docs/quickstart/
- https://fuyao.aicubes.cn/docs/api-reference/financials/
- https://fuyao.aicubes.cn/docs/api-reference/financial-indicators/
- https://cloud.tencent.com/document/product/1823/130078
- https://cloud.tencent.com/document/product/1823/131208
