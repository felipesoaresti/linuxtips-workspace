---
tags: [tipsbank, evidencias, semana-3, dk8s]
created: 2026-05-07
updated: 2026-05-17
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

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Probes configuradas | **Atendido** | Descrições mostram startup/liveness/readiness nas APIs e exec probes no Postgres. |
| Eventos de restart | **Atendido** | Evidências mostram `NotReady`, incremento de `RESTARTS`, `Created` e `Started` após `kill 1` e nova tentativa com `kill -STOP 1`; neste cluster o evento literal `Killing` não foi emitido/capturado. |
| Deploy normal sem falha | **Atendido** | Rollouts normais concluíram; `CrashLoopBackOff` apareceu somente no teste controlado de `kill 1`, que era justamente a validação da liveness. |

#### Observações de alinhamento com o manual

- O manual pede `kubectl describe pod`; a evidência usa principalmente `kubectl describe deployment`, que mostra o mesmo template de probes aplicado aos pods, e complementa com `kubectl debug`, `kubectl get pod -w` e `kubectl get events`.
- O manual pede evento `Killing + Started`. Nas capturas salvas, o kubelet/runtime registrou `Pulled`, `Created` e `Started`, além do pod passar por `NotReady` e incrementar `RESTARTS`. O evento literal `Killing` não apareceu nem na tentativa adicional com `kill -STOP 1`, então a evidência aceita aqui é o ciclo observável de recriação/restart.
- O teste usou `kubectl debug` com BusyBox porque as imagens das APIs são Distroless e não têm shell para executar o `kill 1` diretamente com `kubectl exec`.

Nesta etapa eu tratei saúde da aplicação como contrato operacional. A ideia foi separar claramente três perguntas: o container já terminou de subir? Ele continua vivo? Ele está pronto para receber tráfego? Parece detalhe, mas é isso que evita mandar requisição para pod meio acordado ou manter pod quebrado fingindo normalidade.

**Setup:**
- Probes configuradas em todos os 5 componentes: api-contas, api-transacoes, auditoria, web (nginx), postgres StatefulSet
- api-contas, api-transacoes, auditoria: 3 probes (startupProbe + livenessProbe + readinessProbe) via httpGet
- web: 2 probes (livenessProbe + readinessProbe) via httpGet em `/healthz` — sem startupProbe (nginx sobe rápido)
- postgres: 2 probes (livenessProbe + readinessProbe) via exec `pg_isready -U tipsbank`
- Teste de reinício validado: `kill 1` no processo principal → kubelet reinicia o container automaticamente
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

#### Critério 7 — Teste de reinício: `kill 1` → restart automático pelo kubelet

Validação de que o pod recupera quando o processo principal morre e o kubelet reinicia o container.

Esse teste matou o PID 1 dentro do container principal e observou se o kubelet assumia a recuperação. O pod passar por `NotReady`, `CrashLoopBackOff` e voltar para `Running` com `RESTARTS` incrementado confirma que a plataforma reiniciou o container sem intervenção manual.

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

**Output (`k get events -n tipsbank-transacoes`) — eventos registrados no print salvo:**

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

Confirmação: pod voltou a `2/2 Running` com `RESTARTS: 3`. A recuperação automática está comprovada.

#### Critério 7.1 — Tentativa adicional para capturar `Killing` (2026-05-23)

Depois da primeira revisão, repeti o teste manualmente para tentar capturar o evento literal `Killing` pedido no manual. Foram feitas duas abordagens no mesmo pod `api-transacoes-776f74779b-bkrrq`:

- `kill 1`, encerrando o processo principal `python -m uvicorn`.
- `kill -STOP 1`, travando o processo principal, seguido de `kill 1`.

```bash
kubectl get pods -n tipsbank-transacoes -l app=api-transacoes

kubectl get events -n tipsbank-transacoes --watch \
  --field-selector involvedObject.name=api-transacoes-776f74779b-bkrrq

kubectl get pod -n tipsbank-transacoes api-transacoes-776f74779b-bkrrq -w

kubectl debug -it api-transacoes-776f74779b-bkrrq \
  -n tipsbank-transacoes \
  --image=busybox:1.36 \
  --target=api-transacoes \
  --profile=sysadmin \
  -- sh
```

**Output — processo principal e tentativa com `kill -STOP 1`:**

```
/ # ps
PID   USER     TIME  COMMAND
    1 65532     0:01 python -m uvicorn main:app --host 0.0.0.0 --port 8080
   13 root      0:00 sh
   19 root      0:00 ps
/ # kill -STOP 1
/ # ps
PID   USER     TIME  COMMAND
    1 65532     0:02 python -m uvicorn main:app --host 0.0.0.0 --port 8080
   13 root      0:00 sh
   20 root      0:00 ps
/ # kill 1
```

**Output — pod recreado/reiniciado:**

```
api-transacoes-776f74779b-bkrrq   1/2   NotReady   0                21h
api-transacoes-776f74779b-bkrrq   1/2   Running    1 (1s ago)      21h
api-transacoes-776f74779b-bkrrq   2/2   Running    1 (2s ago)      21h
api-transacoes-776f74779b-bkrrq   1/2   NotReady   1 (10m ago)     21h
api-transacoes-776f74779b-bkrrq   1/2   Running    2 (2s ago)      21h
api-transacoes-776f74779b-bkrrq   2/2   Running    2 (3s ago)      21h
```

**Output — eventos observados:**

```
Normal   Pulled    pod/api-transacoes-776f74779b-bkrrq   Container image "busybox:1.36" already present on machine and can be accessed by the pod
Normal   Created   pod/api-transacoes-776f74779b-bkrrq   Container created
Normal   Started   pod/api-transacoes-776f74779b-bkrrq   Container started
Normal   Pulled    pod/api-transacoes-776f74779b-bkrrq   Container image "felipestaypuff/tipsbank-api-transacoes:v2.0.0" already present on machine and can be accessed by the pod
Normal   Created   pod/api-transacoes-776f74779b-bkrrq   Container created
Normal   Started   pod/api-transacoes-776f74779b-bkrrq   Container started
```

Conclusão da tentativa adicional: mesmo forçando `STOP` no PID 1, o cluster registrou o ciclo como `Pulled`/`Created`/`Started` e o `RESTARTS` subiu de 0 para 1 e depois para 2. O evento literal `Killing` não apareceu nas evidências, mas o comportamento exigido pelo critério — kubelet reiniciar o container após falha manual do processo principal — foi comprovado.

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
*22:35 — Múltiplas sessões de `k debug ... --profile=sysadmin -- sh` com `kill 1`: pod incrementando RESTARTS, confirmando restart automático pelo kubelet*

---

![](<imagens/Captura de tela 2026-05-07 223554.png>)
*22:35 — `k get pod -n tipsbank-transacoes -w`: pod `api-transacoes-f96d7c44d-6f8fx` passando por `CrashLoopBackOff` → `Running` após múltiplos kill 1 (RESTARTS: 2 e depois 3)*

---

![](<imagens/Captura de tela 2026-05-07 223804.png>)
*22:38 — `k get events -n tipsbank-transacoes` + `k get pod -n tipsbank-transacoes -w`: eventos BackOff, Unhealthy (Readiness 503), Pulled, Created e Started; o evento Killing não aparece no print salvo*

---

![](<imagens/Captura de tela 2026-05-23 091120.png>)
*09:11 — tentativa adicional: `kubectl debug`, `ps` mostrando PID 1 como `python -m uvicorn` e execução de `kill 1`*

---

![](<imagens/Captura de tela 2026-05-23 091129.png>)
*09:11 — `kubectl get pod -w`: pod passa para `NotReady`, volta para `Running` e incrementa `RESTARTS` de 0 para 1*

---

![](<imagens/Captura de tela 2026-05-23 091138.png>)
*09:11 — `kubectl get events --watch`: eventos registrados como `Pulled`, `Created` e `Started`, sem evento literal `Killing`*

---

![](<imagens/Captura de tela 2026-05-23 092113.png>)
*09:21 — segunda tentativa: `kill -STOP 1` no processo principal, conferência com `ps` e encerramento posterior com `kill 1`*

---

