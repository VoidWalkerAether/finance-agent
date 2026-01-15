#!/bin/bash

# Finance Agent Server 启动脚本

echo "🚀 Starting Finance Agent Server..."
echo ""

# 检查 Python 版本
python_version=$(python3 --version 2>&1)
echo "Python version: $python_version"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 检查环境变量
if [ -f ".env" ]; then
    echo "✅ .env file found"
else
    echo "⚠️  .env file not found. Please create one with:"
    echo "   ANTHROPIC_AUTH_TOKEN=your_api_key_here"
    echo "   DATABASE_PATH=./data/finance.db"
fi

echo ""
echo "Starting server on port 3000..."
echo "Press Ctrl+C to stop"
echo ""

# 启动服务器
python3 server/server.py
