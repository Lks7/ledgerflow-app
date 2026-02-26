#!/bin/bash
set -e

echo "========================================="
echo "  LedgerFlow 一键部署"
echo "========================================="

# 检查 docker
if ! command -v docker &> /dev/null; then
    echo "未检测到 Docker，正在安装..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker 安装完成"
fi

# 检查 docker compose
if ! docker compose version &> /dev/null; then
    echo "错误：需要 Docker Compose V2，请升级 Docker"
    exit 1
fi

# 创建 .env（如果不存在）
if [ ! -f .env ]; then
    echo "生成 .env 配置文件..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50)
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
    cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${SERVER_IP},localhost
CSRF_TRUSTED_ORIGINS=http://${SERVER_IP}
DB_PATH=/app/db/db.sqlite3
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
EOF
    echo ".env 已生成，服务器 IP: ${SERVER_IP}"
    echo "如需修改请编辑 .env 文件"
fi

echo ""
echo "构建并启动容器..."
docker compose up -d --build

echo ""
echo "========================================="
echo "  部署完成！"
echo "  访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo 'your-server-ip')"
echo "========================================="
echo ""
echo "常用命令："
echo "  查看日志:   docker compose logs -f"
echo "  重启服务:   docker compose restart"
echo "  停止服务:   docker compose down"
echo "  更新部署:   git pull && docker compose up -d --build"
