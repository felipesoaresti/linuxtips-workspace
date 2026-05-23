"""
Locust - stress test do TipsBank.
Simula usuarios criando contas e fazendo transferencias.

Execucao local:
    locust -f locustfile.py --host http://localhost:8082

Execucao em Kubernetes (como Job/Deployment, ver MANUAL-ALUNO semana 3):
    env LOCUST_HOST=http://api-transacoes.tipsbank.svc.cluster.local:8080 locust --headless -u 200 -r 20 -t 5m
"""
import os
import random
import uuid
from locust import HttpUser, task, between, events
from locust.clients import HttpSession

# Adicionado URL  api-contas para conseguir adicionar contas com sucesso
# URL do serviço de contas, pode ser configurada via variavel de ambiente para facilitar a execucao em diferentes ambientes (local, k8s, etc).
CONTAS_URL = os.getenv("CONTAS_URL", "http://localhost:8081")

CONTAS_CRIADAS: list[str] = []


class UsuarioBanco(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        """Cria uma conta por usuario para termos saldo disponivel."""
        self.contas_client = HttpSession(
            base_url=CONTAS_URL,
            request_event=self.environment.events.request,
            user=self,
        )
        documento = "".join(random.choices("0123456789", k=11))
        payload = {
            "titular": f"Aluno {uuid.uuid4().hex[:6]}",
            "documento": documento,
            "senha": "senha123",                   # adicionado campo senha porque e obrigatorio no serviço, sem ele dava erro HTTP 422
            "saldo_inicial": "100000000.00",
        }
        # foi necessario modificar pois dava erro de execução no locust devido nova versao do locust.
        # catch_respoonse=True deve ser usado dentro de um contexto com bloco with.
        # https://docs.locust.io/en/stable/writing-a-locustfile.html#validating-responses
        with self.contas_client.post(
            "/contas",
            json=payload,
            name="/contas (setup)",
            catch_response=True,
        ) as r:
            if r.status_code == 201:
                CONTAS_CRIADAS.append(r.json()["id"])
                r.success()
            else:
                r.failure(f"falha criando conta: {r.status_code}")

    @task(3)
    def transferir(self):
        if len(CONTAS_CRIADAS) < 2:
            return
        origem, destino = random.sample(CONTAS_CRIADAS, 2)
        valor = round(random.uniform(1, 50), 2)
        self.client.post(
            "/transferencias",
            json={"origem_id": origem, "destino_id": destino, "valor": str(valor)},
            name="/transferencias",
        )

    @task(1)
    def consultar_extrato(self):
        if not CONTAS_CRIADAS:
            return
        conta = random.choice(CONTAS_CRIADAS)
        self.client.get(f"/extrato/{conta}", name="/extrato/:id")


@events.test_stop.add_listener
def resumo(environment, **_):
    print(f"\nContas criadas durante o teste: {len(CONTAS_CRIADAS)}")
