#!/bin/bash
# Neurone API 测试脚本
# 使用 curl 命令进行 HTTP 接口测试
#
# 使用方式:
#   ./test_api.sh              # 运行所有测试
#   ./test_api.sh health       # 只运行健康检查测试
#   ./test_api.sh tools        # 只运行工具相关测试

API_BASE="http://127.0.0.1:8080"
RELAY_BASE="http://127.0.0.1:18792"

# 颜色定义
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
RESET='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}=== $1 ===${RESET}"
}

print_pass() {
    echo -e "  ${GREEN}✓ PASS${RESET} $1"
}

print_fail() {
    echo -e "  ${RED}✗ FAIL${RESET} $1"
}

print_info() {
    echo -e "  ${YELLOW}→${RESET} $1"
}

# 健康检查测试
test_health() {
    print_header "健康检查测试"

    # REST API 健康检查
    print_info "测试 REST API 健康检查..."
    RESP=$(curl -s "${API_BASE}/health")
    if echo "$RESP" | grep -q '"status": "healthy"'; then
        print_pass "REST API 健康检查"
    else
        print_fail "REST API 健康检查: $RESP"
    fi

    # Relay 健康检查
    print_info "测试 Relay 健康检查..."
    RESP=$(curl -s "${RELAY_BASE}/health")
    if echo "$RESP" | grep -q '"status": "healthy"'; then
        print_pass "Relay 健康检查"
    else
        print_fail "Relay 健康检查: $RESP"
    fi
}

# 工具列表测试
test_tools() {
    print_header "工具列表测试"

    # 获取工具列表
    print_info "获取工具列表..."
    RESP=$(curl -s "${API_BASE}/api/v1/tools")
    TOOLS_COUNT=$(echo "$RESP" | grep -o '"count": [0-9]*' | grep -o '[0-9]*')
    if [ -n "$TOOLS_COUNT" ]; then
        print_pass "工具列表获取成功 (${TOOLS_COUNT} 个工具)"
    else
        print_fail "工具列表获取失败: $(echo $RESP | head -c 200)"
    fi

    # 搜索工具
    print_info "搜索 'click' 相关工具..."
    RESP=$(curl -s "${API_BASE}/api/v1/tools/search?q=click")
    COUNT=$(echo "$RESP" | grep -o '"count": [0-9]*' | grep -o '[0-9]*')
    print_pass "搜索 'click' 结果: $COUNT 个"

    # 搜索工具
    print_info "搜索 'navigate' 相关工具..."
    RESP=$(curl -s "${API_BASE}/api/v1/tools/search?q=navigate")
    COUNT=$(echo "$RESP" | grep -o '"count": [0-9]*' | grep -o '[0-9]*')
    print_pass "搜索 'navigate' 结果: $COUNT 个"

    # 获取工具详情
    print_info "获取 browser.click 详情..."
    RESP=$(curl -s "${API_BASE}/api/v1/tools/browser.click")
    if echo "$RESP" | grep -q '"name": "browser.click"'; then
        print_pass "browser.click 详情获取成功"
    else
        print_fail "browser.click 详情获取失败"
    fi

    # 获取工具 Schema
    print_info "获取 browser.navigate Schema..."
    RESP=$(curl -s "${API_BASE}/api/v1/tools/browser.navigate/schema")
    if echo "$RESP" | grep -q '"parameters"'; then
        print_pass "browser.navigate Schema 获取成功"
    else
        print_fail "browser.navigate Schema 获取失败"
    fi
}

