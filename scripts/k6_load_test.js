import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

// Custom Metrics for detailed reporting
const dbTrend = new Trend('db_duration');      // DB 응답 속도 추적
const blockedCount = new Counter('blocked_reqs'); // 차단된 요청 수 (429)
const dbSuccessCount = new Counter('db_success_reqs'); // DB 연결 성공 수 (200)

export const options = {
    stages: [
        { duration: '10s', target: 50 },  // Ramp-up
        { duration: '30s', target: 50 },  // Steady
        { duration: '10s', target: 0 },   // Ramp-down
    ],
    thresholds: {
        // Rate Limit 테스트는 429가 정상이므로 에러율 제한 끔
        http_req_duration: ['p(95)<2000'], // 전체 95% 2초 이내
    },
};

export default function () {
    const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

    // --------------------------------------------------------
    // 1. Rate Limiting Test (Root Endpoint)
    // --------------------------------------------------------
    const resRoot = http.get(`${BASE_URL}/`, { tags: { type: 'rate_limit' } });

    check(resRoot, {
        'Rate Limit Worked (429)': (r) => r.status === 429,
        'Normal Resp (200)': (r) => r.status === 200,
    });

    if (resRoot.status === 429) {
        blockedCount.add(1);
    }

    // --------------------------------------------------------
    // 2. Connection Pooling Test (DB Health Check)
    // --------------------------------------------------------
    const resDb = http.get(`${BASE_URL}/health`, { tags: { type: 'db_pool' } });

    check(resDb, {
        'DB Connection Alive (200)': (r) => r.status === 200,
    });

    if (resDb.status === 200) {
        dbSuccessCount.add(1);
        dbTrend.add(resDb.timings.duration);
    }

    sleep(1);
}

// --------------------------------------------------------
// Custom Korean Summary Report
// --------------------------------------------------------
export function handleSummary(data) {
    // Safe access to metrics with fallbacks
    const getMetric = (name, type = 'count') => {
        if (!data.metrics[name]) return 0;
        return type === 'count'
            ? data.metrics[name].values.count || data.metrics[name].values.rate || 0
            : data.metrics[name].values[type] || 0;
    };

    const totalReqs = data.metrics.http_reqs ? data.metrics.http_reqs.values.count : 0;
    const blocked = getMetric('blocked_reqs', 'count');
    const dbSuccess = getMetric('db_success_reqs', 'count');
    const dbAvg = getMetric('db_duration', 'avg').toFixed(2);
    const dbP95 = getMetric('db_duration', 'p(95)').toFixed(2);

    // Calculate percentages
    // Note: totalReqs includes both endpoints. Rough estimates below.

    return {
        'stdout': `
===============================================================================
                  🚀 LOGISFLOW PERFORMANCE TEST REPORT 🚀
===============================================================================

📊 [전체 요약]
   - 총 요청 수 (Total Requests): ${totalReqs}
   - 테스트 시간 (Duration): 50s (Target: 50 VUs)

🛡️ [TEST 1: Rate Limiting (Protection)]
   - 목표: 과도한 트래픽 차단
   - 🚫 차단된 요청 (429 Too Many Requests): ${blocked} 건
   - ✅ 설명: ${blocked > 0 ? "Rate Limiter가 정상 작동하여 공격을 방어했습니다." : "Rate Limit가 작동하지 않았습니다."}

🔌 [TEST 2: Connection Pooling (Stability)]
   - 목표: 부하 속에서도 DB 연결 유지 (pgBouncer)
   - ✅ DB 연결 성공 (200 OK): ${dbSuccess} 건
   - ⏱️ DB 응답 속도 (Latency):
       * 평균 (Avg): ${dbAvg} ms
       * 95% (P95): ${dbP95} ms
   - ✅ 설명: ${dbP95 < 100 ? "매우 안정적 (Pooling 효과 확실)" : "지연 발생 (튜닝 필요)"}

===============================================================================
`
    };
}
