"""
Chat application configuration
"""

import os

# WebSocket settings
WEBSOCKET_URL = "ws://localhost:8000"  # 开发环境
# WEBSOCKET_URL = "wss://your-domain.com"  # 生产环境

# 允许的WebSocket来源
ALLOWED_WEBSOCKET_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3003",
    "http://localhost:3006",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3003",
    "http://127.0.0.1:3006",
] 