![](<imagens/Captura de tela 2026-05-23 092127.png>)
*09:21 — `kubectl get pod -w`: nova transição para `NotReady` e `RESTARTS` subindo de 1 para 2*

---

![](<imagens/Captura de tela 2026-05-23 092135.png>)
*09:21 — `kubectl get events --watch`: nova sequência `Pulled`, `Created` e `Started`; o cluster não emitiu/capturou `Killing`*

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
- Deploy de versão quebrada (`v1.9.9`) via `k8s/tipsbank-transacoes/transacoes-deployment-quebrada.yaml` para simular bad release — pod ficou `1/2 ImagePullBackOff`
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
kubectl rollout history deployment/api-transacoes -n tipsbank-transacoes

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

```
kubectl rollout undo deployment/api-transacoes -n tipsbank-transacoes
deployment.apps/api-transacoes rolled back

k rollout history -n tipsbank-transacoes deployment api-transacoes --revision=13

Pod Template:
  Containers:
   api-transacoes:
    Image:      felipestaypuff/tipsbank-api-transacoes:v1.1.0
    Liveness:   http-get http://:8080/health/live delay=0s timeout=3s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8080/health/ready delay=0s timeout=3s period=5s #success=1 #failure=3
    Startup:    http-get http://:8080/health/startup delay=0s timeout=1s period=5s #success=1 #failure=30
```

Revisão 13 = `felipestaypuff/tipsbank-api-transacoes:v1.1.0` restaurada via `kubectl rollout undo`. O manual pede que o `rollout undo` volte a versão e deixe o pod Ready; a evidência combina o comando de rollback, o histórico com a revisão restaurada e os pods `2/2 Running` registrados após o retorno da versão boa.

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

#### Observações de alinhamento com o manual

- O manual permite que o segundo StatefulSet seja réplica real por streaming ou réplica didática. Aqui foi usado `postgres-replica` como StatefulSet separado didático, com o mesmo Secret e storage próprio.
- Os quatro Deployments com mais de uma réplica (`api-contas`, `api-transacoes`, `auditoria`, `web`) têm `podAntiAffinity preferredDuringSchedulingIgnoredDuringExecution` com `topologyKey: kubernetes.io/hostname`.
- Apenas os StatefulSets do Postgres têm toleration para `compliance=strict:NoSchedule`; os Deployments das APIs não têm essa toleration, então não são agendados no node isolado.

Nesta etapa eu mexi no scheduler: espalhar réplicas, isolar node com taint e permitir que apenas workloads específicos tolerem esse isolamento. É uma camada de resiliência e governança: não basta ter três nodes, é preciso dizer ao Kubernetes como usar esses nodes.

**Setup:**
- `podAntiAffinity preferred` adicionado aos manifestos `k8s/tipsbank-contas/contas-deployment.yaml`, `k8s/tipsbank-transacoes/transacoes-deployment.yaml`, `k8s/tipsbank-auditoria/auditoria-deployment.yaml` e `k8s/tipsbank-web/web-deployment.yaml` — réplicas espalhadas entre nodes
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

Esse é o taint exigido pelo manual no worker isolado. Como ele usa efeito `NoSchedule`, novos pods sem toleration não entram nesse node; pods já existentes só mudam de node depois de restart ou recriação.

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
| `kubectl top pod` | **Atendido** | Saída enviada em 2026-05-17 mostra CPU/memória reais para APIs, Postgres, web, monitoring, Locust e DaemonSet. |

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
- Resultado: QoSClass **Burstable** em todos os pods principais do TipsBank — zero BestEffort — e Metrics Server retornando uso real via `kubectl top pod`.

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

Todos os pods verificados (2×api-contas, 2×api-transacoes, 2×auditoria, 2×web, postgres-0, postgres-replica-0) com QoSClass: **Burstable**. Nenhum **BestEffort**.

---

#### Critério 3 — Metrics Server exibindo uso real com `kubectl top pod`

O segundo critério do manual pede evidência de consumo real depois do Metrics Server. A saída abaixo fecha essa parte: o cluster está retornando CPU e memória por pod, então os requests configurados já podem ser comparados com uso observado. Aqui não tem tuning fino ainda, mas já saiu do modo "no escuro".

```bash
kubectl top pod -A | grep tipsbank
```

**Output:**

```
tipsbank-auditoria    auditoria-69dffc8c99-f45jp                                  2m           39Mi
tipsbank-auditoria    auditoria-69dffc8c99-q6sfq                                  2m           39Mi
tipsbank-contas       api-contas-67dcb8b76c-fbfkm                                 3m           99Mi
tipsbank-contas       api-contas-67dcb8b76c-pb6nt                                 2m           99Mi
tipsbank-contas       postgres-0                                                  6m           32Mi
tipsbank-contas       postgres-replica-0                                          5m           25Mi
tipsbank-monitoring   alertmanager-kube-prometheus-stack-alertmanager-0           1m           31Mi
tipsbank-monitoring   kube-prometheus-stack-grafana-5647658b96-5z4pg              13m          368Mi
tipsbank-monitoring   kube-prometheus-stack-kube-state-metrics-58474dc949-sbl78   3m           21Mi
tipsbank-monitoring   kube-prometheus-stack-operator-7d6bdd985b-llvkj             4m           23Mi
tipsbank-monitoring   kube-prometheus-stack-prometheus-node-exporter-5qmkw        1m           10Mi
tipsbank-monitoring   kube-prometheus-stack-prometheus-node-exporter-hwm8m        1m           11Mi
tipsbank-monitoring   kube-prometheus-stack-prometheus-node-exporter-jfftq        1m           10Mi
tipsbank-monitoring   locust-94b7fdffb-v4hrq                                      1m           59Mi
tipsbank-monitoring   node-collector-6pnc5                                        0m           0Mi
tipsbank-monitoring   node-collector-zgw7q                                        0m           0Mi
tipsbank-monitoring   prometheus-kube-prometheus-stack-prometheus-0               21m          518Mi
tipsbank-transacoes   api-transacoes-659558d96c-cnkcw                             4m           107Mi
tipsbank-transacoes   api-transacoes-659558d96c-h7wfl                             4m           122Mi
tipsbank-transacoes   api-transacoes-659558d96c-wk5hg                             3m           107Mi
tipsbank-web          web-744bdd6fd8-bgw6j                                        1m           4Mi
tipsbank-web          web-744bdd6fd8-dm246                                        1m           4Mi
```

A leitura confirma que o Metrics Server está funcional e que os pods estão reportando uso real. Os pods `node-collector` aparecem com `0m/0Mi` porque rodam um loop leve de BusyBox; isso é esperado para um coletor didático praticamente ocioso.

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
| Targets das 3 APIs | **Atendido** | Após liberar egress do Prometheus para as APIs, `up{job=~"api-contas|api-transacoes|auditoria"}` mostra todos os 7 targets com valor `1`. |
| Grafana com dados reais | **Atendido** | Screenshots e PromQL mostram métricas reais em dashboards/Explore. |
| Alertmanager UI | **Atendido** | Port-forward para `localhost:9093` funcionou e screenshot enviado mostra a tela de Alerts do Alertmanager carregada com grupos de alertas. |

#### Observações de alinhamento com o manual

- O manual diz que ServiceMonitor para `web` é opcional; o documento foca nas três APIs, como pedido obrigatório.
- O manual pede PodMonitor para o sidecar de log somente se ele expuser métricas. O `log-forwarder` é um BusyBox executando `tail -F /var/log/app/app.log`, sem porta HTTP e sem endpoint `/metrics`; por isso não foi criado PodMonitor para ele.
- O print final do Prometheus mostra a tela de targets em scroll parcial. A comprovação completa das 3 APIs `UP` fica no output raw do Prometheus com 7 targets em `value: 1`.

Para fechar a semana, instalei observabilidade de verdade com Prometheus, Alertmanager e Grafana. O foco não foi só abrir dashboard bonito: foi confirmar coleta real das APIs via `ServiceMonitor`, persistência dos componentes e liberação explícita nas NetworkPolicies para o scraping funcionar.

