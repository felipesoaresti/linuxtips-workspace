---
tags: [tipsbank, evidencias, semana-1, dk8s]
created: 2026-04-24
updated: 2026-05-13
status: concluído
semana: 1
---

# TipsBank — Evidências Semana 1: Fundações

## Semana 1 — Fundações

### Etapa 1.1 — Entender a aplicação localmente

**Data de conclusão:** 2026-04-24

#### Objetivo segundo o MANUAL-ALUNO.md

Rodar o TipsBank localmente no `docker-compose`, entender o papel de cada serviço e comprovar o fluxo ponta a ponta da aplicação antes de levar qualquer coisa para Kubernetes.

#### Critérios de aceite do manual

- `curl http://localhost:8081/contas` retorna as contas seed sem expor `senha_hash`.
- Login retorna 200 com senha correta e 401 com senha incorreta.
- Uma transferência de R$ 100 muda o saldo das contas de origem e destino.
- O arquivo `/data/eventos-YYYY-MM-DD.jsonl` da auditoria recebe uma linha por transferência.
- A SPA em `localhost:8080` funciona ponta a ponta.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Contas seed sem `senha_hash` | **Atendido** | Output de `/contas` mostra as contas e não traz `senha_hash`. |
| Login 200/401 | **Atendido** | Há teste com senha `giropops` e teste com senha inválida retornando `credenciais invalidas`. |
| Transferência altera saldos | **Parcialmente atendido** | Há transferência concluída de R$ 100, mas sem evidência lado a lado do saldo antes/depois. |
| Evento JSONL na auditoria | **Parcialmente atendido** | Há evento consultado via `/eventos`; não há, nesta etapa, leitura direta do arquivo dentro do container local. |
| SPA ponta a ponta | **Atendido** | Screenshots mostram dashboard, transferência e auditoria no ambiente local. |

#### Teste 1 — Listar contas seed (sem `senha_hash`)

Primeiro validei se todos os serviços subiam localmente e se os endpoints básicos respondiam. Esse teste é simples, mas importante: antes de mexer em Kubernetes, imagem, ingress ou storage, a aplicação precisa estar coerente no ambiente local.

Também conferi a listagem de contas para garantir que o contrato público da API não expõe `senha_hash`. A senha fica do lado servidor; para o cliente só voltam dados operacionais da conta.

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

#### Teste 2 — Autenticação válida ou retorno 401

Aqui o objetivo foi validar os dois caminhos da autenticação: sucesso com credenciais conhecidas e falha controlada com senha inválida. O retorno positivo mostra os dados da conta autenticada; o retorno de erro não entrega detalhes sensíveis, só informa que as credenciais são inválidas.

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
#### Evento gravado na auditoria

Além do retorno HTTP, validei o comportamento de auditoria. Mesmo quando a tentativa de login falha, o evento precisa ser rastreável para análise posterior. Para um sistema financeiro, esse tipo de trilha é parte da história do incidente, não só um log bonitinho no terminal.

```
curl -X POST http://localhost:8081/login -H 'content-type: application/json' -d '{"documento":"12345678901","senha":"senha-errada-teste"}' | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    90  100    34  100    56    621   1024 --:--:-- --:--:-- --:--:--  1666
{
  "detail": "credenciais invalidas"
}

```

#### Teste 3 — Criar nova conta

Depois da autenticação, testei a criação de uma nova conta usando o endpoint da `api-contas`. O retorno confirma que a API persistiu o registro, gerou um `id` UUID e normalizou o saldo como valor decimal em string, evitando perda de precisão comum quando dinheiro é tratado como número de ponto flutuante.

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

#### Teste 4 — Transferência entre contas

Com contas disponíveis, validei o fluxo principal do TipsBank: transferência entre origem e destino. A resposta `status: concluida` confirma que a `api-transacoes` conseguiu conversar com a camada de contas e registrar a operação sem erro de integração.

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

#### Teste 5 — Evento gravado na auditoria (arquivo JSONL)

Por fim, conferi se a transferência apareceu na auditoria. Esse ponto fecha o ciclo da Semana 1: a ação do usuário não fica só no saldo das contas, ela também vira evento append-only em JSONL, um formato simples, fácil de inspecionar e bom para trilhas de auditoria no lab.

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

---

### Etapa 1.2 — Build Distroless + Trivy + Cosign

**Data de conclusão:** 2026-04-25

#### Objetivo segundo o MANUAL-ALUNO.md

Gerar quatro imagens publicadas em registry controlado, com APIs em base Distroless ou equivalente minimal/nonroot, `web` nonroot, scan limpo de HIGH/CRITICAL e assinatura Cosign verificável.

#### Critérios de aceite do manual

