#!/bin/bash

# 设置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="main.py"  # Python脚本名称
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/$(date +%Y%m%d_%H%M%S).log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 输出开始执行的时间
echo "====================================" | tee -a "$LOG_FILE"
echo "Script started at: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "====================================" | tee -a "$LOG_FILE"

# 检查Python脚本是否存在
if [ ! -f "${SCRIPT_DIR}/${PYTHON_SCRIPT}" ]; then
    echo "Error: Python script ${PYTHON_SCRIPT} not found in ${SCRIPT_DIR}" | tee -a "$LOG_FILE"
    exit 1
fi

# 激活虚拟环境（如果有的话）
if [ -d "venv" ]; then
    echo "Activating virtual environment..." | tee -a "$LOG_FILE"
    source venv/bin/activate
fi

# 执行Python脚本并同时输出到控制台和日志文件
echo "Executing Python script: ${PYTHON_SCRIPT}" | tee -a "$LOG_FILE"
python3 "${SCRIPT_DIR}/${PYTHON_SCRIPT}" 2>&1 | tee -a "$LOG_FILE"

# 获取Python脚本的退出状态
exit_code=${PIPESTATUS[0]}

# 输出结束时间和状态
echo "====================================" | tee -a "$LOG_FILE"
echo "Script finished at: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "Exit code: $exit_code" | tee -a "$LOG_FILE"
echo "====================================" | tee -a "$LOG_FILE"

# 如果使用了虚拟环境，退出虚拟环境
if [ -d "venv" ]; then
    deactivate
fi

# 退出脚本，使用Python脚本的退出码
exit $exit_code