**Setup:**
- kube-prometheus-stack instalado via Helm no namespace `tipsbank-monitoring`
- Values customizados: Grafana com persistence NFS (`nfs-tp-data`, 5Gi), Ingress TLS cert-manager, senha `tipsbank@puff`
- Prometheus com retention 15d, storage NFS 20Gi, `serviceMonitorSelectorNilUsesHelmValues: false`
- Alertmanager com storage NFS 2Gi
- Ingresses publicados para Grafana e Prometheus; Alertmanager validado via port-forward local
- 3 ServiceMonitors criados: api-contas, api-transacoes, auditoria (label `release: kube-prometheus-stack`)
- NetworkPolicies de scraping aplicadas nos 3 namespaces de API
- NetworkPolicy de egress do Prometheus criada em `tipsbank-monitoring`, liberando saída para as três APIs na porta 8080 e DNS no CoreDNS

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

Targets verificados primeiro pela UI do Prometheus e depois via API do próprio cluster. O diagnóstico ficou bem claro: o Prometheus descobria os targets das três APIs, mas não conseguia conectar nos pods para raspar `/metrics`.

**Estado antes da correção — targets descobertos, mas `up=0`:**

```bash
kubectl get --raw '/api/v1/namespaces/tipsbank-monitoring/services/http:kube-prometheus-stack-prometheus:9090/proxy/api/v1/query?query=up%7Bnamespace%3D~%22tipsbank-.*%22%7D'
```

**Trechos relevantes do retorno:**

```json
{"job":"api-contas","namespace":"tipsbank-contas","pod":"api-contas-67dcb8b76c-fbfkm"}       value: 0
{"job":"api-contas","namespace":"tipsbank-contas","pod":"api-contas-67dcb8b76c-pb6nt"}       value: 0
{"job":"api-transacoes","namespace":"tipsbank-transacoes","pod":"api-transacoes-659558d96c-cnkcw"} value: 0
{"job":"api-transacoes","namespace":"tipsbank-transacoes","pod":"api-transacoes-659558d96c-h7wfl"} value: 0
{"job":"api-transacoes","namespace":"tipsbank-transacoes","pod":"api-transacoes-659558d96c-wk5hg"} value: 0
{"job":"auditoria","namespace":"tipsbank-auditoria","pod":"auditoria-69dffc8c99-f45jp"}          value: 0
{"job":"auditoria","namespace":"tipsbank-auditoria","pod":"auditoria-69dffc8c99-q6sfq"}          value: 0
```

O detalhe decisivo veio do endpoint `/api/v1/targets`: o `lastError` era `context deadline exceeded` para todos os pods das APIs.

```bash
kubectl get --raw '/api/v1/namespaces/tipsbank-monitoring/services/http:kube-prometheus-stack-prometheus:9090/proxy/api/v1/targets?state=active' \
  | jq '.data.activeTargets[] | select(.labels.job=="api-contas" or .labels.job=="api-transacoes" or .labels.job=="auditoria") | {job: .labels.job, namespace: .labels.namespace, pod: .labels.pod, health: .health, scrapeUrl: .scrapeUrl, lastError: .lastError}'
```

**Output resumido:**

```json
{"job":"auditoria","namespace":"tipsbank-auditoria","pod":"auditoria-69dffc8c99-f45jp","health":"down","scrapeUrl":"http://10.244.209.217:8080/metrics","lastError":"Get \"http://10.244.209.217:8080/metrics\": context deadline exceeded"}
{"job":"api-contas","namespace":"tipsbank-contas","pod":"api-contas-67dcb8b76c-fbfkm","health":"down","scrapeUrl":"http://10.244.209.196:8080/metrics","lastError":"Get \"http://10.244.209.196:8080/metrics\": context deadline exceeded"}
{"job":"api-transacoes","namespace":"tipsbank-transacoes","pod":"api-transacoes-659558d96c-cnkcw","health":"down","scrapeUrl":"http://10.244.209.221:8080/metrics","lastError":"Get \"http://10.244.209.221:8080/metrics\": context deadline exceeded"}
```

Também foi validado com pods temporários em `tipsbank-monitoring`: o namespace estava tão restrito que até resolução DNS falhava para os FQDNs das APIs.

```bash
kubectl run test-prom-scrape --rm -i --restart=Never -n tipsbank-monitoring \
  --image=curlimages/curl:8.5.0 \
  -- curl -v --max-time 10 http://api-contas.tipsbank-contas.svc.cluster.local:8080/metrics
```

**Output:**

```
* Could not resolve host: api-contas.tipsbank-contas.svc.cluster.local
curl: (6) Could not resolve host: api-contas.tipsbank-contas.svc.cluster.local
```

**Causa raiz:** as políticas de ingress nos namespaces das APIs estavam corretas, mas faltava uma política de **egress do próprio Prometheus** saindo de `tipsbank-monitoring` para `tipsbank-contas`, `tipsbank-transacoes` e `tipsbank-auditoria` na porta 8080. ServiceMonitor cria o alvo, mas quem abre a conexão HTTP é o pod do Prometheus; sem egress liberado, o scrape fica em timeout.

**Solução aplicada — `k8s/network-policies/allow-prometheus-egress-to-tipsbank-apis.yaml`:**

```bash
kubectl apply -f k8s/network-policies/allow-prometheus-egress-to-tipsbank-apis.yaml
# networkpolicy.networking.k8s.io/allow-prometheus-egress-to-tipsbank-apis created
```

```bash
kubectl describe netpol allow-prometheus-egress-to-tipsbank-apis -n tipsbank-monitoring
```

**Output:**

```
PodSelector: prometheus=kube-prometheus-stack-prometheus
Allowing egress traffic:
  To Port: 8080/TCP
  NamespaceSelector: kubernetes.io/metadata.name=tipsbank-contas
  PodSelector: app=api-contas
  ----------
  To Port: 8080/TCP
  NamespaceSelector: kubernetes.io/metadata.name=tipsbank-transacoes
  PodSelector: app=api-transacoes
  ----------
  To Port: 8080/TCP
  NamespaceSelector: kubernetes.io/metadata.name=tipsbank-auditoria
  PodSelector: app=auditoria
  ----------
  To Port: 53/UDP
  To Port: 53/TCP
  NamespaceSelector: kubernetes.io/metadata.name=kube-system
  PodSelector: k8s-app=kube-dns
Policy Types: Egress
```

**Estado final — as 3 APIs `UP`:**

```bash
kubectl get --raw '/api/v1/namespaces/tipsbank-monitoring/services/http:kube-prometheus-stack-prometheus:9090/proxy/api/v1/query?query=up%7Bjob%3D~%22api-contas%7Capi-transacoes%7Cauditoria%22%7D'
```

**Output resumido:**

```json
{"job":"auditoria","namespace":"tipsbank-auditoria","pod":"auditoria-69dffc8c99-f45jp"}                  value: 1
{"job":"auditoria","namespace":"tipsbank-auditoria","pod":"auditoria-69dffc8c99-q6sfq"}                  value: 1
{"job":"api-contas","namespace":"tipsbank-contas","pod":"api-contas-67dcb8b76c-fbfkm"}                   value: 1
{"job":"api-contas","namespace":"tipsbank-contas","pod":"api-contas-67dcb8b76c-pb6nt"}                   value: 1
{"job":"api-transacoes","namespace":"tipsbank-transacoes","pod":"api-transacoes-659558d96c-cnkcw"}       value: 1
{"job":"api-transacoes","namespace":"tipsbank-transacoes","pod":"api-transacoes-659558d96c-h7wfl"}       value: 1
{"job":"api-transacoes","namespace":"tipsbank-transacoes","pod":"api-transacoes-659558d96c-wk5hg"}       value: 1
```

Com isso, o critério literal do manual fica atendido: Prometheus tem targets das 3 APIs e todos aparecem `UP`. O ponto legal aqui é que o problema não era observabilidade em si; era o zero-trust funcionando até demais, bloqueando a saída do Prometheus.

Sobre o sidecar `log-forwarder`: ele não expõe métrica Prometheus. O container só acompanha o arquivo `/var/log/app/app.log` com `tail -F`, então não existe porta ou path para o Prometheus raspar via PodMonitor. A observabilidade do sidecar nesta entrega fica limitada ao log do container, enquanto as métricas HTTP ficam nas três APIs instrumentadas.

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

