---
tags: [tipsbank, evidencias, dk8s]
created: 2026-04-24
status: em-andamento
---

# TipsBank — Evidências de Conclusão

---

## Semana 1 — Fundações

### Etapa 1.1 — Entender a aplicação localmente

**Data de conclusão:** 2026-04-24

#### Teste 1 — Listar contas seed (sem `senha_hash`)

```bash
# health check
curl http://localhost:8081/health/live   # api-contas
curl http://localhost:8082/health/live   # api-transacoes
curl http://localhost:8083/health/live   # auditoria
curl http://localhost:8080/healthz       # frontend nginx

# listar contas (senha_hash não é exposto)
curl http://localhost:8081/contas | jq

```

**Output:**

```
❯ curl http://localhost:8081/health/live
{"status":"ok"}%

❯ curl http://localhost:8082/health/live
{"status":"ok","version":"v1"}%

❯ curl http://localhost:8083/health/live
{"status":"ok"}%

❯ curl http://localhost:8080/healthz
ok

curl http://localhost:8081/contas | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   352  100   352    0     0  62026      0 --:--:-- --:--:-- --:--:-- 70400
[
  {
    "id": "11111111-1111-1111-1111-111111111111",
    "titular": "Jeferson Fernando",
    "documento": "12345678901",
    "saldo": "10000.00"
  },
  {
    "id": "22222222-2222-2222-2222-222222222222",
    "titular": "LinuxTips SA",
    "documento": "98765432100",
    "saldo": "500.00"
  },
  {
    "id": "2287b4f5-136c-4afe-a173-56e5ee741b3e",
    "titular": "Felipe Soares",
    "documento": "00987654321",
    "saldo": "1000.00"
  }
]

```

---

#### Teste 2 — Retorna senaha autenticada 0u 401

```bash
curl -X POST http://localhost:8081/login \
  -H 'content-type: application/json' \
  -d '{"documento":"12345678901","senha":"giropops"}' | jq
```

**Output:**

```
❯ curl -X POST http://localhost:8081/login \
  -H 'content-type: application/json' \
  -d '{"documento":"12345678901","senha":"giropops"}' | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   166  100   120  100    46   2185    837 --:--:-- --:--:-- --:--:--  3018
{
  "id": "11111111-1111-1111-1111-111111111111",
  "titular": "Jeferson Fernando",
  "documento": "12345678901",
  "saldo": "10000.00"
}

```
#### Evento gravado a auditoria

```
curl -X POST http://localhost:8081/login -H 'content-type: application/json' -d '{"documento":"12345678901","senha":"senha-errada-teste"}' | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    90  100    34  100    56    621   1024 --:--:-- --:--:-- --:--:--  1666
{
  "detail": "credenciais invalidas"
}

```

#### Teste 3 - Criar conta Nova

```bash
curl -X POST http://localhost:8081/contas \
  -H 'content-type: application/json' \
  -d '{
    "titular":"Descomplicador",
    "documento":"11122233344",
    "senha":"minhaSenha123",
    "saldo_inicial":"1000.00"
  }' | jq

  ```

**Output:**

```
curl -X POST http://localhost:8081/contas \
  -H 'content-type: application/json' \
  -d '{
    "titular":"Descomplicador",
    "documento":"11122233344",
    "senha":"minhaSenha123",
    "saldo_inicial":"1000.00"
  }' | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   243  100   116  100   127   1888   2068 --:--:-- --:--:-- --:--:--  3983
{
  "id": "196b2685-a669-47d2-b0e5-ff0678251312",
  "titular": "Descomplicador",
  "documento": "11122233344",
  "saldo": "1000.00"
}
```

#### Teste 3 — Transferência entre contas

```bash

curl -X POST http://localhost:8082/transferencias \
  -H 'content-type: application/json' \
  -d '{
    "origem_id":"11111111-1111-1111-1111-111111111111",
    "destino_id":"22222222-2222-2222-2222-222222222222",
    "valor":"100.00"
  }' | jq

  ```

**Output:**

```
❯ curl -X POST http://localhost:8082/transferencias \
  -H 'content-type: application/json' \
  -d '{
    "origem_id":"11111111-1111-1111-1111-111111111111",
    "destino_id":"22222222-2222-2222-2222-222222222222",
    "valor":"100.00"
  }' | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   325  100   186  100   139   1407   1052 --:--:-- --:--:-- --:--:--  2462
{
  "id": "3028e068-86cb-43b1-a5b4-5a954b74c161",
  "origem_id": "11111111-1111-1111-1111-111111111111",
  "destino_id": "22222222-2222-2222-2222-222222222222",
  "valor": "100.00",
  "status": "concluida"
}
```

---

#### Teste 4 — Evento gravado na auditoria (arquivo JSONL)

```bash
curl http://localhost:8083/eventos | jq

```

**Output:**

```
curl http://localhost:8083/eventos | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   311  100   311    0     0  87753      0 --:--:-- --:--:-- --:--:--  101k
[
  {
    "id": "f508fb39-6add-4ecd-8ac6-53e92c61d69e",
    "recebido_em": "2026-04-24T18:14:44.018740+00:00",
    "tipo": "transferencia",
    "transacao_id": "3028e068-86cb-43b1-a5b4-5a954b74c161",
    "origem_id": "11111111-1111-1111-1111-111111111111",
    "destino_id": "22222222-2222-2222-2222-222222222222",
    "valor": "100.00",
    "versao_app": "v1"
  }
]

```

#### Screenshots

![](<imagens/Captura de tela 2026-04-24 152744.png>)
*Dashboard local — app rodando com docker-compose*

![](<imagens/Captura de tela 2026-04-24 153243.png>)
*Todos os containers up (api-contas, api-transacoes, auditoria, web)*

![](<imagens/Captura de tela 2026-04-24 173234.png>)
*Transferência de R\$ 100,00 entre contas*

![](<imagens/Captura de tela 2026-04-24 173258.png>)
*Auditoria — evento de transferência registrado*

---

### Etapa 1.2 — Build Distroless + Trivy + Cosign

**Data de conclusão:** 2026-04-25

#### Justificativa: por que Chainguard/Distroless reduz vulnerabilidades

Nesta etapa eu foquei em reduzir a superfície de ataque das imagens. A ideia foi deixar dentro do container só o necessário para a aplicação rodar: runtime Python, dependências da aplicação e nada de ferramentas extras do sistema.

As imagens Chainguard/Distroless, baseadas em Wolfi, ajudam nisso porque não trazem shell, package manager nem utilitários comuns de troubleshooting. Na prática, se alguém conseguir entrar no container, o ambiente já é bem mais limitado: não tem `sh`, não tem `apt`, não tem `apk` e o processo roda com usuário nonroot. Isso não resolve segurança sozinho, mas diminui bastante o impacto de uma exploração.

No caso da `web`, usei `nginxinc/nginx-unprivileged:1.29-alpine-slim`, que também é uma imagem mais enxuta e roda como usuário 101, sem depender de root para servir o frontend.


#### Usuário nonroot nas imagens ####

