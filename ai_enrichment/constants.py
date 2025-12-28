"""
AI補完バッチの定数定義
"""
# 1バッチあたりの処理件数（25件 = 安全圏）
AI_ENRICH_BATCH_SIZE = 25

# API呼び出し間隔（秒）: 秒間2req制御のため0.5秒
AI_ENRICH_API_DELAY_SECONDS = 0.5