#### Critério 5 — Alertmanager UI funcional

O Alertmanager foi validado via port-forward, que é suficiente para provar que o serviço responde e que a UI está operável. O screenshot enviado mostra a página `/#/alerts` carregada em `localhost:9093`, com grupos por namespace e alertas ativos/listados.

```bash
kubectl port-forward -n tipsbank-monitoring svc/kube-prometheus-stack-alertmanager 9093:9093
```

**Output:**

```
Forwarding from 127.0.0.1:9093 -> 9093
Forwarding from [::1]:9093 -> 9093
Handling connection for 9093
Handling connection for 9093
```

**Ingresses e serviços de observabilidade:**

```
NAME                               CLASS   HOSTS                               ADDRESS         PORTS     AGE
kube-prometheus-stack-grafana      nginx   grafana.tipsbank.staypuff.info      192.168.3.110   80, 443   4d3h
kube-prometheus-stack-prometheus   nginx   prometheus.tipsbank.staypuff.info   192.168.3.110   80, 443   4d3h
locust                             nginx   locust.tipsbank.staypuff.info       192.168.3.110   80        160m
```

```
kube-prometheus-stack-alertmanager               ClusterIP   10.105.148.58    <none>        9093/TCP,8080/TCP   4d3h
kube-prometheus-stack-grafana                    ClusterIP   10.110.149.137   <none>        80/TCP              4d3h
kube-prometheus-stack-prometheus                 ClusterIP   10.111.49.251    <none>        9090/TCP,8080/TCP   4d3h
```

Como o print do Alertmanager foi enviado diretamente no chat e não existe como arquivo dentro de `docs/imagens`, a evidência textual acima registra o comando, a resposta do port-forward e o conteúdo visível na UI.

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

**Status:** Concluído (2026-05-23)

#### Objetivo segundo o MANUAL-ALUNO.md

Criar quatro alertas críticos via PrometheusRule e provocar cada condição para comprovar disparo no Alertmanager.

#### Critérios de aceite do manual

- Os 4 alertas aparecem em `kubectl get prometheusrule -A`.
- Todos disparam quando a condição é provocada, com evidência no `EVIDENCIAS.md`.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| PrometheusRule criada e carregada | **Atendido** | `kubectl get prometheusrule -A` — `tipsbank-slo-alerts` presente em `tipsbank-monitoring`. |
| Targets das 3 APIs scrapeados | **Atendido** | Query `up{}` confirma 6 targets (2 pods × 3 APIs) com `up=1` e label `namespace` correto. |
| `TipsBankApiDown` disparando | **Atendido** | FIRING após `kubectl scale --replicas=0` + `for:2m`. Screenshots abaixo. |
| `TipsBankPodCrashLoop` disparando | **Atendido** | FIRING imediato após 4 restarts via `kubectl debug` + `kill 1`. Screenshots abaixo. |
| `TipsBankErroAltoApi` disparando | **Atendido** | FIRING (2 jobs) — api-contas 60% e api-transacoes 61% de 5xx. Screenshots abaixo. |
| `TipsBankP99Alto` disparando | **Atendido** | FIRING em 2 séries (`api-contas` e `api-transacoes`) após carga com Locust manter p99 acima de 500ms por mais de 5min. |

#### Observações de alinhamento com o manual

- O manual pede que os 4 alertas disparem quando a condição for provocada. A primeira tentativa não gerou latência suficiente para o `TipsBankP99Alto`, mas o teste posterior com Locust elevou o p99 por mais de 5 minutos e fechou o quarto alerta em **FIRING**.
- O objetivo do manual fala em "4 alertas críticos", mas a própria tabela do manual define `TipsBankP99Alto` e `TipsBankPodCrashLoop` com severity `warning`. A implementação seguiu essa tabela: disponibilidade/erros como `critical`, latência/crashloop como `warning`.
- A expressão de `TipsBankApiDown` foi ajustada de `up == 0` para `kube_deployment_status_replicas_available == 0`, porque `up` desaparece quando o Deployment fica sem Endpoints. Essa adaptação mantém o objetivo do alerta: detectar API sem réplicas disponíveis.

---

#### Processo de debug — 2026-05-16 (ontem)

O PrometheusRule passou por 3 iterações até a versão funcional. Documentado a seguir com evidências visuais de cada estado.

---

##### Debug Passo 1 — PrometheusRule v1 criado, expressão com `job=~"tipsbank-.*"`

**2026-05-16 09:31** — PrometheusRule aplicado pela primeira vez. Terminal mostra `kubectl get prometheusrule -A` com `tipsbank-slo-alerts` com 38s de idade. A expressão usava `up{job=~"tipsbank-.*"} == 0`.

![](<imagens/Captura de tela 2026-05-16 093148.png>)

**Problema técnico:** O label `job` no Prometheus Operator é derivado do nome do **Service** sendo scrapeado via `__meta_kubernetes_service_name` durante o relabeling do ServiceMonitor. Os valores reais são `api-contas`, `api-transacoes`, `auditoria` — nenhum começa com `tipsbank-`. O regex `tipsbank-.*` nunca casaria com nenhum target existente.

---

##### Debug Passo 2 — INACTIVE com `job=~"tipsbank-.*"` confirmado

**2026-05-16 09:42** — Prometheus Alerts UI: `tipsbank.availability` em estado **INACTIVE (1)**, confirmando que a expressão nunca avalia como verdadeira. A expressão `up{job=~"tipsbank-.*"} == 0` retorna série vazia — nenhum target tem esse prefixo no job label.

![](<imagens/Captura de tela 2026-05-16 094203.png>)

![](<imagens/Captura de tela 2026-05-16 094213.png>)

**Análise:** O estado INACTIVE significa que a condição de alerta nunca foi verdadeira desde que o PrometheusRule foi carregado. Diferente de PENDING (condição verdadeira mas dentro do `for:`) ou FIRING (condição verdadeira por tempo suficiente). INACTIVE = expressão sempre retorna vazio ou false.

---

##### Debug Passo 3 — Tentativa com `namespace=~"tipsbank-.*"`, estado UNKNOWN

**2026-05-16 09:54** — Após diagnosticar que o filtro `job` estava errado, a expressão foi alterada para `up{namespace=~"tipsbank-.*"} == 0`. O alerta foi para estado **UNKNOWN (1)**.

![](<imagens/Captura de tela 2026-05-16 095454.png>)

**Análise do estado UNKNOWN:** Ocorre quando o Prometheus não consegue avaliar a expressão no período de `interval:` configurado. Neste caso, `api-contas` estava com 0 réplicas — sem Endpoints, sem target no Prometheus, sem série `up` para aquele namespace. A expressão `up{namespace="tipsbank-contas"} == 0` não retorna `true` (série com valor 0), retorna **ausente** (série inexistente). Isso é conceitualmente diferente.

---

##### Debug Passo 4 — Prova da ausência: `up == 0` é vazio quando scale=0

**2026-05-16 09:57** — Query manual `up{namespace=~"tipsbank-.*"} == 0` no Prometheus Query UI confirma o problema: **"Empty query result — This query returned no data."**

![](<imagens/Captura de tela 2026-05-16 095726.png>)

**Raiz do problema:** A métrica `up` é gerada pelo Prometheus **somente quando existe um target para scrape**. O target é criado pelo Prometheus Operator a partir dos Endpoints do Service. Com `--replicas=0`, os Endpoints ficam vazios (`kubectl get endpoints api-contas -n tipsbank-contas` retorna `<none>`). Sem Endpoint, sem target. Sem target, `up` simplesmente não existe para aquele namespace — não é 0, é ausente. A expressão `up{...} == 0` filtra séries onde up=0, mas como não há séries, retorna vazio.

**Conclusão técnica:** `up == 0` detecta falhas de scrape (container running mas `/metrics` inacessível). Não detecta ausência de pods. Para ausência de pods, é necessário usar `kube_deployment_status_replicas_available` do kube-state-metrics, que monitora o objeto Deployment (não o scrape).

---

##### Debug Passo 5 — Diagnóstico dos jobs disponíveis