```
docker inspect felipestaypuff/tipsbank-auditoria:v1.0.0
Found existing alias for "docker". You should use: "d"
[
    {
        "Id": "sha256:37a633a73c433514a171172eeaacc8278e2efd28e8d7ba000891f3579ca5ef51",
        "RepoTags": [
            "felipestaypuff/tipsbank-auditoria:v1.0.0",
            "tipsbank/auditoria:dev"
        ],
        "RepoDigests": [
            "felipestaypuff/tipsbank-auditoria@sha256:37a633a73c433514a171172eeaacc8278e2efd28e8d7ba000891f3579ca5ef51",
            "tipsbank/auditoria@sha256:37a633a73c433514a171172eeaacc8278e2efd28e8d7ba000891f3579ca5ef51"
        ],
        "Comment": "buildkit.dockerfile.v0",
        "Created": "2026-04-25T13:03:31.211109525Z",
        "Author": "github.com/chainguard-dev/apko",
        "Config": {
            "User": "65532",
            "ExposedPorts": {
                "8080/tcp": {}
            },

docker inspect felipestaypuff/tipsbank-api-contas:v1.0.0
Found existing alias for "docker". You should use: "d"
[
    {
        "Id": "sha256:05c5f3b2c81d39a45bab14705176337f3c303375707ed060f58b98060b4fe18c",
        "RepoTags": [
            "felipestaypuff/tipsbank-api-contas:v1.0.0",
            "felipestaypuff/tipsbank/api-contas:v1.0.0",
            "tipsbank/api-contas:dev"
        ],
        "RepoDigests": [
            "felipestaypuff/tipsbank-api-contas@sha256:05c5f3b2c81d39a45bab14705176337f3c303375707ed060f58b98060b4fe18c",
            "felipestaypuff/tipsbank/api-contas@sha256:05c5f3b2c81d39a45bab14705176337f3c303375707ed060f58b98060b4fe18c",
            "tipsbank/api-contas@sha256:05c5f3b2c81d39a45bab14705176337f3c303375707ed060f58b98060b4fe18c"
        ],
        "Comment": "buildkit.dockerfile.v0",
        "Created": "2026-04-25T12:40:39.250071789Z",
        "Author": "github.com/chainguard-dev/apko",
        "Config": {
            "User": "65532",
            "ExposedPorts": {
                "8080/tcp": {}

docker inspect felipestaypuff/tipsbank-api-transacoes:v1.0.0
Found existing alias for "docker". You should use: "d"
[
    {
        "Id": "sha256:4fefcd94fdadc031bb09080b161daea36b9d198a1b81577e3d53f9603249a66e",
        "RepoTags": [
            "felipestaypuff/tipsbank-api-transacoes:v1.0.0",
            "tipsbank/api-transacoes:dev"
        ],
        "RepoDigests": [
            "felipestaypuff/tipsbank-api-transacoes@sha256:4fefcd94fdadc031bb09080b161daea36b9d198a1b81577e3d53f9603249a66e",
            "tipsbank/api-transacoes@sha256:4fefcd94fdadc031bb09080b161daea36b9d198a1b81577e3d53f9603249a66e"
        ],
        "Comment": "buildkit.dockerfile.v0",
        "Created": "2026-04-25T12:52:43.470412819Z",
        "Author": "github.com/chainguard-dev/apko",
        "Config": {
            "User": "65532",
            "ExposedPorts": {
                "8080/tcp": {}

docker inspect felipestaypuff/tipsbank-web:v1.0.0
Found existing alias for "docker". You should use: "d"
[
    {
        "Id": "sha256:2830b4c4bdbd751b17d24eeaf4bb6f294dc31131e6e4849e820d107bc8b117cb",
        "RepoTags": [
            "felipestaypuff/tipsbank-web:v1.0.0",
            "tipsbank/web:dev"
        ],
        "RepoDigests": [
            "felipestaypuff/tipsbank-web@sha256:2830b4c4bdbd751b17d24eeaf4bb6f294dc31131e6e4849e820d107bc8b117cb",
            "tipsbank/web@sha256:2830b4c4bdbd751b17d24eeaf4bb6f294dc31131e6e4849e820d107bc8b117cb"
        ],
        "Comment": "buildkit.dockerfile.v0",
        "Created": "2026-04-25T17:46:06.821207791Z",
        "Config": {
            "User": "101",
            "ExposedPorts": {
                "8080/tcp": {}
            },
```

#### Scan Trivy — 4 imagens

```
Arquivos disponiveis nos diretórios de cada app, todas as tentativas.  /api-contas foi a base para CVE 0.

fepestaypuff/tipsbank-api-contas:v1.0.0 (wolfi 20230201)
══════════════════════════════════════════
Total: 0 (HIGH: 0, CRITICAL: 0)

felipestaypuff/tipsbank-api-transacoes:v1.0.0 (wolfi 20230201)
══════════════════════════════════════════════
Total: 0 (HIGH: 0, CRITICAL: 0)

felipestaypuff/tipsbank-auditoria:v1.0.0 (wolfi 20230201)
══════════════════════════════════════════
Total: 0 (HIGH: 0, CRITICAL: 0)

felipestaypuff/tipsbank-web:v1.0.0 (alpine 3.21)
══════════════════════════════════════════════════
Total: 0 (HIGH: 0, CRITICAL: 0)
```

#### Assinaturas Cosign verificadas

```bash

❯ cat cosing-todas.txt
File: cosing-todas.txt
[
  {
    "critical": {
      "identity": {
        "docker-reference": "index.docker.io/felipestaypuff/tipsbank-api-contas:v1.0.0"
      },
      "image": {
        "docker-manifest-digest": "sha256:05c5f3b2c81d39a45bab14705176337f3c303375707ed060f58b98060b4fe18c"
      },
      "type": "https://sigstore.dev/cosign/sign/v1"
    },
    "optional": {}
  }
]
[
  {
    "critical": {
      "identity": {
        "docker-reference": "index.docker.io/felipestaypuff/tipsbank-api-transacoes:v1.0.0"
      },
      "image": {
        "docker-manifest-digest": "sha256:4fefcd94fdadc031bb09080b161daea36b9d198a1b81577e3d53f9603249a66e"
      },
      "type": "https://sigstore.dev/cosign/sign/v1"
    },
    "optional": {}
  }
]
[
  {
    "critical": {
      "identity": {
        "docker-reference": "index.docker.io/felipestaypuff/tipsbank-auditoria:v1.0.0"
      },
      "image": {
        "docker-manifest-digest": "sha256:37a633a73c433514a171172eeaacc8278e2efd28e8d7ba000891f3579ca5ef51"
      },
      "type": "https://sigstore.dev/cosign/sign/v1"
    },
    "optional": {}
  }
]
[
  {
    "critical": {
      "identity": {
        "docker-reference": "index.docker.io/felipestaypuff/tipsbank-web:v1.0.0"
      },
      "image": {
        "docker-manifest-digest": "sha256:2830b4c4bdbd751b17d24eeaf4bb6f294dc31131e6e4849e820d107bc8b117cb"
      },
      "type": "https://sigstore.dev/cosign/sign/v1"
    },
    "optional": {}
  }
]
```
#### Observações ####

O principal problema encontrado nessa parte foi na imagem da `api-contas`: o scan apontou dois CVEs `CRITICAL` relacionados a uma dependência Python (`pyyaml`). Por isso eu usei essa imagem como base do ajuste e migrei para Chainguard/Distroless até chegar no resultado com `0 HIGH` e `0 CRITICAL`.

Outro ponto importante foi o uso de `latest`. Mesmo a Chainguard mantendo as imagens atualizadas, usar `latest` direto deixa o build menos previsível, porque a base pode mudar sem eu perceber. Para evitar esse tipo de variação, eu validei o digest da imagem e fixei a referência no Dockerfile. Assim o build passa a usar exatamente a imagem testada e versionada junto com o projeto.

 ```
❯ docker inspect cgr.dev/chainguard/python:latest --format '{{index .RepoDigests 0}}'
cgr.dev/chainguard/python@sha256:18a4fbda8c280978b6aa5329f7acd4dbb106876e76fdc87913855ebf4876f2ff

 ```


#### Screenshots

![](<imagens/Captura de tela 2026-04-25 065012.png>)
*Dockerfile multi-stage distroless*

![](<imagens/Captura de tela 2026-04-25 072153.png>)
*requirements.txt das dependências*

![](<imagens/Captura de tela 2026-04-25 091243.png>)
*Trivy scan — resultado do scan de vulnerabilidades*

![](<imagens/Captura de tela 2026-04-25 145426.png>)
*Docker history — imagem distroless (sem shell, sem camadas desnecessárias)*

![](<imagens/Captura de tela 2026-04-25 145754.png>)
*Docker Desktop — imagens TipsBank construídas*

![](<imagens/Captura de tela 2026-04-25 145855.png>)
*Docker Desktop — detalhes das imagens*

![](<imagens/Captura de tela 2026-04-25 150119.png>)
*Inspecção da imagem — digest e layers*

---

### Etapa 1.3 — Cluster kubeadm

**Data de conclusão:** 2026-04-26

#### Cluster provisionado

