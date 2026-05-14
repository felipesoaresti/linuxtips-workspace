---
tags: [tipsbank, evidencias, semana-3, dk8s]
created: 2026-05-07
updated: 2026-05-13
status: concluído
semana: 3
---

# TipsBank — Evidências Semana 3: Resiliência, Scheduling, Autoscaling e Observabilidade

## Semana 3 — Resiliência, Scheduling, Autoscaling e Observabilidade

### Etapa 3.1 — Probes Completas

**Data de conclusão:** 2026-05-07

#### Objetivo segundo o MANUAL-ALUNO.md

Configurar probes corretas nas APIs, no `web` e no Postgres, e validar reinício automático por liveness.

#### Critérios de aceite do manual

- `kubectl describe pod` mostra probes configuradas.
- `kubectl get events` mostra ciclo de falha/restart quando o processo é morto.
- APIs não entram em CrashLoopBackOff durante deploy normal; startup probe dá tempo suficiente para subir.

### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Probes configuradas | **Atendido** | Descrições mostram startup/liveness/readiness nas APIs e exec probes no Postgres. |
| Eventos de restart | **Atendido** | Eventos mostram Unhealthy, BackOff, Created e Started após `kill 1`. |
| Deploy normal sem falha | **Parcialmente atendido** | Rollouts concluídos; `CrashLoopBackOff` aparece apenas no teste proposital de liveness. |

Nesta etapa eu tratei saúde da aplicação como contrato operacional. A ideia foi separar claramente três perguntas: o container já terminou de subir? Ele continua vivo? Ele está pronto para receber tráfego? Parece detalhe, mas é isso que evita mandar requisição para pod meio acordado ou manter pod quebrado fingindo normalidade.

**Setup:**
- Probes configuradas em todos os 5 componentes: api-contas, api-transacoes, auditoria, web (nginx), postgres StatefulSet
- api-contas, api-transacoes, auditoria: 3 probes (startupProbe + livenessProbe + readinessProbe) via httpGet
- web: 2 probes (livenessProbe + readinessProbe) via httpGet em `/healthz` — sem startupProbe (nginx sobe rápido)
- postgres: 2 probes (livenessProbe + readinessProbe) via exec `pg_isready -U tipsbank`
- Teste de liveness validado: `kill 1` no processo principal → kubelet reinicia o container automaticamente
- Init containers funcionando como dependency gates (api-transacoes aguarda postgres + api-contas; web aguarda os 3 serviços)

---

#### Critério 1 — Endpoints health das APIs funcionando (via `kubectl debug`)

Validação direta dentro do container via ephemeral container busybox, necessário pois as imagens são Distroless (sem shell).

Como as imagens são mínimas, o caminho correto não foi "instalar shell na imagem" só para depurar. Usei ephemeral container com BusyBox mirando o container principal, mantendo a imagem de produção enxuta e ainda assim conseguindo testar os endpoints por dentro do Pod.

```bash
k debug -it api-contas-6f58f96b9f-49rl4 \
  --image busybox \
  --target=api-contas \
  -n tipsbank-contas \
  --profile=sysadmin -- sh
```

**Output:**

```
Targeting container "api-contas".
Defaulting debug container name to debugger-wwt48.

/ # wget -qO- http://localhost:8080/health/live
{"status":"ok"}
/ # wget -qO- http://localhost:8080/health/ready
{"status":"ready"}
```

---

#### Critério 2 — api-contas com 3 probes configuradas

```bash
k apply -f k8s/tipsbank-contas/contas-deployment.yaml
k rollout status deployment -n tipsbank-contas api-contas
k describe -n tipsbank-contas deployments.apps api-contas
```

**Output (`k rollout status`):**

```
deployment "api-contas" successfully rolled out
```

**Output (`k describe`) — probes:**

```
    Liveness:   http-get http://:8080/health/live delay=0s timeout=3s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8080/health/ready delay=0s timeout=3s period=5s #success=1 #failure=3
    Startup:    http-get http://:8080/health/startup delay=0s timeout=1s period=5s #success=1 #failure=30
```

**Output (`k describe`) — rollout events:**

```
Events:
  Normal  ScalingReplicaSet  api-contas-c574fcd6b from 0 to 1
  Normal  ScalingReplicaSet  api-contas-6f58f96b9f from 2 to 1
  Normal  ScalingReplicaSet  api-contas-c574fcd6b from 1 to 2
  Normal  ScalingReplicaSet  api-contas-6f58f96b9f from 1 to 0
```

**Manifest (`k8s/tipsbank-contas/contas-deployment.yaml`) — trecho das probes:**

```yaml
          startupProbe:
            httpGet:
              path: /health/startup
              port: 8080
            failureThreshold: 30
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 0
            timeoutSeconds: 3
            periodSeconds: 10
            successThreshold: 1
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 0
            timeoutSeconds: 3
            periodSeconds: 5
            successThreshold: 1
            failureThreshold: 3
```

---

#### Critério 3 — api-transacoes com 3 probes + sidecar log-forwarder

```bash
k delete -f k8s/tipsbank-transacoes/transacoes-deployment-v2.yaml
k apply -f k8s/tipsbank-transacoes/transacoes-deployment.yaml
k rollout status deployment/api-transacoes -n tipsbank-transacoes
k describe -n tipsbank-transacoes deployments.apps api-transacoes
```