**2026-05-16 10:20** — Duas queries de diagnóstico: `up{job=~"api-.*"}` retorna 4 resultados (api-contas e api-transacoes, ambos UP neste momento). `up{job=~".*monitor.*"}` retorna vazio — confirmando que os ServiceMonitors não geram jobs com "monitor" no nome.

![](<imagens/Captura de tela 2026-05-16 102005.png>)

**Confirmação dos labels reais:**
- `job="api-contas"` — derivado do Service `api-contas`
- `job="api-transacoes"` — derivado do Service `api-transacoes`
- `job="auditoria"` — derivado do Service `auditoria`
- `namespace="tipsbank-contas"` — adicionado via `__meta_kubernetes_namespace` no relabeling

O filtro correto para cobrir os 3 serviços é `namespace=~"tipsbank-.*"` (não `job`).

---

##### Debug Passo 6 — Final do dia: ainda INACTIVE com `up{namespace} == 0`

**2026-05-16 17:17** — Após o trabalho do dia, o alerta permanecia **INACTIVE** mesmo com o filtro de namespace corrigido. A expressão `up{namespace=~"tipsbank-.*"} == 0` nunca disparou porque `api-contas` estava com 0 réplicas (Endpoints vazios = sem target = `up` ausente).

![](<imagens/Captura de tela 2026-05-16 171733.png>)

O problema foi deixado para investigar no dia seguinte.

---

#### Diagnóstico e correção final — 2026-05-17 (hoje)

---

##### Diagnóstico 1 — `api-contas` completamente ausente dos targets

**2026-05-17 08:39** — Query `up{job!~"alertmanager.*|prometheus.*|kube.*|node.*|coredns.*"}` retorna apenas 5 séries: apiserver + auditoria (×2) + api-transacoes (×2). **`api-contas` não aparece.**

![](<imagens/Captura de tela 2026-05-17 083932.png>)

**Causa raiz identificada:** Deployment `api-contas` com 0 réplicas de teste anterior não revertido. Sem pods → sem Endpoints → sem target → sem `up` → sem `http_requests_total`.

---

##### Diagnóstico 2 — `http_requests_total` confirma ausência de api-contas

**2026-05-17 08:40** — Query `http_requests_total` mostra apenas séries de `api-transacoes`. Nenhuma série de `api-contas` ou `auditoria` (auditoria não expõe essa métrica por design — usa `auditoria_eventos_total`).

![](<imagens/Captura de tela 2026-05-17 084034.png>)

**Ação de correção:**
```bash
kubectl scale deployment api-contas -n tipsbank-contas --replicas=2
# → Pods subiram, Endpoints populados, target criado pelo Operator, up=1 após ~30s
```

---

#### Evidência 1 — PrometheusRule carregado pelo Operator

```bash
kubectl get prometheusrule -A | grep tipsbank
# → tipsbank-monitoring   tipsbank-slo-alerts   95s
```

```
NAMESPACE             NAME                                                              AGE
tipsbank-monitoring   kube-prometheus-stack-alertmanager.rules                          3d15h
...
tipsbank-monitoring   tipsbank-slo-alerts                                               95s
```

O PrometheusRule `tipsbank-slo-alerts` carregado no namespace `tipsbank-monitoring` com os 4 grupos: `tipsbank.availability`, `tipsbank.latency`, `tipsbank.errors`, `tipsbank.stability`. ✅

---

#### Evidência 2 — Targets das 3 APIs scrapeados (pós-correção)

```promql
up{job!~"alertmanager.*|prometheus.*|kube.*|node.*|coredns.*"}
```

```
up{container="api-contas", job="api-contas", namespace="tipsbank-contas",
   instance="10.244.209.237:8080", pod="api-contas-64554bbd-gjtzr"}   1
up{container="api-contas", job="api-contas", namespace="tipsbank-contas",
   instance="10.244.209.238:8080", pod="api-contas-64554bbd-w68d8"}   1
up{container="api-transacoes", job="api-transacoes", namespace="tipsbank-transacoes",
   instance="10.244.209.225:8080"}   1
up{container="api-transacoes", job="api-transacoes", namespace="tipsbank-transacoes",
   instance="10.244.209.221:8080"}   1
up{container="auditoria", job="auditoria", namespace="tipsbank-auditoria",
   instance="10.244.209.217:8080"}   1
up{container="auditoria", job="auditoria", namespace="tipsbank-auditoria",
   instance="10.244.209.218:8080"}   1
```

6 targets (2 pods × 3 APIs), todos `up=1`, label `namespace` correto para o filtro `namespace=~"tipsbank-.*"`. ✅

---

#### Evidência 3 — Teste `TipsBankApiDown`

**Expressão final (v3.2):**
```promql
kube_deployment_status_replicas_available{
  deployment=~"api-contas|api-transacoes|auditoria",
  namespace=~"tipsbank-.*"
} == 0
```

**Por que `kube_deployment_status_replicas_available` e não `up`:**
- `up` é gerado pelo scrape — depende de Endpoints existirem
- `kube_deployment_status_replicas_available` vem do kube-state-metrics, que monitora o objeto Deployment diretamente via Kubernetes API — existe sempre que o Deployment existe, independente de réplicas
- Com `--replicas=0`: kube-state-metrics reporta `0` imediatamente; `up` simplesmente não existe

**Teste executado:**
```bash
kubectl scale deployment api-contas -n tipsbank-contas --replicas=0
# kube_deployment_status_replicas_available{deployment="api-contas"} → 0 imediato
# Aguardar for:2m → FIRING
```

**Estado PENDING (3m25s após scale=0):**

![](<imagens/Captura de tela 2026-05-17 091229.png>)

**Estado FIRING (14m20s — passou o `for:2m`):**

![](<imagens/Captura de tela 2026-05-17 092247.png>)

**Labels do alerta disparado:**
- `alertname="TipsBankApiDown"`
- `deployment="api-contas"`
- `namespace="tipsbank-contas"`
- `severity="critical"`, `team="tipsbank"`
- `container="kube-state-metrics"` — confirma que vem do kube-state-metrics, não do scrape direto
- Value: `0` (zero réplicas disponíveis)

✅ **TipsBankApiDown FIRING confirmado.**

---

#### Evidência 4 — Teste `TipsBankPodCrashLoop`

**Expressão:**
```promql
increase(
  kube_pod_container_status_restarts_total{
    namespace=~"tipsbank-.*",
    container!~"log-forwarder|init-.*"
  }[10m]
) > 3
```

**`for: 0m`** — dispara imediatamente ao atingir o threshold, sem período de estabilização. Intencionalmente agressivo: CrashLoop é sempre uma anomalia que requer atenção imediata.

**Teste executado:**
```bash
# Kill 1 repetidamente via debug container
kubectl debug -it api-contas-64554bbd-d9m2m \
  --image=busybox --target=api-contas -n tipsbank-contas \
  --profile=sysadmin -- sh
/ # kill 1   # repetido 4x
```

**Terminal durante o teste — kubectl debug sessions + accumulo de RESTARTS:**

![](<imagens/Captura de tela 2026-05-17 093335.png>)

**Estado FIRING (3.769s após threshold atingido):**

![](<imagens/Captura de tela 2026-05-17 093121.png>)

**Labels do alerta disparado:**
- `alertname="TipsBankPodCrashLoop"`
- `pod="api-contas-64554bbd-d9m2m"`
- `container="api-contas"`
- `namespace="tipsbank-contas"`
- `severity="warning"`, `team="tipsbank"`
- Value: `3.08` restarts em 10 minutos (threshold: `> 3`)

**Por que `increase` e não `rate`:** `increase(counter[window])` calcula o incremento absoluto do contador no período. Para restarts, queremos saber "quantas vezes reiniciou", não "qual a taxa por segundo". `increase(...[10m]) > 3` = mais de 3 restarts nos últimos 10 minutos.

✅ **TipsBankPodCrashLoop FIRING confirmado.**

---

#### Evidência 5 — Teste `TipsBankErroAltoApi`

**Expressão:**
```promql
(
  sum by (job, namespace) (
    rate(http_requests_total{namespace=~"tipsbank-.*", status=~"5.."}[3m])
  )
  /
  sum by (job, namespace) (
    rate(http_requests_total{namespace=~"tipsbank-.*"}[3m])
  )
) > 0.05
```

