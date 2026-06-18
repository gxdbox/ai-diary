#!/bin/bash

# AI Diary 数据库备份脚本(含 OSS 上传)
# 用法: ./backup_database.sh
# 功能: 自动备份 SQLite 数据库和 ChromaDB 向量数据,并上传到阿里云 OSS

set -e  # 遇到错误立即退出

# ==================== 配置区域 ====================
# 可根据实际部署环境修改以下路径

BACKUP_DIR="/root/ai-diary/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="/root/ai-diary/ai_diary.db"
CHROMA_DIR="/root/ai-diary/chroma_data"
LOG_FILE="/root/ai-diary/logs/backup.log"
RETENTION_DAYS=7  # 保留备份的天数

# OSS 配置(从环境变量读取)
OSS_ACCESS_KEY_ID="${OSS_ACCESS_KEY_ID:-}"
OSS_ACCESS_KEY_SECRET="${OSS_ACCESS_KEY_SECRET:-}"
OSS_BACKUP_BUCKET_NAME="${OSS_BACKUP_BUCKET_NAME:-ai-diary-backups}"
OSS_ENDPOINT="${OSS_ENDPOINT:-oss-cn-hangzhou.aliyuncs.com}"
OSS_BACKUP_PATH="${OSS_BACKUP_PATH:-backups/}"

# ==================== 函数定义 ====================

log_message() {
    local message="[$(date)] $1"
    echo "$message" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    # 创建必要的目录
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log_message "=========================================="
    log_message "开始备份..."
    log_message "备份目录: $BACKUP_DIR"
    log_message "日期标记: $DATE"
}

backup_sqlite() {
    if [ -f "$DB_FILE" ]; then
        local backup_file="$BACKUP_DIR/ai_diary_${DATE}.db"
        cp "$DB_FILE" "$backup_file"
        
        # 验证备份文件
        if [ -f "$backup_file" ]; then
            local size=$(du -h "$backup_file" | cut -f1)
            log_message "✅ SQLite 数据库备份完成: ai_diary_${DATE}.db (大小: $size)"
        else
            log_message "❌ 错误: SQLite 备份文件创建失败"
            exit 1
        fi
    else
        log_message "❌ 错误: 数据库文件不存在 $DB_FILE"
        exit 1
    fi
}

backup_chromadb() {
    if [ -d "$CHROMA_DIR" ]; then
        local backup_file="$BACKUP_DIR/chroma_data_${DATE}.tar.gz"
        tar czf "$backup_file" -C /root/ai-diary chroma_data/
        
        # 验证备份文件
        if [ -f "$backup_file" ]; then
            local size=$(du -h "$backup_file" | cut -f1)
            log_message "✅ ChromaDB 数据备份完成: chroma_data_${DATE}.tar.gz (大小: $size)"
        else
            log_message "❌ 错误: ChromaDB 备份文件创建失败"
            exit 1
        fi
    else
        log_message "⚠️  警告: ChromaDB 目录不存在 $CHROMA_DIR"
        log_message "   跳过 ChromaDB 备份"
    fi
}