| Node | Hostname | IP | OS | Kubernetes | Runtime |
|---|---|---|---|---|---|
| control-plane | tb-master1 | 192.168.3.40 | Ubuntu 24.04.4 LTS | v1.35.4 | containerd://2.2.1 |
| worker | tb-worker1 | 192.168.3.41 | Ubuntu 24.04.4 LTS | v1.35.4 | containerd://2.2.1 |
| worker | tb-worker2 | 192.168.3.42 | Ubuntu 24.04.4 LTS | v1.35.4 | containerd://2.2.1 |

**CNI:** Calico v3.31.4 via Tigera Operator · **Pod CIDR:** 10.244.0.0/16

#### Teste 1 — Nodes Ready

```bash
kubectl get nodes -o wide
```

**Output:**
```
NAME         STATUS   ROLES           AGE     VERSION   INTERNAL-IP    EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
tb-master1   Ready    control-plane   41m     v1.35.4   192.168.3.40   <none>        Ubuntu 24.04.4 LTS   6.8.0-110-generic   containerd://2.2.1
tb-worker1   Ready    <none>          3m33s   v1.35.4   192.168.3.41   <none>        Ubuntu 24.04.4 LTS   6.8.0-110-generic   containerd://2.2.1
tb-worker2   Ready    <none>          3m14s   v1.35.4   192.168.3.42   <none>        Ubuntu 24.04.4 LTS   6.8.0-110-generic   containerd://2.2.1
```
---

#### Teste 2 — Todos os pods do sistema Running

```bash
kubectl get pods -A -o wide
```

**Output:**
```
NAMESPACE         NAME                                       READY   STATUS    RESTARTS   AGE     IP               NODE
calico-system     calico-kube-controllers-597ff8fcc5-ttv4v   1/1     Running   0          6m56s   10.244.119.4     tb-master1
calico-system     calico-node-b58jm                          1/1     Running   0          3m1s    192.168.3.42     tb-worker2
calico-system     calico-node-nj6dz                          1/1     Running   0          6m56s   192.168.3.40     tb-master1
calico-system     calico-node-zqbd8                          1/1     Running   0          3m20s   192.168.3.41     tb-worker1
calico-system     calico-typha-96f98c97d-dngcb               1/1     Running   0          6m56s   192.168.3.40     tb-master1
calico-system     calico-typha-96f98c97d-h69dv               1/1     Running   0          3m      192.168.3.41     tb-worker1
calico-system     csi-node-driver-m8pgk                      2/2     Running   0          3m20s   10.244.209.193   tb-worker1
calico-system     csi-node-driver-vhvth                      2/2     Running   0          3m1s    10.244.247.1     tb-worker2
calico-system     csi-node-driver-vlmnr                      2/2     Running   0          6m56s   10.244.119.1     tb-master1
kube-system       coredns-7d764666f9-bgpzr                   1/1     Running   0          41m     10.244.119.3     tb-master1
kube-system       coredns-7d764666f9-kf6db                   1/1     Running   0          41m     10.244.119.2     tb-master1
kube-system       etcd-tb-master1                            1/1     Running   0          41m     192.168.3.40     tb-master1
kube-system       kube-apiserver-tb-master1                  1/1     Running   0          41m     192.168.3.40     tb-master1
kube-system       kube-controller-manager-tb-master1         1/1     Running   0          41m     192.168.3.40     tb-master1
kube-system       kube-proxy-2fz7n                           1/1     Running   0          3m20s   192.168.3.41     tb-worker1
kube-system       kube-proxy-8psbk                           1/1     Running   0          41m     192.168.3.40     tb-master1
kube-system       kube-proxy-d6gsv                           1/1     Running   0          3m1s    192.168.3.42     tb-worker2
kube-system       kube-scheduler-tb-master1                  1/1     Running   0          41m     192.168.3.40     tb-master1
tigera-operator   tigera-operator-6cf4cccc57-8p5wr           1/1     Running   0          22m     192.168.3.40     tb-master1
```
---

#### Teste 3 — Pod nginx

```bash
kubectl run nginx --image=nginx
```

**Output:**
```
k get pod nginx -owide
NAME    READY   STATUS    RESTARTS   AGE     IP             NODE         NOMINATED NODE   READINESS GATES
nginx   1/1     Running   0          9m23s   10.244.247.3   tb-worker2   <none>           <none>


kubectl describe node tb-master1 | grep Taints.

Taints:             node-role.kubernetes.io/control-plane:NoSchedule

```


#### Screenshots

![](<imagens/Captura de tela 2026-04-26 130350.png>)
*kubectl edit — ajuste de pod no cluster*

![](<imagens/Captura de tela 2026-04-26 130540.png>)
*kubectl get pods — cluster kubeadm operacional*

![](<imagens/Captura de tela 2026-04-26 130716.png>)
*Nós do cluster — tb-master1, tb-worker1, tb-worker2*

---

### Etapa 1.4 — Namespaces, Deployments e Services

**Data de conclusão:** 2026-04-28

#### Critério 1 — Todos os pods Running

```bash
kubectl get pods -A | grep tipsbank
```

**Output:**
```
tipsbank-auditoria    auditoria-659555485f-r7hbw                 1/1     Running   0               4h11m
tipsbank-auditoria    auditoria-659555485f-zn4tr                 1/1     Running   0               4h11m
tipsbank-contas       api-contas-65d86d5dc7-d6lt6                1/1     Running   0               150m
tipsbank-contas       api-contas-65d86d5dc7-mzns4                1/1     Running   0               150m
tipsbank-contas       postgres-0                                 1/1     Running   0               74m
tipsbank-transacoes   api-transacoes-7558cf5d9c-87vc4            1/1     Running   0               46m
tipsbank-transacoes   api-transacoes-7558cf5d9c-xvqxt            1/1     Running   0               46m
tipsbank-web          web-6bc8b8c546-4hc57                       1/1     Running   0               7m14s
tipsbank-web          web-6bc8b8c546-jwjpt                       1/1     Running   0               7m20s
```

---

#### Critério 2 — Transferência via api-transacoes

```bash
kubectl port-forward -n tipsbank-transacoes svc/api-transacoes 8080:8080

curl -s -X POST http://localhost:8080/transferencias \
  -H "Content-Type: application/json" \
  -d '{"origem_id":"11111111-1111-1111-1111-111111111111","destino_id":"22222222-2222-2222-2222-222222222222","valor":50}' \
  | jq .
```

**Output:**
```json
{
  "id": "9054a950-45c9-46bf-b470-b8012bc2d421",
  "origem_id": "11111111-1111-1111-1111-111111111111",
  "destino_id": "22222222-2222-2222-2222-222222222222",
  "valor": "50.00",
  "status": "concluida"
}
```

---

#### Critério 3 — SPA com login

```bash
kubectl port-forward -n tipsbank-web svc/web 8080:8080 &
sleep 2
curl -s http://localhost:8080/ | grep -i "title\|tipsbank"
```

**Output:**
```
<title>TipsBank — Internet Banking de Luxo</title>
        <img src="/img/logo-banco.png" alt="TipsBank" />
```

Browser: `http://localhost:8080` → login com documento `12345678901` / senha `giropops` → tela de contas abre ✅

---

#### Critério 4 — imagePullSecrets

Imagens públicas no Docker Hub (`felipestaypuff/tipsbank-*:v1.0.0`) — imagePullSecrets nenhumas das imagens esta como private.


#### Screenshots

![](<imagens/Captura de tela 2026-04-27 174113.png>)
*VS Code — manifests YAML de Deployments e Services*

![](<imagens/Captura de tela 2026-04-28 000523.png>)
*Login na aplicação TipsBank rodando no cluster*

![](<imagens/Captura de tela 2026-04-28 000546.png>)
*Tela de login — autenticação com conta de teste*

![](<imagens/Captura de tela 2026-04-28 004537.png>)
*Dashboard — conta Jeferson Fernando acessível*

---

### Etapa 1.5 — ConfigMap, Secret e pod multicontainer

**Data de conclusão:** 2026-04-28

#### Critério 1 — Pods com 2/2 containers Running