**Mecanismo:** Taxa de requests com status 5xx dividida pela taxa total de requests. Label `status` no contador `http_requests_total` é o código HTTP numérico (ex: `"500"`, `"503"`). O regex `5..` casa com qualquer código 5xx. `> 0.05` = mais de 5% de erro.

**Como o alerta disparou para dois jobs simultaneamente:**
- `api-contas` (value: 0.60): Deployment com 0 réplicas + pod `load` gerando requests → Service sem Endpoints → 5xx
- `api-transacoes` (value: 0.61): Readiness probes com `status=503` acumuladas durante instabilidade do postgres — o readiness probe retorna 503 quando o banco não responde, e esse 503 é registrado em `http_requests_total` pelo middleware da aplicação

**Estado PENDING (2 jobs, 3m37s):**

![](<imagens/Captura de tela 2026-05-17 094014.png>)

**Estado FIRING (2 jobs, 7m18s — passou o `for:3m`):**

![](<imagens/Captura de tela 2026-05-17 094352.png>)

**Labels dos alertas disparados:**

| Label | api-contas | api-transacoes |
|---|---|---|
| `job` | `api-contas` | `api-transacoes` |
| `namespace` | `tipsbank-contas` | `tipsbank-transacoes` |
| `severity` | `critical` | `critical` |
| Value | 0.6039 (60.4%) | 0.6116 (61.2%) |
| Active Since | 7m 18.719s | 7m 18.719s |

**Observação importante:** O 503 do `/health/ready` sendo incluído no cálculo de erro é **comportamento correto**. Do ponto de vista do SLO, se o readiness probe falha, a API está degradada. Em produção, filtrar health checks do SLO requer `path!~"/health/.*"` na expressão — decisão de design que depende do SLA acordado com o negócio.

✅ **TipsBankErroAltoApi FIRING confirmado (2 jobs).**

---

#### Evidência 6 — Teste `TipsBankP99Alto`

**Expressão:**
```promql
histogram_quantile(0.99,
  sum by (le, job, namespace) (
    rate(http_request_duration_seconds_bucket{namespace=~"tipsbank-.*"}[5m])
  )
) > 0.5
```

**Como `histogram_quantile` funciona:** A métrica `http_request_duration_seconds` é um Histogram — gera três séries: `_bucket` (contadores por faixa de latência com label `le`), `_count` e `_sum`. O `rate(...[5m])` converte os counters de bucket em taxa/segundo. O `sum by (le, job, namespace)` agrega por job preservando os buckets (`le` é obrigatório para `histogram_quantile`). O resultado é o percentil 99 da latência em segundos. `> 0.5` = mais de 500ms.

**Tentativa inicial sem disparo:**
```
{job="api-transacoes", namespace="tipsbank-transacoes"}   0.10975000000000092
{job="api-contas", namespace="tipsbank-contas"}           0.10974997500027624
```

P99 medido: **~110ms** mesmo sob stress de 100 requisições paralelas. FastAPI em Distroless + PostgreSQL local + rede Calico interna não satura com esse volume. O alerta permaneceu **INACTIVE** — a condição `> 0.5` nunca foi verdadeira.

**Fechamento em 2026-05-23:** Para provocar a condição do manual, rodei nova carga via Locust contra `api-transacoes` e `api-contas`. A carga elevou o p99 para vários segundos e o Prometheus manteve o `TipsBankP99Alto` em **PENDING** até completar o `for: 5m`.

![](<imagens/Captura de tela 2026-05-23 134510.png>)
*13:45 — Prometheus Alerts: `TipsBankP99Alto` em PENDING para `api-transacoes` e `api-contas`, com valores acima de 9s e active por ~3m49s*

Após completar o período de estabilização, o grupo `tipsbank.latency` passou para **FIRING**. O alerta disparou para duas séries:

| Label | api-transacoes | api-contas |
|---|---|---|
| `alertname` | `TipsBankP99Alto` | `TipsBankP99Alto` |
| `namespace` | `tipsbank-transacoes` | `tipsbank-contas` |
| `severity` | `warning` | `warning` |
| Active Since | ~5m10s | ~5m10s |
| Value | 10 | 10 |

![](<imagens/Captura de tela 2026-05-23 134633.png>)
*13:46 — Prometheus Alerts: `TipsBankP99Alto` em FIRING para `api-transacoes` e `api-contas`, depois de passar o `for: 5m`*

A tela do Locust confirma a causa do disparo: latências p99 muito acima do limite de 500ms.

![](<imagens/Captura de tela 2026-05-23 134652.png>)
*13:46 — Locust após o teste: p99 de 19s em `/contas`, 10s em `/transferencias`, 8.8s em `/extrato/:id` e p99 agregado de 11s*

✅ **TipsBankP99Alto FIRING confirmado.**

---

#### Critérios de aceite — status final

| Critério | Status |
|---|---|
| Os 4 alertas aparecem em `kubectl get prometheusrule -A` | ✅ Atendido |
| `TipsBankApiDown` dispara quando condição é provocada | ✅ FIRING após `scale --replicas=0` + 2min |
| `TipsBankPodCrashLoop` dispara quando condição é provocada | ✅ FIRING imediato após 4 restarts em 10min |
| `TipsBankErroAltoApi` dispara quando condição é provocada | ✅ FIRING (2 jobs) após taxa 5xx > 5% por 3min |
| `TipsBankP99Alto` dispara quando condição é provocada | ✅ FIRING após carga com Locust manter p99 acima de 500ms por mais de 5min |

---

### Etapa 3.7 — HPA + Metrics Server + Locust stress test

**Status:** Parcialmente concluído, com validação operacional em 60 usuários — 2026-05-23

#### Objetivo segundo o MANUAL-ALUNO.md

Instalar Metrics Server, configurar HPAs nas 3 APIs e gerar carga real com Locust para comprovar escala automática e scaleDown.

O Manual pede um teste de 5 minutos com 200 usuários, erro do Locust abaixo de 1%, `api-transacoes` escalando para mais de 5 réplicas e scaleDown em até 10 minutos. A implementação de HPA funciona, mas o teste literal de 200 usuários saturou o hardware do homelab. Por isso, além do teste exigido, foram executados testes progressivos com 100, 80, 70 e 60 usuários para separar comportamento da aplicação de limitação física do cluster.

#### Commits desta etapa

| Hash | Mensagem |
|---|---|
| `63b3f3a` | semana 3.7 - HPA-api-contas |
| `9576034` | semana 3.7 - HPA-api-transacoes |
| `1574fe2` | semana 3.7 - HPA-auditoria |
| `5eca298` | semana 3.7 - locust (deploy inicial) |
| `f5a968a` | semana 3.7 - locust em tipsbank-transacoes *(incorreto — revertido)* |
| `3201219` | semana 3.7 - locust em monitoring v3 com networkpolicy allow-dns |

---

#### Evidência 1 — Metrics Server instalado

```bash
kubectl get pods -n kube-system -l k8s-app=metrics-server
# metrics-server-6ccf764647-4bs54   1/1   Running   0   6h55m
```

O kubeadm não inclui o Metrics Server por padrão. Foi necessário patch com `--kubelet-insecure-tls` por causa dos certificados autoassinados dos kubelets no cluster kubeadm.

---

#### Evidência 2 — 3 HPAs com métricas ativas

```
NAMESPACE             NAME                 REFERENCE                   TARGETS           MINPODS   MAXPODS   REPLICAS   AGE
tipsbank-auditoria    hpa-auditoria        Deployment/auditoria        memory: 31%/75%   2         6         2          6h55m
tipsbank-contas       hpa-api-contas       Deployment/api-contas       cpu: 3%/70%       2         10        2          7h
tipsbank-transacoes   hpa-api-transacoes   Deployment/api-transacoes   cpu: 3%/70%       3         15        3          6h58m
```

Todos os 3 HPAs exibem métricas reais (não `<unknown>`).

**Manifests aplicados:**

