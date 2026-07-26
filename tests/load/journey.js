import http from 'k6/http';
import crypto from 'k6/crypto';
import { check, sleep } from 'k6';

const baseUrl = __ENV.BASE_URL || 'http://localhost:5153';
const appSecret = __ENV.WHATSAPP_APP_SECRET || 'placeholder';
const runId = __ENV.RUN_ID || `k6-${Date.now()}`;
const phone = __ENV.E2E_PHONE_NUMBER || '5511999999999';

export const options = {
  vus: Number(__ENV.VUS || 5),
  duration: __ENV.DURATION || '20s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1500'],
    checks: ['rate>0.99'],
  },
};

function webhookPayload(messageId) {
  return {
    object: 'whatsapp_business_account',
    entry: [{
      id: 'k6-account',
      changes: [{
        field: 'messages',
        value: {
          messaging_product: 'whatsapp',
          metadata: {
            display_phone_number: '5511000000000',
            phone_number_id: 'k6-phone-number-id',
          },
          contacts: [{ profile: { name: 'K6' }, wa_id: phone }],
          messages: [{
            from: phone,
            id: messageId,
            timestamp: `${Math.floor(Date.now() / 1000)}`,
            type: 'text',
            text: { body: 'Quero renegociar minha dívida' },
          }],
        },
      }],
    }],
  };
}

export function setup() {
  const ready = http.get(`${baseUrl}/health/ready`);
  check(ready, { 'BFF is ready': (response) => response.status === 200 });
}

export default function () {
  const messageId = `wamid.k6-${runId}-${__VU}-${__ITER}-${Date.now()}`;
  const body = JSON.stringify(webhookPayload(messageId));
  const signature = crypto.hmac('sha256', appSecret, body, 'hex');
  const response = http.post(`${baseUrl}/webhooks/whatsapp`, body, {
    headers: {
      'Content-Type': 'application/json',
      'X-Hub-Signature-256': `sha256=${signature}`,
      'X-K6-Run-Id': runId,
    },
    tags: { journey: 'signed-whatsapp-webhook' },
  });
  check(response, {
    'webhook accepted': (result) => result.status === 200,
    'response is JSON': (result) => (result.headers['Content-Type'] || '').includes('application/json'),
  });
  sleep(0.05);
}