```bash
kubectl get all -A | grep tipsbank
```

**Output:**
```
tipsbank-transacoes   pod/api-transacoes-d4cdd957b-pbhmw             2/2     Running   0               15m
tipsbank-transacoes   pod/api-transacoes-d4cdd957b-sbqsc             2/2     Running   0               14m
```

---

#### Critério 2 — Sidecar lê log estruturado da app

```bash
kubectl logs -c log-forwarder <pod> -n tipsbank-transacoes
```

**Output (`k8s/pod-log-forwarder.txt`):**
```
Aguardando o arquivo de log ser criado...
Aguardando o arquivo de log ser criado...
Aguardando o arquivo de log ser criado...
Aguardando o arquivo de log ser criado...
{"ts":"2026-04-28 22:30:34,474","level":"INFO","service":"api-transacoes","msg":"bootstrap versao=v1"}
```
---

#### Critério 3 — Nenhuma variável sensível no Deployment

```bash
kubectl get deployment api-transacoes -n tipsbank-transacoes -o json | grep -A4 '"env"'
```

**Output (extrato de `k8s/DB_URL.txt`):**
```json
{"name":"DB_URL","valueFrom":{"secretKeyRef":{"key":"DB_URL","name":"transacoes-secret"}}},
{"name":"CONTAS_URL","valueFrom":{"configMapKeyRef":{"key":"CONTAS_URL","name":"transacoes-config"}}},
{"name":"AUDITORIA_URL","valueFrom":{"configMapKeyRef":{"key":"AUDITORIA_URL","name":"transacoes-config"}}},
{"name":"APP_VERSION","valueFrom":{"configMapKeyRef":{"key":"APP_VERSION","name":"transacoes-config"}}},
{"name":"LOG_LEVEL","valueFrom":{"configMapKeyRef":{"key":"LOG_LEVEL","name":"transacoes-config"}}}
```

---


### Etapa 1.6 — PV NFS para a auditoria

**Data de conclusão:** 2026-04-29

**Setup de storage:**

- Manifestos de criação dos storageClass em Tipsbank /clusters/nfs-tp-data.yaml
- StorageClass: `nfs-tp-data` (provisioner: `nfs.csi.k8s.io`, server: `192.168.3.11:/mnt/nfs-data/k8s`)
- PVC: `auditoria-pvc` · RWX · 2Gi · Retain
- Deployment: `securityContext.fsGroup: 65532` (usuário nonroot Distroless)
- Réplicas: 3

---

#### Critério 1 — PVC Bound ao PVC correto

```bash
kubectl get pv,pvc -n tipsbank-auditoria -o wide
```

**Output:**
```
NAME                                                        CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                               STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
persistentvolume/pvc-57fc82db-1c3a-451c-ba7e-50dc8cba78bb   2Gi        RWX            Retain           Bound    tipsbank-auditoria/auditoria-pvc    nfs-tp-data    <unset>                          24h

NAME                                 STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/auditoria-pvc  Bound    pvc-57fc82db-1c3a-451c-ba7e-50dc8cba78bb   2Gi        RWX            nfs-tp-data    <unset>                 24h
```

---

#### Critério 2 — Mesmos arquivos nos pods (Distroless: python3 no lugar de ls)

> **Nota:** a imagem `auditoria` é Distroless — não tem `ls`. Substituto: `python3 -c "import os; print(os.listdir('/data'))"`

```bash
kubectl exec auditoria-659555485f-hqzjc -n tipsbank-auditoria -- python3 -c "import os; print(os.listdir('/data'))"
kubectl exec auditoria-659555485f-r7hbw -n tipsbank-auditoria -- python3 -c "import os; print(os.listdir('/data'))"
```

**Output:**
```
['eventos-2026-04-28.jsonl', 'eventos-2026-04-29.jsonl']
['eventos-2026-04-28.jsonl', 'eventos-2026-04-29.jsonl']
```

#### OBSERVAÇÕES: ####

Para conseguir acessar o conteúdo do PV, primeiramente eu criei um pod debug com a imagem `busybox` e criei um arquivo no barra no diretorio /data. Os arquivos foram lidos pelos pods da auditoria.
Lembrando que todos os containers foram criados com usuário nonroot, o que é uma boa prática de segurança, contudo isso não impede de criar arquivos no PV, o que é esperado. O importante é que os arquivos criados sejam legíveis pelos pods da auditoria.

          spec:
            securityContext:
              fsGroup: 65532

 https://kubernetes.io/docs/tasks/configure-pod-container/security-context/


```bash
kubectl exec auditoria-659555485f-hqzjc -n tipsbank-auditoria -- python3 -c "import os; print(os.listdir('/data'))"
kubectl exec auditoria-659555485f-r7hbw -n tipsbank-auditoria -- python3 -c "import os; print(os.listdir('/data'))"
```

```
['eventos-2026-04-28.jsonl', 'eventos-2026-04-29.jsonl', 'teste-pv.txt']
['eventos-2026-04-28.jsonl', 'eventos-2026-04-29.jsonl', 'teste-pv.txt']
```

Achei preocupante usar um container montado no cluster para auditoria então procurei na documentação da chainguard como criar um container de debug e como ler adequadamente o conteúdo dos PV´s

https://edu.chainguard.dev/chainguard/chainguard-images/troubleshooting/kubectl_cdebug/

```
k debug -it auditoria-659555485f-hqzjc --image busybox --target=auditoria -n tipsbank-auditoria --profile=sysadmin
Targeting container "auditoria". If you don't see processes from this container it may be because the container runtime doesn't support this feature.
Defaulting debug container name to debugger-ms8vk.
All commands and output from this session will be recorded in container logs, including credentials and sensitive information passed through the command prompt.
If you don't see a command prompt, try pressing enter.
/ # ls /proc/1/root/
app/       bin/       data/      dev/       etc/       home/      lib/       lib64/     opt/       packages/  proc/      root/      run/       sbin/      sys/       tmp/       usr/       var/
/ # ls /proc/1/root/data/
eventos-2026-04-28.jsonl  eventos-2026-04-29.jsonl
/ # cat eventos-2026-04-28.jsonl
cat: can't open 'eventos-2026-04-28.jsonl': No such file or directory
/ # cat /proc/1/root/data/eventos-2026-04-28.jsonl
{"id": "75ac655d-4d82-42c3-9dcd-470f36ab45db", "recebido_em": "2026-04-28T03:01:58.583345+00:00", "tipo": "transferencia", "transacao_id": "6bc06460-4f69-4f85-8600-40c186e40e97", "origem_id": "11111111-1111-1111-1111-111111111111", "destino_id": "22222222-2222-2222-2222-222222222222", "valor": "100.00", "versao_app": "v1"}
{"id": "aed3efe3-da43-43d5-9e99-dc56e6391261", "recebido_em": "2026-04-28T03:43:56.847037+00:00", "tipo": "transferencia", "transacao_id": "9054a950-45c9-46bf-b470-b8012bc2d421", "origem_id": "11111111-1111-1111-1111-111111111111", "destino_id": "22222222-2222-2222-2222-222222222222", "valor": "50.00", "versao_app": "v1"}
{"id": "a828e1b5-bccd-42ad-ba8d-3b6c639f48c4", "recebido_em": "2026-04-28T22:10:45.693070+00:00", "tipo": "transferencia", "transacao_id": "7b11e5dc-621d-4296-87c6-46370e62bc50", "origem_id": "11111111-1111-1111-1111-111111111111", "destino_id": "22222222-2222-2222-2222-222222222222", "valor": "50.00", "versao_app": "v1"}
/ #

```

---

#### Critério 3 — 100 transferências → 100 novas linhas no JSONL

```bash

# Port-forward + 100 transferências
shell 1 - kubectl port-forward -n tipsbank-transacoes svc/api-transacoes 8080:8080 &
sleep 2

shell 2 - for i in $(seq 1 100); do
            curl -s -X POST http://localhost:8080/transferencias \
               -H "Content-Type: application/json" \
               -d '{"origem_id":"11111111-1111-1111-1111-111111111111","destino_id":"22222222-2222-2222-2222-222222222222","valor":1}' \
               -o /dev/null
          done

```