upload_to_oss() {
    # 检查是否配置了 OSS 凭据
    if [ -z "$OSS_ACCESS_KEY_ID" ] || [ -z "$OSS_ACCESS_KEY_SECRET" ]; then
        log_message "⚠️  警告: 未配置 OSS 凭据,跳过 OSS 上传"
        log_message "   如需启用 OSS 备份,请在 .env 文件中配置:"
        log_message "   OSS_ACCESS_KEY_ID、OSS_ACCESS_KEY_SECRET、OSS_BACKUP_BUCKET_NAME"
        return 0
    fi
    
    log_message "📤 开始上传到 OSS..."
    
    # 安装 ossutil(如果未安装)
    if ! command -v ossutil &> /dev/null; then
        log_message "   安装 ossutil..."
        curl -s https://gosspublic.alicdn.com/ossutil/install.sh | bash
        if [ $? -ne 0 ]; then
            log_message "❌ 错误: ossutil 安装失败"
            return 1
        fi
        log_message "   ✅ ossutil 安装完成"
    fi
    
    # 配置 ossutil
    log_message "   配置 ossutil..."
    ossutil config -e $OSS_ENDPOINT -i $OSS_ACCESS_KEY_ID -k $OSS_ACCESS_KEY_SECRET > /dev/null 2>&1
    
    # 上传数据库备份
    log_message "   上传数据库备份..."
    ossutil cp "$BACKUP_DIR/ai_diary_${DATE}.db" "oss://${OSS_BACKUP_BUCKET_NAME}/${OSS_BACKUP_PATH}database/" --recursive > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        log_message "   ✅ 数据库备份已上传到 OSS: ${OSS_BACKUP_PATH}database/ai_diary_${DATE}.db"
    else
        log_message "   ❌ 警告: 数据库备份上传失败"
    fi
    
    # 上传 ChromaDB 备份
    if [ -f "$BACKUP_DIR/chroma_data_${DATE}.tar.gz" ]; then
        log_message "   上传 ChromaDB 备份..."
        ossutil cp "$BACKUP_DIR/chroma_data_${DATE}.tar.gz" "oss://${OSS_BACKUP_BUCKET_NAME}/${OSS_BACKUP_PATH}chromadb/" --recursive > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            log_message "   ✅ ChromaDB 备份已上传到 OSS: ${OSS_BACKUP_PATH}chromadb/chroma_data_${DATE}.tar.gz"
        else
            log_message "   ❌ 警告: ChromaDB 备份上传失败"
        fi
    fi
    
    # 删除30天前的 OSS 备份(节省成本)
    log_message "   清理30天前的 OSS 备份..."
    local cutoff_date=$(date -d "30 days ago" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -v-30d +%Y-%m-%dT%H:%M:%S 2>/dev/null)
    if [ -n "$cutoff_date" ]; then
        ossutil rm "oss://${OSS_BACKUP_BUCKET_NAME}/${OSS_BACKUP_PATH}" -r -f --before-time "$cutoff_date" > /dev/null 2>&1
        log_message "   ✅ OSS 旧备份清理完成"
    else
        log_message "   ⚠️  警告: 无法计算日期,跳过 OSS 旧备份清理"
    fi
    
    log_message "✅ OSS 上传完成"
}

cleanup_old_backups() {
    log_message "🧹 清理 ${RETENTION_DAYS} 天前的旧备份..."
    
    local deleted_count=0
    
    # 删除旧的 SQLite 备份
    while IFS= read -r -d '' file; do
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
    done < <(find "$BACKUP_DIR" -name "ai_diary_*.db" -mtime +${RETENTION_DAYS} -print0 2>/dev/null || true)
    
    # 删除旧的 ChromaDB 备份
    while IFS= read -r -d '' file; do
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
    done < <(find "$BACKUP_DIR" -name "chroma_data_*.tar.gz" -mtime +${RETENTION_DAYS} -print0 2>/dev/null || true)
    
    if [ $deleted_count -gt 0 ]; then
        log_message "   已删除 $deleted_count 个旧备份文件"
    else
        log_message "   没有需要清理的旧备份"
    fi
}

show_summary() {
    log_message "=========================================="
    
    # 显示备份文件列表
    log_message "当前备份文件:"
    ls -lh "$BACKUP_DIR"/ai_diary_*.db 2>/dev/null | while read line; do
        log_message "  $(basename $(echo $line | awk '{print $NF}')) - $(echo $line | awk '{print $5}')"
    done
    
    ls -lh "$BACKUP_DIR"/chroma_data_*.tar.gz 2>/dev/null | while read line; do
        log_message "  $(basename $(echo $line | awk '{print $NF}')) - $(echo $line | awk '{print $5}')"
    done
    
    # 显示总大小
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    log_message "备份目录总大小: $BACKUP_SIZE"
    log_message "✅ 备份完成!"
    log_message ""
}

# ==================== 主流程 ====================

main() {
    check_prerequisites
    backup_sqlite
    backup_chromadb
    cleanup_old_backups
    upload_to_oss
    show_summary
}

# 执行主流程
main

# ==================== 使用说明 ====================
# 
# 手动测试备份:
#   cd /root/ai-diary
#   ./scripts/backup_database.sh
#   ls -lh backups/
#
# 查看备份日志:
#   tail -f /root/ai-diary/logs/backup.log
#
# 配置定时任务 (每天凌晨2点执行):
#   crontab -e
#   添加: 0 2 * * * /root/ai-diary/scripts/backup_database.sh
#
# 查看定时任务:
#   crontab -l
#
# 恢复数据库:
#   cp backups/ai_diary_YYYYMMDD_HHMMSS.db ai_diary.db
#   tar xzf backups/chroma_data_YYYYMMDD_HHMMSS.tar.gz -C /root/ai-diary/