**Output (`k describe`) — probes:**

```
    Liveness:   http-get http://:8080/health/live delay=0s timeout=3s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8080/health/ready delay=0s timeout=3s period=5s #success=1 #failure=3
    Startup:    http-get http://:8080/health/startup delay=0s timeout=1s period=5s #success=1 #failure=30
```

Obs: container `log-forwarder` (sidecar busybox com `tail -F /var/log/app/app.log`) sem probe — não expõe endpoint.

---

#### Critério 4 — auditoria com 3 probes (3 réplicas, NFS RWX)

```bash
k apply -f k8s/tipsbank-auditoria/auditoria-deployment.yaml
k rollout status deployment/auditoria -n tipsbank-auditoria
k describe -n tipsbank-auditoria deployments.apps auditoria
```

**Output (`k describe`) — probes:**

```
    Liveness:   http-get http://:8080/health/live delay=0s timeout=3s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8080/health/ready delay=0s timeout=3s period=5s #success=1 #failure=3
    Startup:    http-get http://:8080/health/startup delay=0s timeout=1s period=5s #success=1 #failure=30
```

**Output (`k describe`) — rollout events (3 réplicas):**

```
Events:
  Normal  ScalingReplicaSet  auditoria-7fd5c4f477 from 0 to 1
  Normal  ScalingReplicaSet  auditoria-86d479b57b from 3 to 2
  Normal  ScalingReplicaSet  auditoria-7fd5c4f477 from 1 to 2
  Normal  ScalingReplicaSet  auditoria-86d479b57b from 2 to 1
  Normal  ScalingReplicaSet  auditoria-7fd5c4f477 from 2 to 3
  Normal  ScalingReplicaSet  auditoria-86d479b57b from 1 to 0
```

---

#### Critério 5 — web (nginx-unprivileged) com liveness + readiness + 3 init containers

```bash
k apply -f k8s/tipsbank-web/web-deployment.yaml
k rollout status deployment/web -n tipsbank-web
k describe -n tipsbank-web deployment web
```

**Output (`k describe`) — probes:**

```
    Liveness:   http-get http://:8080/healthz delay=5s timeout=1s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8080/healthz delay=5s timeout=1s period=5s #success=1 #failure=3
```

**Output (`k describe`) — init containers:**

```
  Init Containers:
   init-contas:
    Image: busybox:1.36
    Command: until wget -q --spider http://api-contas.tipsbank-contas.svc.cluster.local:8080/health/live; ...
   init-transacoes:
    Image: busybox:1.36
    Command: until wget -q --spider http://api-transacoes.tipsbank-transacoes.svc.cluster.local:8080/health/live; ...
   init-auditoria:
    Image: busybox:1.36
    Command: until wget -q --spider http://auditoria.tipsbank-auditoria.svc.cluster.local:8080/health/live; ...
```

**Manifest (`k8s/tipsbank-web/web-deployment.yaml`) — trecho das probes:**

```yaml
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3
```

---

#### Critério 6 — Postgres (StatefulSet) com exec probe `pg_isready`

```bash
k apply -f k8s/tipsbank-contas/postgres-statefull.yaml
k describe -n tipsbank-contas statefulsets.apps postgres
```

**Output (`k describe`) — probes:**

```
    Liveness:   exec [pg_isready -U tipsbank] delay=30s timeout=3s period=10s #success=1 #failure=3
    Readiness:  exec [pg_isready -U tipsbank] delay=5s timeout=3s period=5s #success=1 #failure=3
```

**Output (`k describe`) — eventos de restart controlado:**

```
Events:
  Normal  SuccessfulDelete  statefulset-controller  Delete Pod postgres-0 in StatefulSet postgres successful
  Normal  SuccessfulCreate  statefulset-controller  Create Pod postgres-0 in StatefulSet postgres successful
```

**Manifest (`k8s/tipsbank-contas/postgres-statefull.yaml`) — trecho das probes:**

```yaml
          livenessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - tipsbank
            initialDelaySeconds: 30
            timeoutSeconds: 3
            periodSeconds: 10
            successThreshold: 1
            failureThreshold: 3
          readinessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - tipsbank
            initialDelaySeconds: 5
            timeoutSeconds: 3
            periodSeconds: 5
            successThreshold: 1
            failureThreshold: 3
```

---

#### Critério 7 — Teste liveness: `kill 1` → reinício automático pelo kubelet

Validação de que a livenessProbe detecta a morte do processo principal e o kubelet reinicia o container.

Esse foi o teste mais direto da liveness: matar o processo principal e observar se o kubelet assume a recuperação. O pod passar por `NotReady`, `CrashLoopBackOff` e voltar para `Running` com `RESTARTS` incrementado confirma que a plataforma detectou a falha e reiniciou o container sem intervenção manual.

```bash
# Debug com ephemeral container para acessar namespaces do pod Distroless
k debug -it api-transacoes-f96d7c44d-6f8fx \
  --image busybox \
  --target=api-transacoes \
  -n tipsbank-transacoes \
  --profile=sysadmin -- sh

/ # kill 1
/ # exit

# Observar transições de estado
k get pod -n tipsbank-transacoes -w
```

**Output (`k get pod -w`) — ciclo completo de reinício:**