`k8s/hpa/hpa-api-contas.yaml` — Resource CPU 70%, min 2, max 10:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hpa-api-contas
  namespace: tipsbank-contas
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-contas
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 2
          periodSeconds: 120
```

`k8s/hpa/hpa-api-transcoes.yaml` — **ContainerResource** CPU 70% (só container `api-transacoes`, exclui sidecar `log-forwarder`), min 3, max 15:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hpa-api-transacoes
  namespace: tipsbank-transacoes
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-transacoes
  minReplicas: 3
  maxReplicas: 15
  metrics:
    - type: ContainerResource
      containerResource:
        name: cpu
        container: api-transacoes
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 2
          periodSeconds: 120
```

`k8s/hpa/hpa-auditoria.yaml` — Resource Memory 75%, min 2, max 6:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hpa-auditoria
  namespace: tipsbank-auditoria
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: auditoria
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
```

---

#### Evidência 3 — Locust deployado em tipsbank-monitoring

```bash
kubectl get pods -n tipsbank-monitoring -l app=locust
# locust-94b7fdffb-v4hrq   1/1   Running   0   110s
```

Ingress: `locust.tipsbank.staypuff.info` → Service 8089 → pod locust.
`LOCUST_HOST=http://api-transacoes.tipsbank-transacoes.svc.cluster.local:8080`

---

#### Incidente DNS — falha de resolução em tipsbank-monitoring

**Data:** 2026-05-17 ~17:53–18:00

**Sintoma:**
```bash
kubectl run test-curl --rm -i --restart=Never -n tipsbank-monitoring \
  --image=curlimages/curl:8.5.0 \
  -- curl -v --max-time 5 \
  http://api-transacoes.tipsbank-transacoes.svc.cluster.local:8080/health/ready

# * Could not resolve host: api-transacoes.tipsbank-transacoes.svc.cluster.local
# curl: (6) Could not resolve host: ...
```

**Causa raiz:** pods em `tipsbank-monitoring` não tinham egress para porta 53 (CoreDNS). A política de ingress `allow-from-monitoring` em `tipsbank-transacoes` estava correta, mas o tráfego nunca chegava lá porque o pod nem resolvia o hostname.

**Erro de namespace intermediário (commit `f5a968a`):** Locust foi movido para `tipsbank-transacoes` tentando evitar o problema. Porém esse namespace tem `default-deny-all` — o Locust ficou inacessível pelo ingress-nginx (UI bloqueada) e sem DNS também. Revertido.

**NetworkPolicies em `tipsbank-transacoes` confirmadas:**
```bash
kubectl get networkpolicy -n tipsbank-transacoes
# default-deny-all              <none>   (ingress+egress bloqueados por padrão)
# allow-dns-egress-transacoes   <none>   (egress DNS liberado para os pods)
# allow-ingress-to-api-transacoes ...
# allow-transacoes-to-contas ...
# allow-transacoes-to-auditoria ...
```

**Solução — `k8s/network-policies/allow-monitoring-locust-to-transacoes.yaml`:**
```yaml
# Política 1: egress do pod Locust → api-transacoes:8080
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-locust-egress-to-transacoes
  namespace: tipsbank-monitoring
spec:
  podSelector:
    matchLabels:
      app: locust
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: tipsbank-transacoes
          podSelector:
            matchLabels:
              app: api-transacoes
      ports:
        - port: 8080
          protocol: TCP
---
# Política 2: egress DNS de todos os pods → CoreDNS
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress-monitoring
  namespace: tipsbank-monitoring
spec:
  podSelector: {}
  policyTypes:
    - Egress
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

```bash
kubectl apply -f k8s/network-policies/allow-monitoring-locust-to-transacoes.yaml
# networkpolicy.networking.k8s.io/allow-locust-egress-to-transacoes created
# networkpolicy.networking.k8s.io/allow-dns-egress-monitoring created
```

A política de ingress no lado de `tipsbank-transacoes` (aplicada anteriormente):
```bash
kubectl describe networkpolicy allow-from-monitoring -n tipsbank-transacoes
# PodSelector: app=api-transacoes
# Ingress: To Port 8080/TCP From NamespaceSelector: tipsbank-monitoring
```

---

#### Evidência 4 — Teste exigido pelo Manual: 200 usuários saturou o hardware

Em 2026-05-22 e 2026-05-23, o teste com 200 usuários comprovou que o HPA reage, mas também mostrou que o hardware disponível não sustenta essa carga com o critério de erro do Manual.

Evidências principais:

| Tela | Leitura |
|---|---|
| `2026-05-22 084327` / `084336` | Proxmox com CPU geral em 94% e depois 99% dos 8 CPUs; nós `pve1` e `pve2` próximos de saturação. |
| `2026-05-22 084623` | `api-contas` em 10 réplicas e `api-transacoes` em 15 réplicas; pods com `OOMKilled` e `CrashLoopBackOff`. |
| `2026-05-22 084932` / `085953` | Locust parado com 7% de falhas, 746 falhas em 11187 requests e p99 agregado de 13s. |
| `2026-05-23 134226` | Locust rodando com 200 usuários, 6% de falhas e p99 agregado de 14s. |
| `2026-05-23 134301` / `134310` / `134441` | Proxmox entre 97% e 99% de CPU; `pve2` chegou a 100%. |

![](<imagens/Captura de tela 2026-05-22 084623.png>)
![](<imagens/Captura de tela 2026-05-22 084932.png>)
![](<imagens/Captura de tela 2026-05-23 134226.png>)
![](<imagens/Captura de tela 2026-05-23 134310.png>)

Conclusão: o teste de 200 usuários não atende o aceite de erro `< 1%`, mas é uma evidência importante de limite de capacidade do ambiente. O HPA escalou até o máximo configurado, porém a CPU física do homelab virou o gargalo.

---

#### Evidência 5 — Testes progressivos para encontrar carga compatível com o hardware

Foram feitos testes adicionais reduzindo usuários para identificar uma carga operacional que preservasse o critério de erro do Manual.

| Usuários | Requests | Falhas | Erro real | p99 agregado | Resultado |
|---:|---:|---:|---:|---:|---|
| 100 | 11978 | 133 | 1,11% | 3500 ms | Acima do limite de erro. |
| 80 | 3230 | 33 | 1,02% | 3300 ms | Ainda acima do limite, por pouco. |
| 70 | 3887 | 38 | 0,98% | 3100 ms | Abaixo de 1%, mas a UI arredonda para 1%. |
| 60 | 3865 | 0 | 0,00% | 1700 ms | Melhor evidência operacional no hardware atual. |

No teste com 60 usuários:

```
USERS: 60
RPS: 38.3
FAILURES: 0%
Aggregated: 3865 requests, 0 fails, p99 1700 ms
```

Detalhe por rota:

| Rota | Requests | Falhas | p99 |
|---|---:|---:|---:|
| `POST /contas (setup)` | 60 | 0 | 870 ms |
| `GET /extrato/:id` | 945 | 0 | 370 ms |
| `POST /transferencias` | 2860 | 0 | 1900 ms |

![](<imagens/Captura de tela 2026-05-23 144555.png>)
![](<imagens/Captura de tela 2026-05-23 145401.png>)

---

#### Evidência 6 — HPA escalando durante os testes

Antes de iniciar nova rodada, o HPA voltou ao mínimo:

```
tipsbank-auditoria    hpa-auditoria        memory: 41%/75%   2   6    2
tipsbank-contas       hpa-api-contas       cpu: 7%/70%       2   10   2
tipsbank-transacoes   hpa-api-transacoes   cpu: 1%/50%       3   15   3
```

Durante o teste com 60 usuários, o HPA voltou a escalar:

```
tipsbank-contas       hpa-api-contas       cpu: 95%/70%   2   10   10
tipsbank-transacoes   hpa-api-transacoes   cpu: 96%/50%   3   15   13
```

O critério "`api-transacoes` acima de 5 réplicas" foi atendido com folga. Em rodadas anteriores, `api-transacoes` chegou a 15 réplicas e `api-contas` a 10 réplicas.

![](<imagens/Captura de tela 2026-05-23 142648.png>)
![](<imagens/Captura de tela 2026-05-23 145333.png>)
![](<imagens/Captura de tela 2026-05-23 145444.png>)

---

#### Evidência 7 — ScaleDown observado

O teste original de 2026-05-17 registrou scaleDown de `api-transacoes` de 7 para 3 réplicas. O retorno ocorreu em aproximadamente 11-13 minutos, compatível com a configuração declarada:

```yaml
scaleDown:
  stabilizationWindowSeconds: 300
  policies:
    - type: Pods
      value: 2
      periodSeconds: 120
