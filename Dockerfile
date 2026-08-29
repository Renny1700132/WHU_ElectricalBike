# 使用官方轻量级 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 为了安装一些底层 C++ 库（如 OpenCV 需要的 libgl），先更新系统包
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目的所有代码到容器中
COPY . .

# 暴露 Hugging Face 要求的 7860 端口
EXPOSE 7860

# 启动命令（假设你的入口文件叫 run.py）
CMD ["python", "run.py"]