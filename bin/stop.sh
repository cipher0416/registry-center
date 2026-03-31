#!/bin/bash

# 简化版 - 仅通过端口停止服务
# 使用方法: ./stop.sh 8888 或 ./stop.sh -p 8888

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 解析参数
if [ "$1" = "-p" ]; then
    PORT=$2
else
    PORT=$1
fi

# 检查端口参数
if [ -z "$PORT" ]; then
    echo "使用方法: $0 -p <端口号>"
    echo "示例: $0 -p 8888"
    exit 1
fi

echo "正在停止端口 $PORT 上的服务..."

# 查找占用端口的进程
if command -v lsof &> /dev/null; then
    PID=$(lsof -ti:$PORT)
elif command -v netstat &> /dev/null; then
    PID=$(netstat -tlnp 2>/dev/null | grep ":$PORT " | awk '{print $7}' | cut -d'/' -f1)
else
    echo -e "${RED}错误: 未找到 lsof 或 netstat 命令${NC}"
    exit 1
fi

if [ -z "$PID" ]; then
    echo -e "${YELLOW}未找到占用端口 $PORT 的进程${NC}"
    exit 0
fi

echo "找到进程 PID: $PID"

# 停止进程
kill $PID 2>/dev/null
sleep 2

# 检查是否停止
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}进程未响应，强制停止...${NC}"
    kill -9 $PID 2>/dev/null
    sleep 1
fi

# 验证端口是否释放
if command -v lsof &> /dev/null; then
    if lsof -ti:$PORT > /dev/null 2>&1; then
        echo -e "${RED}端口 $PORT 仍被占用${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}服务已停止${NC}"