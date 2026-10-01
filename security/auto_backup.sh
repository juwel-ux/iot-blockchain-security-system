#!/bin/bash
# auto_backup.sh - Automatic Backup Script

# Configuration
BACKUP_DIR="/home/emdad/Desktop/iot_backups"
PROJECT_DIR="/home/emdad/Desktop/iot_blockchain_project"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

echo "========================================="
echo "📦 Starting IoT Blockchain Backup"
echo "   Time: $(date)"
echo "========================================="

# 1. Backup encrypted keys
echo "📌 Backing up IPFS keys..."
cp -r ~/.ipfs "$BACKUP_DIR/ipfs_backup_$TIMESTAMP" 2>/dev/null

# 2. Backup project files (excluding large files)
echo "📌 Backing up project files..."
rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    "$PROJECT_DIR/" "$BACKUP_DIR/project_backup_$TIMESTAMP/"

# 3. Backup MongoDB
echo "📌 Backing up MongoDB..."
mongodump --db iot_project_db --out "$BACKUP_DIR/mongodb_backup_$TIMESTAMP" 2>/dev/null

# 4. Backup IPFS pinned files list
echo "📌 Saving IPFS pinned files list..."
curl -s -X POST http://localhost:5001/api/v0/pin/ls > "$BACKUP_DIR/ipfs_pins_$TIMESTAMP.json"

# 5. Create backup info file
cat > "$BACKUP_DIR/backup_info_$TIMESTAMP.txt" << EOF
Backup created: $(date)
Project version: $(git -C $PROJECT_DIR rev-parse HEAD 2>/dev/null || echo "unknown")
IPFS node ID: $(ipfs id -f="<id>" 2>/dev/null || echo "unknown")
EOF

# 6. Remove old backups (older than RETENTION_DAYS)
echo "📌 Cleaning old backups..."
find "$BACKUP_DIR" -type d -name "*_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null

# 7. Compress backup
echo "📌 Compressing backup..."
tar -czf "$BACKUP_DIR/iot_backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" \
    project_backup_$TIMESTAMP ipfs_backup_$TIMESTAMP mongodb_backup_$TIMESTAMP 2>/dev/null

# 8. Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR/iot_backup_$TIMESTAMP.tar.gz" | cut -f1)

echo ""
echo "========================================="
echo "✅ BACKUP COMPLETE!"
echo "   Location: $BACKUP_DIR/iot_backup_$TIMESTAMP.tar.gz"
echo "   Size: $BACKUP_SIZE"
echo "========================================="

# Optional: Send notification (if you have a notification system)
# curl -X POST https://your-notification-server.com/backup-status \
#      -H "Content-Type: application/json" \
#      -d "{\"status\":\"success\",\"timestamp\":\"$TIMESTAMP\",\"size\":\"$BACKUP_SIZE\"}"