- `trivy image` retorna 0 HIGH e 0 CRITICAL nas 4 imagens.
- `cosign verify` passa nas 4 imagens.
- `docker inspect` mostra usuário final não-root: UID 65532 nas APIs e UID 101 no `web`.
- Tamanho final das imagens Python menor que 150 MB e `web` menor que 30 MB.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Trivy 0 HIGH/CRITICAL | **Atendido** | Resumo do scan mostra `Total: 0 (HIGH: 0, CRITICAL: 0)` para as 4 imagens. |
| Cosign verify | **Atendido** | Bloco de verificação mostra assinatura e digest das 4 imagens. |
| Usuário nonroot | **Atendido** | `docker inspect` mostra `User: 65532` nas APIs e `User: 101` no `web`. |
| Tamanho das imagens | **Pendente de evidência explícita** | O arquivo não mostra `docker images`/tamanho final das imagens. |

#### Observações de alinhamento com o manual

- O manual cita Google Distroless como caminho base e permite Wolfi/Chainguard se o Trivy ficar limpo. As evidências usam Chainguard/Wolfi nas APIs e `nginx-unprivileged` no `web`.

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
Os relatórios completos ficaram salvos nos diretórios de cada app. A `api-contas` foi usada como base do ajuste porque foi nela que apareceram os CVEs críticos no primeiro scan. Depois da troca da base e revisão das dependências, as quatro imagens ficaram sem vulnerabilidades HIGH ou CRITICAL.

felipestaypuff/tipsbank-api-contas:v1.0.0 (wolfi 20230201)
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

Depois do scan, assinei e verifiquei as imagens com Cosign. A verificação amarra a tag publicada ao digest esperado; assim, além de saber que a imagem foi escaneada, também dá para confirmar que o artefato consumido no deploy é exatamente o artefato assinado.