```
NAME                             READY   STATUS             RESTARTS      AGE
api-transacoes-f96d7c44d-6f8fx   2/2     Running            2 (40s ago)   126m
api-transacoes-f96d7c44d-6f8fx   1/2     NotReady           2 (58s ago)   127m
api-transacoes-f96d7c44d-6f8fx   1/2     CrashLoopBackOff   2 (4s ago)    127m
api-transacoes-f96d7c44d-6f8fx   1/2     Running            3 (24s ago)   127m
api-transacoes-f96d7c44d-6f8fx   2/2     Running            3 (29s ago)   127m
```

**Output (`k get events -n tipsbank-transacoes`) — eventos registrados:**

```
Normal    Pulled      Container image already present on machine
Normal    Created     Container created
Normal    Started     Container started
Warning   Unhealthy   Readiness probe failed: HTTP probe failed with statuscode: 503
Warning   BackOff     Back-off restarting failed container api-transacoes
Warning   Unhealthy   Readiness probe failed: dial tcp 10.244.209.242:8080: connection refused
Normal    Pulled      Successfully pulled image "busybox" in 847ms
Normal    Created     Container created
Normal    Started     Container started
```

Confirmação: pod voltou a `2/2 Running` com `RESTARTS: 3` — livenessProbe funcionando corretamente.

---

#### Screenshots — Semana 3.1

![](<imagens/Captura de tela 2026-05-07 194828.png>)
*19:48 — `kubectl debug` na api-contas: validação dos endpoints `/health/live` e `/health/ready` dentro do container Distroless via ephemeral busybox*

---

![](<imagens/Captura de tela 2026-05-07 195900.png>)
*19:59 — VS Code com `contas-deployment.yaml` aberto mostrando as probes no manifest + segundo debug container validando os endpoints*

---

![](<imagens/Captura de tela 2026-05-07 201226.png>)
*20:12 — `k describe -n tipsbank-contas deployments.apps api-contas`: 3 probes configuradas (Liveness, Readiness, Startup) + eventos do rolling update concluído (revision 8)*

---

![](<imagens/Captura de tela 2026-05-07 201823.png>)
*20:18 — `k describe -n tipsbank-auditoria deployments.apps auditoria`: 3 probes + rolling update das 3 réplicas concluído com PVC NFS (auditoria-pvc)*

---

![](<imagens/Captura de tela 2026-05-07 202916.png>)
*20:29 — `k describe -n tipsbank-transacoes deployments.apps api-transacoes`: 3 probes no container principal + sidecar log-forwarder + 2 init containers (init-postgres + init-api-contas)*

---

![](<imagens/Captura de tela 2026-05-07 221323.png>)
*22:13 — `k apply -f ../tipsbank-web/web-deployment.yaml` + describe do web: 3 init containers aguardando todos os upstreams (api-contas, api-transacoes, auditoria) via FQDN inter-namespace*

---

![](<imagens/Captura de tela 2026-05-07 221648.png>)
*22:16 — `k describe -n tipsbank-web deployment web` completo: init-contas + init-transacoes + init-auditoria + liveness + readiness para `/healthz` (revision 11)*

---

![](<imagens/Captura de tela 2026-05-07 222252.png>)
*22:22 — `k apply -f postgres-statefull.yaml` + `k describe statefulsets.apps postgres`: probes com exec `pg_isready -U tipsbank` (liveness: delay=30s, readiness: delay=5s) + evento de recreação do pod*

---

![](<imagens/Captura de tela 2026-05-07 223512.png>)
*22:35 — Múltiplas sessões de `k debug ... --profile=sysadmin -- sh` com `kill 1`: pod incrementando RESTARTS, confirmando que o kubelet está reiniciando o container via livenessProbe*

---

![](<imagens/Captura de tela 2026-05-07 223554.png>)
*22:35 — `k get pod -n tipsbank-transacoes -w`: pod `api-transacoes-f96d7c44d-6f8fx` passando por `CrashLoopBackOff` → `Running` após múltiplos kill 1 (RESTARTS: 2 e depois 3)*

---

![](<imagens/Captura de tela 2026-05-07 223804.png>)
*22:38 — `k get events -n tipsbank-transacoes` + `k get pod -n tipsbank-transacoes -w`: ciclo completo de eventos — BackOff, Unhealthy (Readiness 503), Pulled, Created, Started — livenessProbe funcionando em produção*

---

---

### Etapa 3.2 — Rollout Strategy e Rollback

**Data de conclusão:** 2026-05-08

#### Objetivo segundo o MANUAL-ALUNO.md

Definir estratégia de rollout explícita na `api-transacoes`, simular release quebrada e comprovar rollback sem derrubar tráfego.

#### Critérios de aceite do manual

- Rollout quebrado não derruba tráfego.
- `kubectl rollout history` mostra pelo menos 3 revisões.
- `kubectl rollout undo` restaura versão e pod fica Ready.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Tráfego preservado | **Atendido** | Endpoint segue `HTTP/2 200` enquanto pod novo está em `ImagePullBackOff`. |
| Histórico | **Atendido** | Histórico mostra 6 revisões. |
| Rollback | **Atendido** | Revisão restaurada para `v1.1.0` com pods `2/2 Running`. |

Aqui o objetivo foi validar uma release ruim sem derrubar o serviço. Configurei o rollout para manter disponibilidade (`maxUnavailable: 0`) e forcei uma versão quebrada. O resultado esperado era simples: pod novo falha, pods antigos continuam atendendo, tráfego segue 200 e o rollback volta para a versão boa.

