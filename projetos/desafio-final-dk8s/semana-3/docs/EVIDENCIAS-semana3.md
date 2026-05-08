---
tags: [tipsbank, evidencias, semana-3, dk8s]
created: 2026-05-07
updated: 2026-05-07
status: em-andamento
semana: 3
---

# TipsBank — Evidências Semana 3: Resiliência e Observabilidade

---

## Semana 3 — Resiliência e Observabilidade

### Etapa 3.1 — Probes Completas

**Data de conclusão:** 2026-05-07

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