**Output:**
```
kubectl exec -n tipsbank-auditoria debug-nfs -- wc -l /data/eventos-2026-04-29.jsonl
101 /data/eventos-2026-04-29.jsonl
```

101 linhas em `eventos-2026-04-29.jsonl` — 100 do for loop + 1 do teste manual.


#### Screenshots

![](<imagens/Captura de tela 2026-04-27 174248.png>)
*NFS /data — arquivo de auditoria criado e lido pelo pod*

---


## Semana 2 — Exposição e Segurança de Rede

### Etapa 2.1 — Ingress Nginx + múltiplos hosts

**Data de conclusão:** 2026-04-29

**Setup:**
- MetalLB instalado via Helm · IP Pool: `192.168.3.200-209` · IP alocado: `192.168.3.110`
- Ingress Nginx Controller instalado via Helm · `type: LoadBalancer` · EXTERNAL-IP: `192.168.3.110`
- DNS Pi-hole: `app.tipsbank.staypuff.info` e `api.tipsbank.staypuff.info` → `192.168.3.110`
- Ingresses criados: `tipsbank-web` (frontend), `tipsbank-contas`, `tipsbank-transacoes`, `tipsbank-auditoria`

#### Critério 1 — Frontend SPA acessível via hostname

```bash
curl -s http://app.tipsbank.staypuff.info/ | grep -i "tipsbank\|title"
```

**Output:**
```
<title>TipsBank — Internet Banking de Luxo</title>
        <img src="/img/logo-banco.png" alt="TipsBank" />
```

#### Critério 2 — API contas via Ingress com path routing

```bash
curl -s http://api.tipsbank.staypuff.info/contas/contas | python3 -m json.tool
```

**Output:**
```json
[
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "titular": "Jeferson Fernando",
        "documento": "12345678901",
        "saldo": "9699.00"
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "titular": "LinuxTips SA",
        "documento": "98765432100",
        "saldo": "801.00"
    }
]
```

#### Critério 3 — Health checks das 3 APIs via Ingress

```bash
curl -s http://api.tipsbank.staypuff.info/contas/health/live
curl -s http://api.tipsbank.staypuff.info/transacoes/health/live
curl -s http://api.tipsbank.staypuff.info/auditoria/health/live
```

**Output:**
```
{"status":"ok"}
{"status":"ok","version":"v1"}
{"status":"ok"}
```


#### Screenshots

![](<imagens/Captura de tela 2026-04-29 204941.png>)
*VS Code — MetalLB e Ingress Nginx YAML*

![](<imagens/Captura de tela 2026-04-29 223452.png>)
*VS Code — Ingress resource configurado*

![](<imagens/Captura de tela 2026-05-01 181601.png>)
*curl HTTP — todos os hosts respondendo corretamente*

![](<imagens/Captura de tela 2026-05-01 201139.png>)
*helm install ingress-nginx via MetalLB*

---

### Etapa 2.2 — TLS + recursos avançados do Ingress

**Data de conclusão:** 2026-05-01