```bash

❯ cat cosign-todas.txt
File: cosign-todas.txt
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
#### Observações

O principal problema encontrado nessa parte foi na imagem da `api-contas`: o scan apontou dois CVEs `CRITICAL` relacionados a uma dependência Python (`pyyaml`). Por isso eu usei essa imagem como base do ajuste e migrei para Chainguard/Distroless até chegar no resultado com `0 HIGH` e `0 CRITICAL`.

Outro ponto importante foi o uso de `latest`. Mesmo a Chainguard mantendo as imagens atualizadas, usar `latest` direto deixa o build menos previsível, porque a base pode mudar sem eu perceber. Para evitar esse tipo de variação, eu validei o digest da imagem e fixei a referência no Dockerfile. Assim o build passa a usar exatamente a imagem testada e versionada junto com o projeto. Menos surpresa no build, menos drama no deploy.

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
*Inspeção da imagem — digest e layers*

---

---

### Etapa 1.3 — Cluster kubeadm

**Data de conclusão:** 2026-04-26

#### Objetivo segundo o MANUAL-ALUNO.md

Instalar um cluster kubeadm multi-node com 1 control-plane e 2 workers, containerd e CNI funcionando.

#### Critérios de aceite do manual

- 3 nodes `Ready`.
- Pods do `kube-system` em `Running`.
- `kubectl run nginx --image=nginx` agenda o pod em worker, sem remover o taint do control-plane.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| 3 nodes Ready | **Atendido** | `kubectl get nodes -o wide` mostra `tb-master1`, `tb-worker1` e `tb-worker2` Ready. |
| Pods kube-system Running | **Atendido** | `kubectl get pods -A -o wide` mostra componentes principais Running. |
| Pod nginx em worker | **Atendido** | Pod `nginx` aparece em `tb-worker2`; taint do control-plane segue `NoSchedule`. |

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

---

### Etapa 1.4 — Namespaces, Deployments e Services

**Data de conclusão:** 2026-04-28

#### Objetivo segundo o MANUAL-ALUNO.md

Subir APIs, frontend e Postgres em namespaces separados usando Deployments, Services e StatefulSet, ainda sem Ingress, validando via `port-forward`.

#### Critérios de aceite do manual

- Pods TipsBank em `Running` nos namespaces esperados.
- `port-forward` para `api-transacoes` permite transferência via API.
- `port-forward` para `web` abre a SPA com login funcionando.
- `imagePullSecrets` configurado quando o registry for privado.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Pods Running | **Atendido** | `kubectl get pods -A | grep tipsbank` mostra workloads da aplicação Running. |
| Transferência via API | **Atendido** | Transferência via `svc/api-transacoes` retorna `status: concluida`. |
| SPA via port-forward | **Atendido** | `curl` retorna HTML da SPA e há evidência de login no browser. |
| imagePullSecrets | **Não aplicável neste lab** | As imagens estão públicas no Docker Hub; por isso não foi necessário `imagePullSecret`. |

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

As imagens usadas no lab foram publicadas como públicas no Docker Hub (`felipestaypuff/tipsbank-*:v1.0.0`). Por isso, nenhum `imagePullSecret` foi necessário neste momento.

Se essas imagens fossem privadas, o caminho correto seria criar um secret do tipo `kubernetes.io/dockerconfigjson` e referenciá-lo nos `ServiceAccounts` ou diretamente nos Pods. Como o objetivo aqui era validar deploy, service discovery e comunicação entre os componentes, manter as imagens públicas deixou o fluxo mais direto.


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

---

### Etapa 1.5 — ConfigMap, Secret e pod multicontainer

**Data de conclusão:** 2026-04-28

#### Objetivo segundo o MANUAL-ALUNO.md

Transformar `api-transacoes` em Pod multicontainer com sidecar lendo log de arquivo compartilhado e mover configuração para ConfigMaps/Secrets.

#### Critérios de aceite do manual

- Pod de `api-transacoes` mostra 2 containers.
- `kubectl logs -c log-forwarder` mostra log estruturado da app.
- Nenhuma variável sensível aparece chapada no Deployment; valores vêm de `secretKeyRef` e `configMapKeyRef`.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| 2 containers | **Atendido** | `kubectl get all -A` mostra pods `api-transacoes` como `2/2 Running`. |
| Log do sidecar | **Atendido** | `kubectl logs -c log-forwarder` mostra log estruturado `bootstrap versao=v1`. |
| Secret/ConfigMap | **Atendido** | Extrato JSON mostra `DB_URL` vindo de Secret e URLs/versão/log level vindos de ConfigMap. |

#### Critério 1 — Pods com 2/2 containers Running

Nesta etapa a `api-transacoes` passou a ter dois containers no mesmo Pod: o container principal da aplicação e um sidecar `log-forwarder`. O `2/2 Running` confirma que os dois containers subiram e compartilham o mesmo ciclo de vida do Pod.

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

O sidecar fica lendo o arquivo de log gerado pela aplicação. Isso separa responsabilidade: a API continua focada em regra de negócio, enquanto o segundo container cuida do encaminhamento/observação dos logs. Para o lab, o `tail` em BusyBox resolve; em produção, esse padrão poderia evoluir para Fluent Bit, Vector ou outro agente.

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

Também validei a separação entre configuração e segredo. URLs internas e versão da aplicação ficaram em `ConfigMap`; `DB_URL`, que contém credencial de banco, ficou em `Secret`. O Deployment passa a referenciar as chaves, sem deixar valor sensível chapado no manifesto.

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

---

### Etapa 1.6 — PV NFS para a auditoria

**Data de conclusão:** 2026-04-29

#### Objetivo segundo o MANUAL-ALUNO.md

Usar PV/PVC NFS RWX para a auditoria, permitindo que múltiplas réplicas escrevam/leiam o mesmo conjunto de eventos em `/data`.

#### Critérios de aceite do manual

- `kubectl get pv,pvc -A` mostra PV Bound ao PVC correto.
- Dois pods da auditoria listam os mesmos arquivos em `/data`.
- Após 100 transferências, o total de linhas bate com os eventos disparados.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| PV/PVC Bound | **Atendido** | `kubectl get pv,pvc` mostra `auditoria-pvc` Bound ao PV NFS. |
| Mesmos arquivos entre pods | **Atendido com adaptação** | Como a imagem é Distroless, a listagem foi feita com `python3` e `kubectl debug`, não com `ls`. |
| 100 transferências | **Atendido** | `wc -l` mostra 101 linhas: 100 do loop + 1 teste manual já documentado. |

#### Observações de alinhamento com o manual

- O manual pede `ls /data`, mas a imagem Distroless não tem `ls`; a evidência usa método equivalente e explica o motivo.

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

#### Observações

Para validar o conteúdo do PV, primeiro usei um pod de debug com imagem `busybox` e criei um arquivo em `/data`. Depois confirmei que os pods da auditoria enxergavam o mesmo arquivo. Isso prova o comportamento RWX do volume NFS: múltiplas réplicas conseguem ler e escrever no mesmo armazenamento compartilhado.

Todos os containers da aplicação foram criados com usuário nonroot, o que é uma boa prática de segurança. Isso não bloqueia escrita no PV quando o volume está com permissões corretas. O ponto importante é combinar usuário do container, permissões do volume e `fsGroup`, para que a aplicação escreva onde precisa sem rodar como root.

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

Como a imagem da auditoria é Distroless, ela não traz shell nem utilitários como `ls` e `cat`. Em vez de alterar a imagem só para depurar, usei ephemeral container com `kubectl debug`. O acesso via `/proc/1/root/data` permite inspecionar o filesystem do container alvo sem comprometer a proposta da imagem mínima.

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
