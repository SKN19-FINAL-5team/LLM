#!/bin/bash
# SPLADE API 서버 연결 상태 확인 스크립트

API_URL="${SPLADE_API_URL:-http://localhost:8001}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"

echo "🔍 SPLADE API 서버 연결 모니터링 시작"
echo "   API URL: $API_URL"
echo "   체크 간격: ${CHECK_INTERVAL}초"
echo "   종료: Ctrl+C"
echo ""

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    if curl -s --max-time 5 "$API_URL/health" > /dev/null 2>&1; then
        echo "[$TIMESTAMP] ✅ 연결 정상"
    else
        echo "[$TIMESTAMP] ❌ 연결 실패"
        echo "   확인 사항:"
        echo "   1. SSH 터널이 실행 중인지 확인"
        echo "   2. RunPod API 서버가 실행 중인지 확인"
        echo "   3. 포트 포워딩 설정 확인 (8001 -> 8000)"
    fi
    
    sleep "$CHECK_INTERVAL"
done