**Setup:**
- TLS: cert-manager + ClusterIssuer `prod-letsencrypt-cloudflare` (Let's Encrypt DNS-01 via API Cloudflare)
- Certificados: Let's Encrypt reais, browser-trusted, renovação automática em 30 dias antes do vencimento
- Rate limit: `limit-rps: "50"` no Ingress frontend + `limit-req-status-code: "429"` no ConfigMap global
- Basic Auth: Secret `basic-auth` no namespace `tipsbank-contas` + Ingress dedicado para `/contas/admin`
- Affinity Cookie: `TIPSBANK_AFFINITY` com `Max-Age=172800` no Ingress de transações

#### Critério 1 — HTTPS funcionando com cert Let's Encrypt real

```bash
curl https://app.tipsbank.staypuff.info/
curl https://api.tipsbank.staypuff.info/contas/health/live

echo | openssl s_client -connect 192.168.3.110:443 \
  -servername app.tipsbank.staypuff.info 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

**Output:**
```
subject=CN = app.tipsbank.staypuff.info
issuer=C = US, O = Let's Encrypt, CN = R12
notBefore=May  2 01:36:16 2026 GMT
notAfter=Jul 31 01:36:15 2026 GMT
```

```
kubectl get certificate -A
NAMESPACE             NAME               READY   SECRET             AGE
tipsbank-auditoria    api-tipsbank-tls   True    api-tipsbank-tls   46s
tipsbank-contas       api-tipsbank-tls   True    api-tipsbank-tls   2m45s
tipsbank-transacoes   api-tipsbank-tls   True    api-tipsbank-tls   84s
tipsbank-web          app-tipsbank-tls   True    app-tipsbank-tls   8m3s
```

`curl` sem `-k` funcionando. Browser mostra TLS sem aviso. Cert emitido via DNS-01.

**Nota:** `limit-req-status-code` é configuração global do ConfigMap do ingress-nginx (não annotation por Ingress).
https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/configmap/#limit-req-status-code

Patch aplicado: `kubectl patch configmap ingress-nginx-controller -n ingress-nginx --type merge -p '{"data":{"limit-req-status-code":"429"}}'`

#### Critério 2 — Basic Auth: 401 sem credencial, 200 com credencial

```bash
curl -k https://api.tipsbank.staypuff.info/contas/admin/contas
```

**Output:**
```html
<html>
<head><title>401 Authorization Required</title></head>
<body>
<center><h1>401 Authorization Required</h1></center>
<hr><center>nginx</center>
</body>
</html>
```

```bash
curl -k -u admin:senha123 https://api.tipsbank.staypuff.info/contas/admin/contas
```

**Output:**
```json
[{"id":"11111111-1111-1111-1111-111111111111","titular":"Jeferson Fernando","documento":"12345678901","saldo":"9699.00"},{"id":"22222222-2222-2222-2222-222222222222","titular":"LinuxTips SA","documento":"98765432100","saldo":"801.00"}]
```

#### Critério 3 — Rate limit 429 após rajada

```bash
hey -n 1000 -c 10 https://app.tipsbank.staypuff.info/
```

**Output (extrato):**
```
Requests/sec: 4187.4280

Status code distribution:
  [200]  261 responses
  [429]  739 responses
```

**Nota — por que a annotation não funcionou e foi necessário o ConfigMap:**

Aqui o problema foi uma diferença de escopo dentro do ingress-nginx. Eu tentei tratar o retorno `429` como se fosse uma annotation do próprio Ingress, mas essa annotation não existe.

O `limit-rps` funciona por rota, porque ele injeta o `limit_req` no bloco `location` do `nginx.conf`. Só que o status retornado quando o limite é estourado vem da diretiva `limit_req_status`, que fica no bloco global `http {}`. Por isso o ajuste certo não era no Ingress da aplicação, e sim no ConfigMap do controller.

Referência oficial: https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/configmap/

| Chave | Tipo | Default | Descrição |
|---|---|---|---|
| `limit-req-status-code` | int | **503** | HTTP status code retornado quando o rate limit é excedido |

Patch aplicado:
```bash
kubectl patch configmap ingress-nginx-controller -n ingress-nginx \
  --type merge \
  -p '{"data":{"limit-req-status-code":"429"}}'
kubectl rollout restart deployment ingress-nginx-controller -n ingress-nginx
```



#### Critério 4 — Affinity Cookie em transações

```bash
curl -k -v https://api.tipsbank.staypuff.info/transacoes/health/live 2>&1 | grep -i set-cookie
```

**Output:**
```
set-cookie: TIPSBANK_AFFINITY=1777686728.211.645.931183|ce724c427397688022a6eba53715081e; Expires=Mon, 04-May-26 01:52:07 GMT; Max-Age=172800; Path=/transacoes; Secure; HttpOnly
```

#### Nota arquitetural — TLS no homelab vs EKS

| Ambiente | TLS termina em | cert-manager? |
|---|---|---|
| Homelab (este lab) | nginx-ingress (cert-manager + Let's Encrypt DNS-01 Cloudflare) | Sim |
| EKS com ALB | AWS ALB + ACM | Não |
| EKS com Nginx Ingress | nginx-controller (cert-manager + Let's Encrypt DNS-01) | Sim |


#### Screenshots

![](<imagens/Captura de tela 2026-05-01 235112.png>)
*helm install cert-manager — instalação do controlador*

![](<imagens/Captura de tela 2026-05-01 235134.png>)
*Certificado TLS emitido pelo Let's Encrypt*

![](<imagens/Captura de tela 2026-05-01 235153.png>)
*Browser — HTTPS validado com cadeado verde*

![](<imagens/Captura de tela 2026-05-01 235215.png>)
*curl HTTPS — resposta 200 com TLS*

![](<imagens/Captura de tela 2026-05-01 235228.png>)
*Detalhes do certificado — CN e validade*

---

### Etapa 2.3 — Cluster EKS Paralelo

**Data de conclusão:** 2026-05-03

**Setup:**
- Cluster EKS `tipsbank` provisionado via `eksctl create cluster` na região `us-east-1` (2 nodes managed, `t3.medium`)
- EBS CSI Driver instalado via addon eksctl + IRSA com policy `AmazonEBSCSIDriverPolicy`
- EFS CSI Driver instalado via addon eksctl + IAM com `AmazonElasticFileSystemFullAccess`
- EFS File System `fs-0d5b539e1d48f267d` criado com mount targets na VPC do cluster
- Storage: PostgreSQL em PVC gp2 (RWO), auditoria em PV EFS estático (RWX)
- Ingress Nginx instalado via Helm (`type: LoadBalancer` → NLB AWS provisionado)
- cert-manager + ClusterIssuer `prod-letsencrypt-cloudflare` (mesmo do homelab — DNS-01 não precisa de acesso HTTP ao cluster)
- Secret `cloudflare-api-token-secret` copiado do homelab para o EKS

**Problemas encontrados e soluções:**

Nessa etapa os problemas vieram principalmente da diferença entre o homelab e o EKS. O manifesto que funcionava localmente precisava de ajustes para storage, DNS e permissões AWS.

| # | Problema | Causa | Solução |
|---|---|---|---|
| 1 | `eksctl create cluster` → `AccessDeniedException: eks:DescribeClusterVersions` | IAM user `eks-tipsbank` sem permissões EKS | Inline policy com `eks:*`, `ssm:GetParameter`, `autoscaling:*`, `ecr:*` |
| 2 | `ebs-csi-controller` CrashLoopBackOff | OIDC não habilitado no cluster → service account sem credenciais AWS | `eksctl utils associate-iam-oidc-provider` + `eksctl create iamserviceaccount` + `rollout restart` |
| 3 | `postgres-0` Pending | StatefulSet com `storageClassName: local-path` (não existe no EKS) | Alterado para `gp2` no manifest adaptado |
| 4 | `postgres-0` CrashLoopBackOff após bind do EBS | EBS ext4 cria `lost+found` na raiz do volume → initdb recusa diretório não-vazio | Adicionado `PGDATA=/var/lib/postgresql/data/pgdata` (subdiretório limpo) |
| 5 | PVC `auditoria-pvc` ProvisioningFailed | EFS CSI Driver v3.0.1: bug no modo `efs-ap` — campo `permissions` não é passado ao `CreateAccessPoint` | Abandonado dynamic provisioning; criado PV estático com `volumeHandle: fs-0d5b539e1d48f267d` (sem Access Point) |
| 6 | Frontend "offline" (nginx 502, DNS timeout) | nginx `resolver 10.96.0.10` (CoreDNS homelab) inacessível do EKS — CoreDNS do EKS é `10.100.0.10` | Novo ConfigMap com `resolver 10.100.0.10` + `rollout restart` do Deployment web |

O primeiro bloqueio foi permissão: o usuário IAM ainda não tinha acesso suficiente para o `eksctl` consultar e criar os recursos do EKS. Depois disso, o EBS CSI entrou em `CrashLoopBackOff` porque faltava associar o OIDC ao cluster, então o service account não conseguia assumir a role da AWS via IRSA.

No PostgreSQL, o problema foi de storage. O manifesto ainda usava `local-path`, que existia no homelab, mas não no EKS. Troquei para `gp2`. Depois que o EBS montou, apareceu outro detalhe: volume ext4 cria o diretório `lost+found` na raiz, e o `initdb` do Postgres não aceita inicializar em um diretório que já tenha conteúdo. A correção foi apontar o `PGDATA` para um subdiretório limpo.

Na auditoria, o EFS CSI falhou no provisionamento dinâmico com Access Point, então abandonei o dynamic provisioning e usei um PV estático apontando para o File System. Para esse lab ficou mais direto e previsível.

O frontend ficou offline com `502` porque o Nginx ainda estava configurado com o IP do CoreDNS do homelab (`10.96.0.10`). No EKS o CoreDNS era `10.100.0.10`, então o Nginx não resolvia os serviços internos. Ajustei o ConfigMap e reiniciei o Deployment web. Como esse arquivo é montado com `subPath`, o Kubernetes não faz hot-reload automático do ConfigMap dentro do pod; por isso o `rollout restart` é obrigatório depois desse tipo de alteração.

---

#### Critério 1 — Dois contexts funcionando no kubeconfig

```bash
kubectl config get-contexts
```

**Output:**
```
CURRENT   NAME           CLUSTER                                    AUTHINFO                                                NAMESPACE
*         eks-tipsbank   tipsbank.us-east-1.eksctl.io               felipe@tipsbank.us-east-1.eksctl.io
          homelab-k8s    kubernetes                                 kubernetes-admin
          kind-girus     kind-girus                                 kind-girus
          tipsbank       tipsbank                                   kubernetes-admin-tipsbank
```

---

#### Critério 2 — Nodes do EKS com status Ready

```bash
kubectl --context eks-tipsbank get nodes -o wide
```

**Output:**
```
NAME                             STATUS   ROLES    AGE   VERSION                INTERNAL-IP      EXTERNAL-IP     OS-IMAGE         KERNEL-VERSION   CONTAINER-RUNTIME
ip-192-168-22-154.ec2.internal   Ready    <none>   8h    v1.31.14-eks-40737a8   192.168.22.154   3.80.218.169    Amazon Linux 2   5.10.235-227.928.amzn2.x86_64   containerd://1.7.27
ip-192-168-43-182.ec2.internal   Ready    <none>   8h    v1.31.14-eks-40737a8   192.168.43.182   98.93.78.27     Amazon Linux 2   5.10.235-227.928.amzn2.x86_64   containerd://1.7.27
```

---

#### Critério 3 — TipsBank acessível via HTTPS com DNS real

```bash
curl -s https://app.tipsbank.staypuff.info/healthz
curl -s https://api.tipsbank.staypuff.info/contas/health/live
curl -s https://api.tipsbank.staypuff.info/transacoes/health/live
curl -s https://api.tipsbank.staypuff.info/auditoria/health/live
```

**Output:**
```
ok
{"status":"ok"}
{"status":"ok","version":"v1"}
{"status":"ok"}
```

```bash
kubectl --context eks-tipsbank get certificate -A
```

**Output:**
```
NAMESPACE             NAME               READY   SECRET             AGE
tipsbank-auditoria    api-tipsbank-tls   True    api-tipsbank-tls   2h
tipsbank-contas       api-tipsbank-tls   True    api-tipsbank-tls   2h
tipsbank-transacoes   api-tipsbank-tls   True    api-tipsbank-tls   2h
tipsbank-web          app-tipsbank-tls   True    app-tipsbank-tls   2h
```

```bash
kubectl --context eks-tipsbank get clusterissuer prod-letsencrypt-cloudflare
```

**Output:**
```
NAME                            READY   AGE
prod-letsencrypt-cloudflare     True    2h
```

```bash
kubectl --context eks-tipsbank get pv,pvc -A | grep tipsbank
```

**Output:**
```
persistentvolume/auditoria-efs-pv                            5Gi        RWX            Retain           Bound     tipsbank-auditoria/auditoria-pvc                                    2h
persistentvolume/pvc-6bb54f9c-...                            5Gi        RWO            Delete           Bound     tipsbank-contas/postgres-data-postgres-0   gp2                     2h

tipsbank-auditoria   auditoria-pvc              Bound    auditoria-efs-pv     5Gi    RWX                    2h
tipsbank-contas      postgres-data-postgres-0   Bound    pvc-6bb54f9c-...     5Gi    RWO    gp2              2h
```

Cluster destruído com `eksctl delete cluster --name tipsbank --region us-east-1` após concluir as evidências.


#### Screenshots

![](<imagens/Captura de tela 2026-05-03 113222.png>)
*eksctl create cluster — criação do cluster EKS tipsbank*

![](<imagens/Captura de tela 2026-05-03 113516.png>)
*kubectl config get-contexts — contexto EKS ativo*

![](<imagens/Captura de tela 2026-05-03 114821.png>)
*kubectl get nodes — worker nodes EKS Running*

![](<imagens/Captura de tela 2026-05-03 115945.png>)
*EBS CSI driver — instalação do addon*

![](<imagens/Captura de tela 2026-05-03 120130.png>)
*Ingress Nginx — LoadBalancer NLB provisionado*

![](<imagens/Captura de tela 2026-05-03 120413.png>)
*Cloudflare DNS — registros apontando para o NLB*

![](<imagens/Captura de tela 2026-05-03 120640.png>)
*kubectl get ingress — ADDRESS do NLB*

![](<imagens/Captura de tela 2026-05-03 120649.png>)
*dig tipsbank.staypuff.info — resolução para IPs do NLB*

![](<imagens/Captura de tela 2026-05-03 121329.png>)
*AWS Console — instâncias EC2 worker nodes*

![](<imagens/Captura de tela 2026-05-03 122619.png>)
*kubectl apply — postgres StatefulSet no EKS*

![](<imagens/Captura de tela 2026-05-03 124816.png>)
*postgres — CrashLoopBackOff resolvido, pod Running 1/1*

![](<imagens/Captura de tela 2026-05-03 130403.png>)
*kubectl apply — api-contas Deployment no EKS*

![](<imagens/Captura de tela 2026-05-03 195244.png>)
*kubectl get all -A — todos os pods Running no EKS*

![](<imagens/Captura de tela 2026-05-03 200701.png>)
*TipsBank — homepage acessível no EKS*

![](<imagens/Captura de tela 2026-05-03 202048.png>)
*TipsBank — dashboard com 2 correntistas*

![](<imagens/Captura de tela 2026-05-03 202958.png>)
*kubectl apply — todos os Ingresses configurados*

![](<imagens/Captura de tela 2026-05-03 203239.png>)
*Transferência de R\$ 99,99 via EKS*

![](<imagens/Captura de tela 2026-05-03 203256.png>)
*Extrato — transferência registrada no EKS*

![](<imagens/Captura de tela 2026-05-03 203938.png>)
*Dashboard — Olá Felipe, R\$ 100.000.000,00 no EKS*

---

### Etapa 2.4 — Canary de Transações

**Data de conclusão:** 2026-05-04

**Setup:**
- Deployment `api-transacoes-v2` (1 réplica) com imagem `felipestaypuff/tipsbank-api-transacoes:v2.0.0`
- Service `api-transacoes-v2` ClusterIP porta 8080
- Ingress canário `tipsbank-api-transacoes-canary` com `canary-weight: "10"` + `canary-by-header-value: "true"`
- Endpoint novo: `GET /pix` (mock) disponível apenas na v2

#### Critério 1 — Split ~90/10 por peso

```bash
for i in $(seq 1 100); do
  curl -sk -c /dev/null https://api.tipsbank.staypuff.info/transacoes/health/live
done | grep -o '"version":"v[12]"' | sort | uniq -c
```

**Output (4 amostras):**
```
  84 "version":"v1"    16 "version":"v2"
  92 "version":"v1"     8 "version":"v2"
  92 "version":"v1"     8 "version":"v2"
  91 "version":"v1"     9 "version":"v2"
```

Split dentro da faixa esperada (~90/10).

#### Critério 2 — Header `X-Canary: true` força 100% para v2

```bash
curl -sk -H "X-Canary: true" https://api.tipsbank.staypuff.info/transacoes/health/live
```

**Output:**
```json
{"status":"ok","version":"v2"}
```

#### Critério 3 — Endpoint `/pix` acessível via v2

```bash
curl -sk -H "X-Canary: true" https://api.tipsbank.staypuff.info/transacoes/pix
```

**Output:**
```json
{"versao":"v2","chave_tipo":"cpf","chave":"000.000.000-00","banco":"TipsBank","mensagem":"Endpoint PIX disponivel apenas na v2"}
```

#### Critério 4 — `rollout undo` funciona em ambos os Deployments

```bash
kubectl rollout undo deployment/api-transacoes-v2 -n tipsbank-transacoes
kubectl rollout history deployment/api-transacoes-v2 -n tipsbank-transacoes
```

**Output:**
```
deployment.apps/api-transacoes-v2 rolled back
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```

**Problemas encontrados:**

Os problemas do canary foram pequenos, mas todos ligados a detalhes que mudam completamente o comportamento do roteamento.

| # | Problema | Causa | Solução |
|---|---|---|---|
| 1 | Pod v2 retornando `version: v1` | Env var `APP-VERSION` (hífen) é inválida em Linux — ignorada. `APP_VERSION` do ConfigMap sobrescrevia com `v1` |  `APP_VERSION: "v2"`  |
| 2 | `X-Canary: always` não forçava v2 | `canary-by-header-value: "true"` substitui os valores padrão `always`/`never` | `X-Canary: true` (valor configurado) |
| 3 | `curl -H " X-Canary: true"` (espaço no header) não funcionou | Espaço antes do nome do header — nginx não reconhece, cai no weight | Header names são whitespace-sensitive |

O primeiro ponto foi a versão da aplicação. O pod v2 subia, mas respondia como `v1`, porque eu tinha usado `APP-VERSION` com hífen. Em variável de ambiente Linux isso não é um nome válido, então o valor era ignorado e o `APP_VERSION` antigo do ConfigMap continuava vencendo. Corrigi para `APP_VERSION: "v2"`.

Depois teve o header do canary. Como eu configurei `canary-by-header-value: "true"`, o valor esperado passou a ser exatamente `true`. Nesse modo, `always` e `never` deixam de ser os valores padrão úteis para o teste. Também peguei um erro simples de digitação no `curl`: havia um espaço antes de `X-Canary`, e o Nginx não reconhece esse header como o mesmo nome.


#### Screenshots

![](<imagens/Captura de tela 2026-05-04 101916.png>)
*locustfile.py — script de carga para teste do canary*

![](<imagens/Captura de tela 2026-05-04 102049.png>)
*docker build — construção da imagem api-transacoes-v2*

![](<imagens/Captura de tela 2026-05-04 102323.png>)
*cosign sign — assinatura da imagem v2.0.0*

![](<imagens/Captura de tela 2026-05-04 105816.png>)
*cosign verify + kubectl apply — deploy da v2*

![](<imagens/Captura de tela 2026-05-04 105925.png>)
*kubectl get pods — api-transacoes v1 e v2 Running*

![](<imagens/Captura de tela 2026-05-04 114535.png>)
*kubectl get pods — todos os pods tipsbank-transacoes Running*

![](<imagens/Captura de tela 2026-05-04 114656.png>)
*wget health/live — resposta confirmando versão v1/v2*

![](<imagens/Captura de tela 2026-05-04 151935.png>)
*Ingress canary — weight=10, for loop curl (v1 e v2 respondendo)*

![](<imagens/Captura de tela 2026-05-04 160207.png>)
*Canary weight=50 — distribuição 50/50 confirmada*

---

### Etapa 2.5 — NetworkPolicy Zero-Trust

**Data de conclusão:** 2026-05-05

**Setup:**
- CNI: Calico v3.31.4 (Felix + iptables) — NetworkPolicy suportada nativamente
- 18 NetworkPolicies aplicadas: 4 `default-deny` + 14 `allow` nos 4 namespaces
- Arquivos: `k8s/network-policies/deny-all.yaml` + `allow-tipsbank-{contas,transacoes,auditoria,web}.yaml`
- Regra DNS: port-only (sem `to:`), obrigatório pelo DNAT do kube-proxy ser avaliado após o Calico
- NFS egress: ipBlock `192.168.3.0/24` com `except` para os 3 nodes do cluster

#### Critério 1 — auditoria NÃO acessa api-contas (timeout esperado)

```bash
# Teste via ClusterIP direto sem DNS
kubectl debug -it auditoria-659555485f-hqzjc \
  --image=curlimages/curl --target=auditoria \
  -n tipsbank-auditoria --profile=netadmin \
  -- curl -m 5 http://10.110.102.200:8080/health/live

# Teste via DNS
kubectl debug -it auditoria-659555485f-hqzjc \
  --image=curlimages/curl --target=auditoria \
  -n tipsbank-auditoria \
  -- curl -m 5 http://api-contas.tipsbank-contas.svc.cluster.local.:8080/health/live
```

**Output:**
```
curl: (28) Connection timed out after 5002 milliseconds
curl: (28) Connection timed out after 5003 milliseconds
```

NetworkPolicy bloqueou o TCP:8080 — auditoria não está na whitelist de ingress do tipsbank-contas.

#### Critério 2 — transacoes ACESSA api-contas (200 esperado)

```bash
kubectl debug -it api-transacoes-d4cdd957b-pbhmw \
  --image=curlimages/curl --target=api-transacoes \
  -n tipsbank-transacoes --profile=netadmin \
  -- curl -m 5 http://10.110.102.200:8080/health/live
```

**Output:**
```
{"status":"ok"}
```

allow-transacoes-to-contas liberou o egress TCP:8080.

#### Critério 3 — pods NÃO acessam IPs externos (timeout esperado)

```bash

# MetalLB homelab geral
kubectl debug -it api-contas-65d86d5dc7-d6lt6 \
  --image=curlimages/curl --target=api-contas \
  -n tipsbank-contas --profile=netadmin \
  -- curl -m 5 http://192.168.3.100:5000
```

**Output:**
```
curl: (28) Connection timed out after 5002 milliseconds
curl: (28) Connection timed out after 5002 milliseconds
```

default-deny bloqueou egress para IPs externos não permitidos.

#### Smoke test — aplicação continua funcionando após as policies

```bash
curl -s -o /dev/null -w "%{http_code}" https://app.tipsbank.staypuff.info
```

**Output:**
```
200
```

Ingress → web → APIs: fluxo completo funcionando com zero-trust ativo.

**Problemas encontrados:**

Aqui os problemas foram bem ligados à ordem em que Kubernetes, kube-proxy e Calico tratam DNS e tráfego de rede.

| # | Problema | Causa | Solução |
|---|---|---|---|
| 1 | `curl: (6) Could not resolve host` com curlimages/curl | Alpine/musl + ndots:5 + 4 search domains: musl desiste antes do lookup absoluto | Trailing dot no FQDN (`svc.cluster.local.`) ou usar ClusterIP direto |
| 2 | DNS egress com `namespaceSelector: kube-system` bloqueava novos containers | Calico avalia antes do DNAT — query vai para ClusterIP `10.96.0.10`, não ao pod real do coredns | Regra DNS port-only (sem `to:`): `To: <any>` |
| 3 | `--profile=legacy` deprecated no kubectl debug | K8s depreciou o perfil legacy | Usar `--profile=netadmin` ou `--profile=general` |

O primeiro sintoma foi o `curlimages/curl` não resolver alguns nomes internos. A imagem usa Alpine/musl, e com `ndots:5` mais vários search domains o resolver pode desistir antes de fechar o lookup como esperado. Para tirar essa variável do teste, usei FQDN com ponto final (`svc.cluster.local.`) ou ClusterIP direto.

O segundo ponto foi mais importante para a NetworkPolicy: liberar DNS apenas com `namespaceSelector: kube-system` não funcionava de forma consistente, porque o Calico avalia a política antes do DNAT do kube-proxy. A requisição saía para o ClusterIP do DNS (`10.96.0.10`), não diretamente para o pod real do CoreDNS. A primeira solução funcional foi liberar porta 53 sem `to`, mas isso ainda era amplo demais para zero-trust.

Também atualizei o uso do `kubectl debug`, porque o perfil `legacy` já está deprecated. Passei a usar `--profile=netadmin` ou `--profile=general`, dependendo do teste.

#### Screenshots

![](<imagens/Captura de tela 2026-05-05 162258.png>)
*Smoke test pré-NP — app respondendo em https://app.tipsbank.staypuff.info*

![](<imagens/Captura de tela 2026-05-05 165348.png>)
*kubectl apply — allow-tipsbank-web.yaml criado*

![](<imagens/Captura de tela 2026-05-05 170413.png>)
*kubectl get networkpolicy — NetworkPolicies aplicadas*

![](<imagens/Captura de tela 2026-05-05 173301.png>)
*kubectl apply — allow-tipsbank-contas.yaml criado*

![](<imagens/Captura de tela 2026-05-05 180818.png>)
*Extrato -R\$ 0,01 — app funcional após NetworkPolicies*

![](<imagens/Captura de tela 2026-05-05 183110.png>)
*allow-tipsbank-auditoria.yaml (NFS ipBlock) + kubectl apply all*

![](<imagens/Captura de tela 2026-05-05 183630.png>)
*kubectl get deployments -A — todos os Deployments Running*

![](<imagens/Captura de tela 2026-05-05 191430.png>)
*kubectl debug auditoria — wget interno confirmando isolamento*

![](<imagens/Captura de tela 2026-05-05 195504.png>)
*curl auditoria→api-contas — bloqueado (zero-trust confirmado)*

#### Refinamento — Regra DNS restrita ao CoreDNS (2026-05-06)

**Motivação:** A implementação inicial usou regra DNS port-only (sem `to:`), porque foi o caminho que fez o DNS voltar a funcionar durante os testes com Calico. O problema é que isso ficava aberto demais para uma proposta zero-trust: qualquer pod poderia mandar tráfego na porta 53 para qualquer destino, bastando parecer uma query DNS. Em um ambiente bancário, isso é um risco real de exfiltração via DNS tunneling.

**O que mudou:** A regra `allow-dns-egress-*` foi endurecida nos 4 namespaces para:

```yaml
egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - port: 53
      protocol: UDP
    - port: 53
      protocol: TCP
```

**Por que funciona agora:** O problema anterior com `namespaceSelector: kube-system` sozinho era que o Calico avaliava a política antes do DNAT do kube-proxy, então a query ia para o ClusterIP `10.96.0.10`, e não para o pod real do CoreDNS. Com `namespaceSelector + podSelector`, a política passa a casar com os endpoints reais do CoreDNS usando o label `k8s-app: kube-dns`. Resultado: DNS continua funcionando, mas agora só pode ir para os pods CoreDNS. Isso fecha a brecha da regra por porta aberta.

**Manifestos atualizados:**
- `k8s/network-policies/allow-dns-egress-contas` (tipsbank-contas)
- `k8s/network-policies/allow-dns-egress-transacoes` (tipsbank-transacoes)
- `k8s/network-policies/allow-dns-egress-auditoria` (tipsbank-auditoria)
- `k8s/network-policies/allow-dns-egress-web` (tipsbank-web)

#### Screenshots (refinamento DNS — 2026-05-06)

![](<imagens/Captura de tela 2026-05-06 174455.png>)
*Manifesto DNS refinado — `namespaceSelector kube-system + podSelector k8s-app: kube-dns`*

![](<imagens/Captura de tela 2026-05-06 174858.png>)
*kubectl apply — NetworkPolicies DNS atualizadas em todos os 4 namespaces*

![](<imagens/Captura de tela 2026-05-06 174928.png>)
*Smoke test pós-refinamento — aplicação respondendo com regra DNS zero-trust mais restrita*

---

## Semana 3 — Resiliência e Observabilidade

> [!NOTE] Pendente

---

## Semana 4 — Compliance e Entrega Final

> [!NOTE] Pendente
