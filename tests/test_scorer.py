"""三维判分单元测试（PROJECT.md §8.5 / PLAN D7）

至少 8 个 case：
1. 完全正确
2. 工具对、顺序错
3. 顺序对、参数错
4. 工具集合包含多余项
5. 工具集合缺项
6. 重复工具刷分（验证 matched_expected_idx 生效）
7. 对抗样例（expected 空 + predicted 空）→ 100
8. 对抗样例（expected 空 + predicted 非空）→ 0
TODO: D7 编写
"""