**Setup:**
- `revisionHistoryLimit: 5` e `strategy.rollingUpdate.maxSurge: 1, maxUnavailable: 0` adicionados ao `api-transacoes`
- Deploy de versão quebrada (`v1.9.9`) para simular bad release — pod ficou `1/2 ImagePullBackOff`
- Comprovação de zero downtime durante rollout travado via curl e browser
- Rollback via `kubectl rollout undo` → revisão restaurada com `v1.1.0`

---

#### Critério 1 — Pods durante rollout quebrado (maxUnavailable: 0 funcionando)

O pod novo ficou preso em `ImagePullBackOff`, mas os dois pods antigos permaneceram `Running`. Isso mostra que o Deployment não sacrificou capacidade saudável para colocar uma versão quebrada no ar.

```
NAME                              READY   STATUS             RESTARTS   AGE
api-transacoes-5cb7cc9b8b-l5fsp   2/2     Running            0          13m
api-transacoes-5cb7cc9b8b-sh8hm   2/2     Running            0          13m
api-transacoes-d56bff9bc-k7n8g    1/2     ImagePullBackOff   0          70s
```

2 pods velhos (`v1.1.0`) permanecem `Running`. Pod novo (`v1.9.9`) em `ImagePullBackOff`. `1/2` = log-forwarder iniciou OK, api-transacoes falhou ao puxar `v1.9.9`.

---

#### Critério 2 — Tráfego mantido durante rollout quebrado

Mesmo com release ruim em andamento, o endpoint continuou respondendo. Essa é a parte que importa para quem usa o sistema: rollout pode falhar, mas a aplicação não precisa cair junto.

```
HTTP/2 200
{"status":"ok","version":"v1"}
```

HTTP/2 200 confirmado via curl e browser enquanto o pod `v1.9.9` estava em `ImagePullBackOff`.

---

#### Critério 3 — kubectl rollout history ≥ 3 revisões

```
REVISION  CHANGE-CAUSE
7         <none>
8         <none>
9         <none>
10        <none>
12        <none>
13        <none>
```

6 revisões visíveis. Revisão 12 = `v1.9.9` (quebrada). Revisão 13 = `v1.1.0` (restaurada via undo).

---

#### Critério 4 — rollout undo: pod Ready com versão restaurada

Revisão 13 = `felipestaypuff/tipsbank-api-transacoes:v1.1.0` com todos os pods `2/2 Running`.

---

#### Screenshots — Semana 3.2

![](<imagens/Captura de tela 2026-05-08 121923.png>)
*12:19 — VS Code com `transacoes-deployment.yaml`: `revisionHistoryLimit: 5` e `strategy.rollingUpdate.maxSurge: 1, maxUnavailable: 0` visíveis no manifest + terminal com `kubectl rollout history` antes (revisions 1–11) e depois do `k apply` (revisions 6–11)*

---

![](<imagens/Captura de tela 2026-05-08 125335.png>)
*12:53 — Browser em `api.tipsbank.staypuff.info/transacoes/health/live` retornando `{"status":"ok","version":"v1"}` enquanto o pod v1.9.9 estava em `ImagePullBackOff` — prova do zero downtime com `maxUnavailable: 0`*

---

![](<imagens/Captura de tela 2026-05-08 125417.png>)
*12:54 — VS Code com manifest (seção `strategy` visível) + terminal com `curl` mostrando health/live respondendo `{"status":"ok","version":"v1"}` durante o rollout travado*

---

---

### Etapa 3.3 — Affinity, AntiAffinity, Taints e Tolerations

**Data de conclusão:** 2026-05-10

#### Objetivo segundo o MANUAL-ALUNO.md

Usar anti-affinity, taints e tolerations para espalhar réplicas e isolar workloads sensíveis.

#### Critérios de aceite do manual

- Postgres primary e replica em nodes diferentes.
- Pods de API sem toleration não vão para node com taint.
- `kubectl describe node` confirma o taint.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Primary/replica separados | **Atendido** | `postgres-0` em `tb-worker2` e `postgres-replica-0` em `tb-worker1`. |
| APIs fora do node tainted | **Atendido** | Filtro por `tb-worker2` mostra apenas `postgres-0`. |
| Taint confirmado | **Atendido** | `describe node` mostra `compliance=strict:NoSchedule`. |

Nesta etapa eu mexi no scheduler: espalhar réplicas, isolar node com taint e permitir que apenas workloads específicos tolerem esse isolamento. É uma camada de resiliência e governança: não basta ter três nodes, é preciso dizer ao Kubernetes como usar esses nodes.

**Setup:**
- `podAntiAffinity preferred` adicionado a todos os Deployments (`api-contas`, `api-transacoes`, `auditoria`, `web`) com `topologyKey: kubernetes.io/hostname` — réplicas espalhadas entre nodes
- Taint `compliance=strict:NoSchedule` aplicado no `tb-worker2` + label `compliance=strict`
- `postgres-statefull.yaml`: `nodeAffinity preferred` (prefere node com label `compliance=strict`) + toleration `compliance=strict:NoSchedule`
- `postgres-statefull-replica.yaml`: `podAntiAffinity required` + toleration `compliance=strict:NoSchedule`
- **Bug corrigido durante implementação**: manifest inicial tinha `podAffinity` (em vez de `podAntiAffinity`) + `topologyKey: kubernetes.io/name` (label inexistente) → pod ficou em `Pending` com `0/3 nodes available: 2 node(s) didn't match pod affinity rules`. Fix: delete StatefulSet + PVC, corrigir para `podAntiAffinity` + `topologyKey: kubernetes.io/hostname`, reaplicar.

