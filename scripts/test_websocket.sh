#!/bin/bash

# WebSocket 多轮对话一键测试脚本
# 用法: ./scripts/test_websocket.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}🧪 Finance Agent - WebSocket 多轮对话测试${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

# 检查依赖
echo -e "${YELLOW}[1/4] 检查依赖...${NC}"

if ! python -c "import websockets" 2>/dev/null; then
    echo -e "${RED}❌ 缺少依赖: websockets${NC}"
    echo ""
    echo -e "${YELLOW}正在安装...${NC}"
    pip install websockets
    echo -e "${GREEN}✅ 安装完成${NC}"
else
    echo -e "${GREEN}✅ websockets 已安装${NC}"
fi

echo ""

# 检查环境变量
echo -e "${YELLOW}[2/4] 检查环境变量...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ 未找到 .env 文件${NC}"
    echo ""
    echo "请执行以下步骤:"
    echo "  1. cp .env.example .env"
    echo "  2. 编辑 .env 文件，设置 ANTHROPIC_API_KEY"
    echo "  3. 重新运行此脚本"
    exit 1
fi

# 检查 API Key
API_KEY=$(grep -E "^ANTHROPIC_API_KEY=" .env | cut -d '=' -f2)
if [ -z "$API_KEY" ]; then
    API_KEY=$(grep -E "^ANTHROPIC_AUTH_TOKEN=" .env | cut -d '=' -f2)
fi

if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ 未配置 API Key${NC}"
    echo ""
    echo "请在 .env 文件中设置:"
    echo "  ANTHROPIC_API_KEY=sk-ant-api03-xxxxx"
    exit 1
else
    echo -e "${GREEN}✅ API Key 已配置${NC}"
fi

echo ""

# 检查服务器是否运行
echo -e "${YELLOW}[3/4] 检查服务器状态...${NC}"

if curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务器正在运行 (http://localhost:3000)${NC}"
else
    echo -e "${RED}❌ 服务器未运行${NC}"
    echo ""
    echo -e "${YELLOW}提示: 请先启动服务器${NC}"
    echo ""
    echo "方式 1: 新终端运行"
    echo "  python server/server.py"
    echo ""
    echo "方式 2: 后台运行"
    echo "  nohup python server/server.py > server.log 2>&1 &"
    echo ""
    read -p "是否现在启动服务器? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}正在启动服务器...${NC}"
        nohup python server/server.py > server.log 2>&1 &
        SERVER_PID=$!
        echo -e "${GREEN}✅ 服务器已在后台启动 (PID: $SERVER_PID)${NC}"
        echo -e "${BLUE}   日志文件: server.log${NC}"
        
        # 等待服务器启动
        echo -e "${YELLOW}等待服务器就绪...${NC}"
        for i in {1..10}; do
            if curl -s http://localhost:3000/health > /dev/null 2>&1; then
                echo -e "${GREEN}✅ 服务器已就绪${NC}"
                break
            fi
            sleep 1
            echo -n "."
        done
        echo ""
    else
        echo ""
        echo "请手动启动服务器后再运行此脚本"
        exit 1
    fi
fi

echo ""

# 运行测试
echo -e "${YELLOW}[4/4] 启动 WebSocket 测试...${NC}"
echo ""
echo -e "${BLUE}=====================================================================${NC}"
echo ""

python scripts/test_websocket_chat.py

echo ""
echo -e "${BLUE}=====================================================================${NC}"
echo -e "${GREEN}✅ 测试完成${NC}"
echo -e "${BLUE}=====================================================================${NC}"
