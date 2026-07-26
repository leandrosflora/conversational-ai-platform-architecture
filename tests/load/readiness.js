import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = __ENV.BASE_URL || 'http://localhost:5153';
const targetPath = __ENV.TARGET_PATH || '/health/ready';

export const options = {
  scenarios: {
    readiness: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 5,
      maxVUs: 20,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const response = http.get(`${baseUrl}${targetPath}`, {
    tags: { endpoint: 'health-ready' },
    timeout: '5s',
  });
  check(response, {
    'readiness is 200': (r) => r.status === 200,
  });
  sleep(0.1);
}