---

#### Critério 1 — Primary e replica em nodes diferentes

O banco primário e a réplica ficaram em nodes diferentes. Isso reduz risco de perder os dois ao mesmo tempo em uma falha de node e confirma que a `podAntiAffinity` obrigatória da réplica está funcionando.

```bash
kubectl get pods -o wide -n tipsbank-contas | grep postgres
```

**Output:**

```
postgres-0           1/1     Running   0          15h     10.244.247.61    tb-worker2   <none>           <none>
postgres-replica-0   1/1     Running   0          2m      10.244.205.214   tb-worker1   <none>           <none>
```

`postgres-0` (primary) em `tb-worker2` — node com taint `compliance=strict:NoSchedule`, tolerado pelo pod.
`postgres-replica-0` em `tb-worker1` — forçado pelo `requiredDuringSchedulingIgnoredDuringExecution` podAntiAffinity que proíbe co-agendamento com pods `app: postgres`.

---

#### Critério 2 — Pods de API sem toleration não vão para node com taint

```bash
kubectl get pods -o wide -A | grep tipsbank | grep tb-worker2
```

**Output:**

```
tipsbank-contas   postgres-0   1/1   Running   0   15h   10.244.247.61   tb-worker2   <none>   <none>
```

Apenas `postgres-0` (com toleration `compliance=strict:NoSchedule`) está em `tb-worker2`. Nenhum pod de API chegou ao node isolado.

---

#### Critério 3 — Taint confirmado no node

```bash
kubectl describe node tb-worker2 | grep -A 3 Taints
```

**Output:**

```
Taints:             compliance=strict:NoSchedule
```

---

#### Screenshots — Semana 3.3

![](<imagens/Captura de tela 2026-05-10 080601.png>)
*08:06 — VS Code com `postgres-statefull-replica.yaml` (podAntiAffinity + topologyKey: kubernetes.io/hostname visíveis) + terminal mostrando: erro inicial de scheduling (`0/3 nodes available: 2 node(s) didn't match pod affinity rules`), delete do StatefulSet + PVC, recreate e estado final com `postgres-0` em `tb-worker2` e `postgres-replica-0` em `tb-worker1`*

---

---

### Etapa 3.4 — Resources, Limits e QoS

**Data de conclusão:** 2026-05-11

#### Objetivo segundo o MANUAL-ALUNO.md

Definir requests/limits em 100% dos containers para evitar BestEffort e tornar consumo previsível.

#### Critérios de aceite do manual

- Nenhum pod com `QoSClass: BestEffort`.
- `kubectl top pod` mostra uso real depois do Metrics Server.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Zero BestEffort | **Atendido** | Todos os pods listados aparecem com `QoS Class: Burstable`. |
| kubectl top pod | **Pendente de evidência explícita** | O arquivo não mostra output de `kubectl top pod`. |

Aqui a aplicação deixou de ser "BestEffort". Definir `requests` e `limits` dá ao scheduler informação real para alocar os Pods e dá ao kubelet limites claros para CPU e memória. Não é tuning final de produção, mas já tira o ambiente daquele modo freestyle perigoso.

**Setup:**
- `resources.requests` e `resources.limits` adicionados a todos os containers principais e sidecars
- api-contas (main): `cpu: 100m→500m / memory: 128Mi→256Mi`
- api-transacoes (main): `cpu: 100m→500m / memory: 128Mi→256Mi`
- log-forwarder (sidecar): `cpu: 10m→50m / memory: 16Mi→32Mi`
- auditoria (main): `cpu: 100m→500m / memory: 128Mi→256Mi`
- web (main): `cpu: 100m→500m / memory: 128Mi→256Mi`
- postgres primary: `cpu: 250m→1000m / memory: 512Mi→1024Mi`
- postgres replica: `cpu: 200m→500m / memory: 256Mi→512Mi`
- Resultado: QoSClass **Burstable** em todos os 10 pods do tipsbank — zero BestEffort

---

#### Critério 1 — kubectl describe: resources e QoS da api-contas

```bash
k describe pod -n tipsbank-contas api-contas-6c4cbcc8b9-c449g
```

**Output (trechos relevantes):**

```
Init Containers:
  init-postgres:
    Image:   busybox:1.36
    Command: until nc -z postgres-service.tipsbank-contas.svc.cluster.local 5432; ...
    State:   Terminated  Reason: Completed  Exit Code: 0
    Ready:   True

Containers:
  api-contas:
    Image:  felipestaypuff/tipsbank-api-contas:v1.0.0
    Limits:
      cpu:     500m
      memory:  256Mi
    Requests:
      cpu:      100m
      memory:   128Mi
    Liveness:   http-get http://:8080/health/live delay=0s timeout=3s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8080/health/ready delay=0s timeout=3s period=5s #success=1 #failure=3
    Startup:    http-get http://:8080/health/startup delay=0s timeout=1s period=5s #success=1 #failure=30

QoS Class:  Burstable
```

---

#### Critério 2 — QoSClass Burstable em todos os pods (zero BestEffort)

