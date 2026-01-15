#!/bin/bash

# Finance Agent Server 停止脚本
# 停止后端服务和前端静态文件服务

echo "🛑 Stopping Finance Agent Services..."
echo ""

# PID 文件路径
BACKEND_PID_FILE=".backend.pid"
FRONTEND_PID_FILE=".frontend.pid"

# 停止后端服务
if [ -f $BACKEND_PID_FILE ]; then
    BACKEND_PID=$(cat $BACKEND_PID_FILE)
    echo "🔧 Stopping backend server (PID: $BACKEND_PID)..."
    
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null
        sleep 1
        
        # 如果进程还在运行，强制杀死
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo "   ⚠️  Force killing backend..."
            kill -9 $BACKEND_PID 2>/dev/null
        fi
        
        echo "   ✅ Backend stopped"
    else
        echo "   ℹ️  Backend process not running"
    fi
    
    rm -f $BACKEND_PID_FILE
else
    echo "⚠️  Backend PID file not found, searching by process name..."
    
    # 查找并杀死 server.py 进程
    BACKEND_PIDS=$(pgrep -f "python3 server/server.py")
    if [ -n "$BACKEND_PIDS" ]; then
        echo "   Found backend process(es): $BACKEND_PIDS"
        for pid in $BACKEND_PIDS; do
            kill $pid 2>/dev/null
            echo "   ✅ Stopped backend PID: $pid"
        done
    else
        echo "   ℹ️  No backend process found"
    fi
fi

# 停止前端服务
if [ -f $FRONTEND_PID_FILE ]; then
    FRONTEND_PID=$(cat $FRONTEND_PID_FILE)
    echo "📡 Stopping frontend server (PID: $FRONTEND_PID)..."
    
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID 2>/dev/null
        sleep 1
        
        # 如果进程还在运行，强制杀死
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            echo "   ⚠️  Force killing frontend..."
            kill -9 $FRONTEND_PID 2>/dev/null
        fi
        
        echo "   ✅ Frontend stopped"
    else
        echo "   ℹ️  Frontend process not running"
    fi
    
    rm -f $FRONTEND_PID_FILE
else
    echo "⚠️  Frontend PID file not found, searching by process name..."
    
    # 查找并杀死 http.server 进程（端口 8080）
    FRONTEND_PIDS=$(lsof -ti:8080 2>/dev/null)
    if [ -n "$FRONTEND_PIDS" ]; then
        echo "   Found frontend process(es) on port 8080: $FRONTEND_PIDS"
        for pid in $FRONTEND_PIDS; do
            kill $pid 2>/dev/null
            echo "   ✅ Stopped frontend PID: $pid"
        done
    else
        echo "   ℹ️  No frontend process found on port 8080"
    fi
fi

echo ""
echo "✅ All services stopped"