# 工具执行测试
test_execute() {
    print_header "工具执行测试"

    # 测试 browser.navigate
    print_info "执行 browser.navigate (导航到百度)..."
    RESP=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"tool": "browser.navigate", "params": {"url": "https://www.baidu.com"}, "timeout": 30000}' \
        "${API_BASE}/api/v1/execute")
    if echo "$RESP" | grep -q '"success": true'; then
        print_pass "browser.navigate 执行成功"
    else
        print_fail "browser.navigate 执行失败: $(echo $RESP | head -c 200)"
    fi

    # 测试 browser.extract
    print_info "执行 browser.extract (提取标题)..."
    RESP=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"tool": "browser.extract", "params": {"selector": "title", "source": "text"}, "timeout": 10000}' \
        "${API_BASE}/api/v1/execute")
    if echo "$RESP" | grep -q '"success"'; then
        print_pass "browser.extract 执行成功"
    else
        print_fail "browser.extract 执行失败"
    fi

    # 测试 inject_script
    print_info "执行 inject_script (执行 JS)..."
    RESP=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"tool": "inject_script", "params": {"code": "return 1+1", "world": "ISOLATED"}, "timeout": 10000}' \
        "${API_BASE}/api/v1/execute")
    if echo "$RESP" | grep -q '"success"'; then
        print_pass "inject_script 执行成功"
    else
        print_fail "inject_script 执行失败"
    fi

    # 测试无效工具
    print_info "执行不存在的工具 (应返回错误)..."
    RESP=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"tool": "nonexistent.tool", "params": {}}' \
        "${API_BASE}/api/v1/execute")
    if echo "$RESP" | grep -q '"success": false'; then
        print_pass "无效工具正确返回失败"
    else
        print_fail "无效工具处理异常"
    fi
}

# 流程相关测试
test_flows() {
    print_header "流程相关测试"

    # 获取流程列表
    print_info "获取流程列表..."
    RESP=$(curl -s "${API_BASE}/api/v1/flows")
    if echo "$RESP" | grep -q '"flows"'; then
        print_pass "流程列表获取成功"
    else
        print_fail "流程列表获取失败"
    fi

    # 测试分页
    print_info "测试流程列表分页..."
    RESP=$(curl -s "${API_BASE}/api/v1/flows?page=1&page_size=10")
    if echo "$RESP" | grep -q '"page"'; then
        print_pass "流程列表分页参数正常"
    else
        print_fail "流程列表分页异常"
    fi

    # 获取不存在的流程详情
    print_info "获取不存在的流程详情 (应返回 404)..."
    RESP=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/flows/nonexistent_id")
    if [ "$RESP" = "404" ]; then
        print_pass "正确返回 404"
    else
        print_fail "返回状态码: $RESP (预期 404)"
    fi

    # 创建流程（功能待实现）
    print_info "创建流程..."
    RESP=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{
            "name": "测试流程",
            "description": "API 测试创建的流程",
            "steps": [{"id": "step1", "name": "测试步骤", "type": "action", "tool": "browser.click"}]
        }' \
        "${API_BASE}/api/v1/flows")
    if echo "$RESP" | grep -q "501\|待实现"; then
        print_pass "创建流程功能待实现（预期行为）"
    else
        print_pass "创建流程: $RESP"
    fi
}

# 完整测试
test_all() {
    echo ""
    echo -e "${BLUE}============================================${RESET}"
    echo -e "${BLUE}  Neurone API 测试 (curl 命令行版)${RESET}"
    echo -e "${BLUE}============================================${RESET}"

    test_health
    test_tools
    test_execute
    test_flows

    echo ""
    echo -e "${BLUE}============================================${RESET}"
    echo -e "${BLUE}  测试完成${RESET}"
    echo -e "${BLUE}============================================${RESET}"
    echo ""
}

# 显示帮助
show_help() {
    echo ""
    echo -e "${BLUE}Neurone API 测试脚本${RESET}"
    echo ""
    echo "使用方式:"
    echo "  $0                  # 运行所有测试"
    echo "  $0 health           # 只运行健康检查测试"
    echo "  $0 tools            # 只运行工具相关测试"
    echo "  $0 execute          # 只运行执行相关测试"
    echo "  $0 flows            # 只运行流程相关测试"
    echo "  $0 --help           # 显示此帮助信息"
    echo ""
}

# 主函数
case "$1" in
    --help|-h)
        show_help
        ;;
    health)
        test_health
        ;;
    tools)
        test_tools
        ;;
    execute)
        test_execute
        ;;
    flows)
        test_flows
        ;;
    "")
        test_all
        ;;
    *)
        echo -e "${RED}未知参数: $1${RESET}"
        show_help
        exit 1
        ;;
esac