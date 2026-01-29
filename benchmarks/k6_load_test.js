import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '10s', target: 50 },  // 10초 동안 사용자 50명으로 증가 (Ramp-up)
    { duration: '30s', target: 50 },  // 30초 동안 유지 (Steady)
    { duration: '10s', target: 0 },   // 10초 동안 감소 (Ramp-down)
  ],
  thresholds: {
    errors: ['rate<0.1'], // 에러율 10% 미만 목표 (Rate Limit 테스트 시에는 무시 가능)
    http_req_duration: ['p(95)<500'], // 95%의 요청이 500ms 이내 처리
  },
};

export default function () {
  const BASE_URL = 'http://localhost:8000';

  // 1. Root Endpoint (Rate Limit Test)
  const resRoot = http.get(`${BASE_URL}/`);
  
  check(resRoot, {
    'status is 200': (r) => r.status === 200,
    'rate limited (429)': (r) => r.status === 429,
  });

  if (resRoot.status === 429) {
    errorRate.add(1); // 429도 에러로 집계하여 Rate Limit 발동 확인
  }

  // 2. Database Endpoint (Connection Pooling Test)
  // Health check endpoint usually hits DB if configured, but we'll use a lightweight one.
  // Assuming /health checks DB or a simple query.
  // If not, we can hit the API root primarily for Rate Limit.
  
  sleep(1);
}
