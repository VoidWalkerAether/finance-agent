#!/bin/bash

# Finance Agent Server 启动脚本
# 启动后端服务和前端静态文件服务

echo "🚀 Starting Finance Agent Server..."
echo ""

# 检查 Python 版本
python_version=$(python3 --version 2>&1)
echo "Python version: $python_version"

# 检查虚拟环境
# 优先检查是否有 conda 环境
if command -v conda &> /dev/null; then
    # 检查 conda 环境列表中是否有 ml_env
    if conda env list | grep -q "^ml_env"; then
        echo "✅ Found conda environment: ml_env"
        conda activate ml_env
    elif [ -d "ml_env" ]; then
        echo "✅ Found local ml_env directory"
        # 检测本地目录类型
        if [ -f "ml_env/pyvenv.cfg" ]; then
            echo "   🐍 Detected venv environment"
            if [ -f "ml_env/bin/activate" ]; then
                source ml_env/bin/activate
            else
                echo "   ⚠️  activate script not found, this appears to be a conda-based venv"
                echo "   Attempting to use conda environment instead..."
                conda activate ml_env
            fi
        else
            echo "   ⚠️  Unknown environment type in ml_env directory"
            echo "   Attempting to activate as venv..."
            if [ -f "ml_env/bin/activate" ]; then
                source ml_env/bin/activate
            else
                echo "   ❌ Error: Cannot activate ml_env"
                exit 1
            fi
        fi
    else
        echo "⚠️  ml_env environment not found. Creating one..."
        echo "   🐍 Creating conda environment..."
        conda create -n ml_env python=3.11 -y
        conda activate ml_env
        echo "📦 Installing dependencies..."
        pip install -r requirements.txt
    fi
else
    # 没有 conda，使用 venv
    if [ -d "ml_env" ]; then
        echo "✅ Found local ml_env directory"
        if [ -f "ml_env/bin/activate" ]; then
            source ml_env/bin/activate
        else
            echo "   ❌ Error: ml_env/bin/activate not found"
            echo "   Please recreate the virtual environment"
            exit 1
        fi
    else
        echo "⚠️  ml_env virtual environment not found. Creating one..."
        echo "   🐍 Creating venv environment..."
        python3 -m venv ml_env
        source ml_env/bin/activate
        echo "📦 Installing dependencies..."
        pip install -r requirements.txt
    fi
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
echo "============================================================"
echo "🚀 Starting Finance Agent Services"
echo "============================================================"

# PID 文件路径
BACKEND_PID_FILE=".backend.pid"
FRONTEND_PID_FILE=".frontend.pid"

# 清理旧的 PID 文件
rm -f $BACKEND_PID_FILE $FRONTEND_PID_FILE

# 启动前端静态文件服务器（后台运行）
echo "📡 Starting frontend server on http://localhost:8080"
python3 -m http.server 8080 > /dev/null 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > $FRONTEND_PID_FILE
echo "   ✅ Frontend PID: $FRONTEND_PID"

# 等待前端服务启动
sleep 1

# 启动后端服务（前台运行）
echo "🔧 Starting backend server on http://localhost:3000"
echo "   📄 Frontend: http://localhost:8080/demo.html"
echo "   📚 API Docs: http://localhost:3000/api/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo "Or run './stop_server.sh' to stop services"
echo "============================================================"
echo ""

# 启动后端服务并保存 PID
python3 server/server.py &
BACKEND_PID=$!
echo $BACKEND_PID > $BACKEND_PID_FILE

# 等待后端进程
wait $BACKEND_PID

# 后端进程结束后，清理前端服务
echo ""
echo "🛑 Backend stopped, cleaning up frontend service..."
if [ -f $FRONTEND_PID_FILE ]; then
    FRONTEND_PID=$(cat $FRONTEND_PID_FILE)
    kill $FRONTEND_PID 2>/dev/null
    rm -f $FRONTEND_PID_FILE
fi
rm -f $BACKEND_PID_FILE