O objetivo não era criar Pods `Guaranteed`, porque requests e limits iguais para tudo ficariam rígidos demais para este lab. `Burstable` é um bom meio-termo: o cluster reserva o mínimo necessário e ainda permite alguma elasticidade controlada.

```bash
k describe pod -n tipsbank-contas api-contas-6c4cbcc8b9-ppb45 | grep QoS
k describe pod -n tipsbank-contas postgres-0 | grep QoS
k describe pod -n tipsbank-contas postgres-replica-0 | grep QoS
k describe pod -n tipsbank-auditoria auditoria-69dffc8c99-f45jp | grep QoS
k describe pod -n tipsbank-auditoria auditoria-69dffc8c99-q6sfq | grep QoS
k describe pod -n tipsbank-transacoes api-transacoes-659558d96c-cnkcw | grep QoS
k describe pod -n tipsbank-transacoes api-transacoes-659558d96c-wk5hg | grep QoS
k describe pod -n tipsbank-web web-744bdd6fd8-bgw6j | grep QoS
k describe pod -n tipsbank-web web-744bdd6fd8-dm246 | grep QoS
```

**Output:**

```
QoS Class:                   Burstable
QoS Class:                   Burstable
QoS Class:                   Burstable
QoS Class:                   Burstable
QoS Class:                   Burstable
QoS Class:                   Burstable
QoS Class:                   Burstable
QoS Class:                   Burstable
QoS Class:                   Burstable
```

Todos os 10 pods (2×api-contas, 2×api-transacoes, 2×auditoria, 2×web, postgres-0, postgres-replica-0) com QoSClass: **Burstable**. Nenhum **BestEffort**.

---

#### Manifests — resources adicionados (trechos)

**`k8s/tipsbank-contas/contas-deployment.yaml`** — api-contas:

```yaml
      containers:
        - name: api-contas
          resources:
            limits:
              memory: "256Mi"
              cpu: "500m"
            requests:
              memory: "128Mi"
              cpu: "100m"
```

**`k8s/tipsbank-transacoes/transacoes-deployment.yaml`** — api-transacoes + log-forwarder:

```yaml
      containers:
        - name: api-transacoes
          resources:
            limits:
              memory: "256Mi"
              cpu: "500m"
            requests:
              memory: "128Mi"
              cpu: "100m"
        - name: log-forwarder
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 50m
              memory: 32Mi
```

**`k8s/tipsbank-auditoria/auditoria-deployment.yaml`** — auditoria:

```yaml
      containers:
        - name: auditoria
          resources:
            limits:
              memory: "256Mi"
              cpu: "500m"
            requests:
              memory: "128Mi"
              cpu: "100m"
```

**`k8s/tipsbank-web/web-deployment.yaml`** — web:

```yaml
      containers:
        - name: web
          resources:
            limits:
              memory: "256Mi"
              cpu: "500m"
            requests:
              memory: "128Mi"
              cpu: "100m"
```

**`k8s/tipsbank-contas/postgres-statefull.yaml`** — postgres primary:

```yaml
      containers:
        - name: postgres
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1024Mi
```

**`k8s/tipsbank-contas/postgres-statefull-replica.yaml`** — postgres replica:

