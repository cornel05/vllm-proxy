"""
Simulate many client IPs hitting the proxy.

Each simulated user picks a random IP from a pool and sends it as
X-Forwarded-For — which is exactly what the proxy's get_client_ip()
reads. This populates per-IP Prometheus metrics so you can verify the
Grafana dashboard works with many distinct IPs.

Target the FastAPI app directly (port 8000), NOT nginx (8081) — nginx
overwrites X-Forwarded-For with the real remote address.

Run:
    pip install locust
    locust -f locustfile.py --host http://localhost:8000

Then open http://localhost:8089 and start a swarm.
Or headless:
    locust -f locustfile.py --host http://localhost:8000 \
        --users 50 --spawn-rate 10 --run-time 2m --headless
"""

import random

from locust import HttpUser, task, between

# Pool of fake client IPs. Keep this bounded (e.g. 20-50) — Prometheus
# creates one time-series per unique IP, so thousands of IPs = high
# cardinality. A small pool is enough to verify the dashboard.
IP_POOL = [f"10.0.{a}.{b}" for a in range(1, 6) for b in range(1, 11)]  # 50 IPs

PROMPTS = [
    "What is 2 + 2?",
    "Name a color.",
    "Say hello.",
    "Tell me a one-line joke.",
    "What day comes after Monday?",
]


class ProxyUser(HttpUser):
    # Each simulated user waits 1-3s between requests
    wait_time = between(1, 3)

    def on_start(self):
        # Each user sticks to one IP for its lifetime (realistic)
        self.fake_ip = random.choice(IP_POOL)

    @task
    def chat(self):
        self.client.post(
            "/v1/chat/completions",
            json={
                "model": "phi",
                "messages": [{"role": "user", "content": random.choice(PROMPTS)}],
                "max_tokens": 32,
                "stream": False,
            },
            headers={"X-Forwarded-For": self.fake_ip},
            name="/v1/chat/completions",  # group all under one name in stats
        )