```

Esse comportamento é tecnicamente coerente com a política aplicada, mas passa um pouco do limite literal do Manual, que pede retorno em até 10 minutos.

![](<imagens/Captura de tela 2026-05-17 183154.png>)

---

#### Critérios de aceite — status final

| Critério | Status | Detalhe |
|---|---|---|
| `kubectl get hpa -A` mostra 3 HPAs com métricas ativas | Atendido | HPAs de `api-contas`, `api-transacoes` e `auditoria` exibem CPU/memória reais. |
| Réplicas de `api-transacoes` sobem acima de 5 | Atendido | `api-transacoes` chegou a 13 réplicas no teste de 60 usuários e a 15 réplicas nas cargas maiores. |
| Erro rate no Locust abaixo de 1% | Atendido no teste operacional de 60 usuários; não atendido em 200 usuários | 60 usuários: 0 falhas em 3865 requests. 200 usuários: 6-9% de falhas por saturação do hardware. |
| Teste de 5 min com 200 usuários | Parcialmente atendido | Executado, mas o homelab saturou CPU e o erro ficou acima de 1%. |
| ScaleDown retorna réplicas em até 10 minutos | Parcialmente atendido | Retorno observado em ~11-13 min, coerente com `stabilizationWindowSeconds: 300` + remoção gradual, mas acima do limite literal. |
| Locust acessível via Ingress | Atendido | `locust.tipsbank.staypuff.info` operacional. |
| Incidente DNS diagnosticado e resolvido | Atendido | Egress DNS e egress Locust -> `api-transacoes` liberados via NetworkPolicy. |

---

### Etapa 3.8 — DaemonSet de coleta

**Status:** ✅ Concluído — 2026-05-17 · commit `538bc70`

---

#### Objetivo segundo o MANUAL-ALUNO.md

Criar um DaemonSet simples rodando em todos os workers, com finalidade didática de coleta ou registro de eventos do node, incluindo toleration para o taint `compliance=strict`. O aceite exige que `kubectl get ds -A` mostre `DESIRED == CURRENT == READY` igual ao número de workers.

---

#### Manifest aplicado — `k8s/tipsbank-monitoring/node-collector-ds.yaml`

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-collector
  namespace: tipsbank-monitoring
  labels:
    app: node-collector
    app.kubernetes.io/part-of: tipsbank
spec:
  selector:
    matchLabels:
      app: node-collector
  template:
    metadata:
      labels:
        app: node-collector
    spec:
      tolerations:
        - key: "compliance"
          operator: "Equal"
          value: "strict"
          effect: "NoSchedule"
      containers:
        - name: node-collector
          image: busybox:1.36
          command:
            - /bin/sh
            - -c
            - |
              while true; do
                echo "$(date) node=$(hostname) disk=$(df -h / | tail -1 | awk '{print $5}')";
                sleep 30;
              done
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 50m
              memory: 32Mi
          volumeMounts:
            - name: host-root
              mountPath: /host
              readOnly: true
      volumes:
        - name: host-root
          hostPath:
            path: /
```

---

#### Análise do mecanismo Taint/Toleration

O DaemonSet controller avalia cada node individualmente. A ausência de toleration age como filtro de exclusão:

| Node | Taint | Toleration no DS | Scheduling |
|---|---|---|---|
| `tb-master1` | `node-role.kubernetes.io/control-plane:NoSchedule` | ❌ ausente | **Excluído** |
| `tb-worker1` | `<none>` | N/A | **Agendado** |
| `tb-worker2` | `compliance=strict:NoSchedule` | ✅ presente | **Agendado** |

DESIRED=2 porque somente os 2 workers são elegíveis. O control-plane permanece excluído sem necessidade de `nodeSelector` — a ausência intencional de toleration cumpre esse papel.

**Idempotência**: durante a sessão o taint foi removido e reaplicado. Uma toleration sem taint correspondente é silenciosamente ignorada — nenhum erro, sem impacto no scheduling.

---

#### Evidência 1 — Estado dos nodes antes do deploy

```bash
kubectl describe nodes | grep -A5 Taints
```
```
# tb-master1
Taints:   node-role.kubernetes.io/control-plane:NoSchedule

# tb-worker1
Taints:   <none>

# tb-worker2
Taints:   compliance=strict:NoSchedule
```

`kubectl top nodes` (baseline):
```
NAME         CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
tb-master1   241m         6%       1969Mi          51%
tb-worker1   286m         7%       2965Mi          50%
tb-worker2   76m          1%       1547Mi          26%
```

![](<imagens/Captura de tela 2026-05-17 191529.png>)
![](<imagens/Captura de tela 2026-05-17 191605.png>)

---

#### Evidência 2 — Apply e critério de aceite

```bash
kubectl apply -f k8s/tipsbank-monitoring/node-collector-ds.yaml
# daemonset.apps/node-collector created

kubectl get ds -A
```

```
NAMESPACE             NAME                                             DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
tipsbank-monitoring   kube-prometheus-stack-prometheus-node-exporter   3         3         3       3            3           kubernetes.io/os=linux
tipsbank-monitoring   node-collector                                   2         2         2       2            2           <none>
```

`DESIRED == CURRENT == READY == 2` — critério de aceite ✅

`NODE SELECTOR: <none>` confirma que a seleção de nodes é feita exclusivamente via toleration/taint, sem nodeSelector declarado.

![](<imagens/Captura de tela 2026-05-17 193311.png>)

---

#### Evidência 3 — Logs dos dois pods

```bash
kubectl logs -l app=node-collector -n tipsbank-monitoring
```

```
Sun May 17 22:29:47 UTC 2026 node=node-collector-6pnc5 disk=30%
Sun May 17 22:30:17 UTC 2026 node=node-collector-6pnc5 disk=30%
Sun May 17 22:30:47 UTC 2026 node=node-collector-6pnc5 disk=30%
Sun May 17 22:29:47 UTC 2026 node=node-collector-zgw7q disk=46%
Sun May 17 22:30:17 UTC 2026 node=node-collector-zgw7q disk=46%
Sun May 17 22:30:48 UTC 2026 node=node-collector-zgw7q disk=46%
```

![](<imagens/Captura de tela 2026-05-17 193446.png>)

Dois pods distintos com discos diferentes (30% vs 46%) confirmam o loop de coleta a cada 30s. A mesma tela mostra `kubectl get pods -o wide` com `node-collector-6pnc5` no `tb-worker2` e `node-collector-zgw7q` no `tb-worker1`, comprovando um pod em cada worker.

O campo `node=` exibe o nome do pod (não o node) — `hostname` em K8s resolve `Pod.metadata.name` via `/etc/hostname`. Para expor o node real seria necessário Downward API (`spec.nodeName` via `fieldRef`). O manifesto também monta o host em `/host`, mas o comando usado na evidência executa `df -h /`; portanto a evidência deve ser lida como registro didático de uso de disco e identidade do pod por worker, suficiente para o aceite desta etapa.

---

#### Critérios de aceite — status final

| Critério | Status | Detalhe |
|---|---|---|
| `kubectl get ds -A` mostra DS com `DESIRED == CURRENT == READY == 2` | ✅ | DESIRED=2, CURRENT=2, READY=2 — tb-worker1 e tb-worker2 |
| DaemonSet não roda no control-plane | ✅ | Sem toleration para `node-role.kubernetes.io/control-plane:NoSchedule` |
| Toleration para `compliance=strict:NoSchedule` | ✅ | `key=compliance, operator=Equal, value=strict, effect=NoSchedule` |
| Pod registrando evento/métrica simples em cada worker | ✅ | Logs confirmam `hostname` e `df -h /` a cada 30s; `kubectl get pods -o wide` confirma um pod no `tb-worker1` e outro no `tb-worker2` |