```yaml
      containers:
        - name: postgres-replica
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

#### Screenshots — Semana 3.4

![](<imagens/Captura de tela 2026-05-11 171912.png>)
*17:19 — `kubectl describe pod api-contas-6c4cbcc8b9-c449g -n tipsbank-contas`: init container `init-postgres` (Terminated/Completed), container `api-contas` com Limits (cpu:500m, memory:256Mi) e Requests (cpu:100m, memory:128Mi) + 3 probes configuradas. QoS Class: Burstable*

---

![](<imagens/Captura de tela 2026-05-11 171926.png>)
*17:19 — Continuação do describe: NFS volume attached; describe dos pods de auditoria, transacoes e web — todos com QoSClass: Burstable. `kubectl get pods -A` mostrando todos os pods tipsbank em Running*

---

![](<imagens/Captura de tela 2026-05-11 172012.png>)
*17:20 — `kubectl apply` nos StatefulSets postgres primary e replica + eventos de criação (Container created/started). `kubectl get pods -A` com todos os 10 pods em 2/2 Running. `kubectl describe pod` confirmando QoSClass: Burstable no pod api-contas*

---

---

### Etapa 3.5 — Observabilidade: kube-prometheus-stack + Grafana

**Data de conclusão:** 2026-05-13

#### Objetivo segundo o MANUAL-ALUNO.md

Instalar kube-prometheus-stack, expor Grafana/Prometheus e coletar métricas reais das três APIs via ServiceMonitor.

#### Critérios de aceite do manual

- Prometheus UI mostra targets das 3 APIs como `UP`.
- Dashboard Grafana renderiza dados reais.
- Alertmanager UI funcional.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Targets das 3 APIs | **Parcialmente atendido** | Há 3 ServiceMonitors criados; evidência visual/textual de UP aparece para contas e auditoria. Falta explicitar `api-transacoes` UP. |
| Grafana com dados reais | **Atendido** | Screenshots e PromQL mostram métricas reais em dashboards/Explore. |
| Alertmanager UI | **Pendente de evidência explícita** | Pods do Alertmanager estão Running, mas não há evidência da UI funcional. |

#### Observações de alinhamento com o manual

- O manual diz que ServiceMonitor para `web` é opcional; o documento foca nas três APIs, como pedido obrigatório.

Para fechar a semana, instalei observabilidade de verdade com Prometheus, Alertmanager e Grafana. O foco não foi só abrir dashboard bonito: foi confirmar coleta real das APIs via `ServiceMonitor`, persistência dos componentes e liberação explícita nas NetworkPolicies para o scraping funcionar.

**Setup:**
- kube-prometheus-stack instalado via Helm no namespace `tipsbank-monitoring`
- Values customizados: Grafana com persistence NFS (`nfs-tp-data`, 5Gi), Ingress TLS cert-manager, senha `tipsbank@puff`
- Prometheus com retention 15d, storage NFS 20Gi, `serviceMonitorSelectorNilUsesHelmValues: false`
- Alertmanager com storage NFS 2Gi
- 3 ServiceMonitors criados: api-contas, api-transacoes, auditoria (label `release: kube-prometheus-stack`)
- NetworkPolicies de scraping aplicadas nos 3 namespaces de API

---

#### Critério 1 — Todos os pods do tipsbank-monitoring em Running

```bash
kubectl get pods -A | grep tipsbank-monitoring
```

**Output:**

```
tipsbank-monitoring   alertmanager-kube-prometheus-stack-alertmanager-0           2/2     Running   0               104m
tipsbank-monitoring   kube-prometheus-stack-grafana-5647658b96-5z4pg              3/3     Running   0               105m
tipsbank-monitoring   kube-prometheus-stack-kube-state-metrics-58474dc949-sbl78   1/1     Running   0               105m
tipsbank-monitoring   kube-prometheus-stack-operator-7d6bdd985b-llvkj             1/1     Running   0               105m
tipsbank-monitoring   kube-prometheus-stack-prometheus-node-exporter-5qmkw        1/1     Running   0               105m
tipsbank-monitoring   kube-prometheus-stack-prometheus-node-exporter-hwm8m        1/1     Running   0               105m
tipsbank-monitoring   kube-prometheus-stack-prometheus-node-exporter-jfftq        1/1     Running   0               105m
tipsbank-monitoring   prometheus-kube-prometheus-stack-prometheus-0               2/2     Running   0               104m
```

---

#### Critério 2 — ServiceMonitors das 3 APIs descobertos pelo Prometheus

```bash
kubectl get servicemonitors.monitoring.coreos.com -A | grep tipsbank
```

**Output:**

```
tipsbank-auditoria    api-auditoria-monitor     12m
tipsbank-contas       api-contas-monitor        12m
tipsbank-transacoes   api-transacoes-monitor    12m
```

---

#### Critério 3 — Prometheus UI mostra targets das APIs como UP

Targets verificados via `kubectl port-forward -n tipsbank-monitoring svc/kube-prometheus-stack-prometheus 9090:9090`:
- `serviceMonitor/tipsbank-contas/api-contas-monitor/0` → **2/2 up**
- `serviceMonitor/tipsbank-auditoria/api-auditoria-monitor/0` → **2/2 up**

NetworkPolicy `allow-prometheus-scrape-*` foi necessária — sem ela, targets ficavam DOWN com "context deadline exceeded".

Esse erro foi útil: ele provou que o zero-trust da Semana 2 estava ativo de verdade. O Prometheus só passou a coletar depois que recebeu permissão explícita para acessar as portas de métricas das APIs.

---

#### Critério 4 — Grafana acessível com dados reais

No Grafana, validei não só o login, mas também consultas PromQL com séries das APIs. Métrica subindo em `http_requests_total` confirma que os endpoints estão sendo raspados e que os dados chegaram até a camada de visualização.

Senha confirmada via secret:
```bash
kubectl get secret --namespace tipsbank-monitoring -l app.kubernetes.io/component=admin-secret \
  -o jsonpath="{.items[0].data.admin-password}" | base64 --decode ; echo
