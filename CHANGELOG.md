# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Puppeteer 混合模式支持（开发中）

### Changed
- 无障碍树获取支持真实树（通过 Puppeteer CDP）

---

## [2.0.1] - 2025-02-27

### Added
- 无障碍树（A11yTree）工具支持

### Fixed
- A11yTreeTool 参数处理并添加自动重连逻辑
- site_tab_map 按密钥初始化逻辑
- 小红书笔记列表获取 - note_id 和 url 提取
- 优化 site_tab_map 初始化逻辑，支持按密钥初始化
- all_urls 授权时的网站撤销/授权逻辑

---

## [2.0.0] - 2025-02-XX

### Added
- 完整的浏览器自动化工具集
- 多插件密钥系统
- WebSocket Relay 服务器
- FastAPI REST 接口

### Changed
- 从 v1 迁移到 v2 架构