# Output: tipsbank@puff
```

PromQL funcionando no Explore:
```promql
rate(http_requests_total{namespace=~"tipsbank-.*"}[1m])
```

---

#### Screenshots — Semana 3.5

![](<imagens/Captura de tela 2026-05-13 171347.png>)
*17:13 — VS Code com `values-kube-prometheus-stack.yaml` aberto + terminal: `helm install kube-prometheus-stack` retornando `STATUS: deployed` + NOTES com instruções de acesso*

---

![](<imagens/Captura de tela 2026-05-13 171528.png>)
*17:15 — Terminal: `kubectl get pods -l "release=kube-prometheus-stack"` mostrando primeiros 5 pods Running (kube-state-metrics, operator, 3x node-exporter) + port-forward para Grafana*

---

![](<imagens/Captura de tela 2026-05-13 171705.png>)
*17:17 — Browser: tela de boas-vindas do Grafana ("Welcome to Grafana") acessado via port-forward na porta 3000 — instalação confirmada*

---

![](<imagens/Captura de tela 2026-05-13 171850.png>)
*17:18 — Terminal: senha recuperada `tipsbank@puff` via `kubectl get secret` + `kubectl get pods -A | grep tipsbank-monitoring` mostrando todos os 8 pods Running (alertmanager 2/2, grafana 3/3, prometheus 2/2, node-exporter x3)*

---

![](<imagens/Captura de tela 2026-05-13 190757.png>)
*19:07 — VS Code: `allow-prometheus-tipsbank-contas.yaml` + terminal: `kubectl get servicemonitors -A` mostrando `api-contas-monitor` + `kubectl describe servicemonitor api-contas-monitor` (Port: api-contas, Interval: 30s) + port-forward prometheus 9090*

---

![](<imagens/Captura de tela 2026-05-13 190853.png>)
*19:08 — Prometheus UI (localhost:9090) → Status → Target health: `serviceMonitor/tipsbank-contas/api-contas-monitor/0` aparece como UP (verde) — primeiro target tipsbank funcionando*

---

![](<imagens/Captura de tela 2026-05-13 191105.png>)
*19:11 — Prometheus UI: Target health completo — api-contas-monitor/0 UP + todos os targets kube-prometheus-stack visíveis*

---

![](<imagens/Captura de tela 2026-05-13 191539.png>)
*19:15 — Grafana: dashboard Kubernetes/Views/Pods filtrando namespace `tipsbank-contas` — CPU/Memory por container visível para api-contas e postgres com valores reais*

---

![](<imagens/Captura de tela 2026-05-13 192144.png>)
*19:21 — Grafana Explore: query `http_requests_total` filtrada por `namespace=~"tipsbank-.*"` — séries temporais ascendentes confirmam scraping ativo das APIs*

---

![](<imagens/Captura de tela 2026-05-13 192159.png>)
*19:21 — VS Code: NetworkPolicy + terminal: port-forward para prometheus 9090 e grafana 3000:80 com múltiplas conexões sendo tratadas*

---

![](<imagens/Captura de tela 2026-05-13 192745.png>)
*19:27 — Grafana Explore: `rate(http_requests_total{namespace=~"tipsbank-.*"}[1m])` — legenda com api-contas, paths /health/live, /health/ready, /health/startup confirmando métricas reais*

---

![](<imagens/Captura de tela 2026-05-13 195815.png>)
*19:58 — VS Code split: ServiceMonitor auditoria + api-contas lado a lado + terminal: apply dos 3 ServiceMonitors + `kubectl get servicemonitors -A | grep tipsbank` mostrando os 3 monitors criados*

---

![](<imagens/Captura de tela 2026-05-13 200706.png>)
*20:07 — Prometheus UI: auditoria DOWN (vermelho, "context deadline exceeded") + api-contas UP — demonstração de que NetworkPolicy bloqueava o scraping antes de ser aplicada*

---

![](<imagens/Captura de tela 2026-05-13 201827.png>)
*20:18 — VS Code split: NetworkPolicies auditoria + contas + terminal: apply das 3 NetworkPolicies de scraping + `kubectl get networkpolicies -A` confirmando todas as políticas ativas*

---

![](<imagens/Captura de tela 2026-05-13 202327.png>)
*20:23 — Prometheus UI: Target health **FINAL** — `serviceMonitor/tipsbank-auditoria/api-auditoria-monitor/0` **2/2 up**, `serviceMonitor/tipsbank-contas/api-contas-monitor/0` **2/2 up**, todos os targets UP (verde)*

---

---

### Etapa 3.6 — PrometheusRule com alertas de SLO

**Status:** Pendente de evidência neste arquivo.

#### Objetivo segundo o MANUAL-ALUNO.md

Criar quatro alertas críticos via PrometheusRule e provocar cada condição para comprovar disparo no Alertmanager.

#### Critérios de aceite do manual

- Os 4 alertas aparecem em `kubectl get prometheusrule -A`.
- Todos disparam quando a condição é provocada, com evidência no `EVIDENCIAS.md`.

#### Resultado

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| PrometheusRules criadas | **Pendente** | Não há output de `kubectl get prometheusrule -A`. |
| Alertas disparando | **Pendente** | Não há screenshot/output de Alertmanager com os alertas acionados. |

---

### Etapa 3.7 — HPA + Metrics Server + Locust stress test

**Status:** Pendente de evidência neste arquivo.

#### Objetivo segundo o MANUAL-ALUNO.md

Configurar Metrics Server, HPAs nas APIs e gerar carga com Locust para comprovar escala automática.

#### Critérios de aceite do manual

- `kubectl get hpa -A` mostra 3 HPAs com métricas ativas.
- Durante stress test, réplicas de `api-transacoes` sobem acima de 5.
- Taxa de erro no Locust fica abaixo de 1%.
- Após o teste, scaleDown retorna as réplicas em até 10 minutos.

#### Resultado

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| HPAs ativos | **Pendente** | Não há output de HPA. |
| Escala sob carga | **Pendente** | Não há evidência de Locust/HPA escalando. |
| Erro abaixo de 1% | **Pendente** | Não há relatório do Locust. |
| ScaleDown | **Pendente** | Não há evidência de retorno de réplicas. |

---

### Etapa 3.8 — DaemonSet de coleta

**Status:** Pendente de evidência neste arquivo.

#### Objetivo segundo o MANUAL-ALUNO.md

Criar um DaemonSet didático ou de coleta rodando em todos os workers, inclusive com toleration para node com taint.

#### Critérios de aceite do manual

- `kubectl get ds -A` mostra um DaemonSet com `DESIRED == CURRENT == READY` igual ao número de workers.

#### Resultado

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| DaemonSet em todos os workers | **Pendente** | Não há output de `kubectl get ds -A` para um DS próprio da etapa. |
