---
tags: [tipsbank, evidencias, semana-4, dk8s, kyverno, rbac, x509]
created: 2026-05-18
updated: 2026-06-15
status: pendente-video
semana: 4
---

# TipsBank — Evidências Semana 4: Compliance e Entrega Final

## Semana 4 — Compliance e Entrega Final

### Etapa 4.1 — Kyverno: Validate (proibir root, proibir latest)

**Data de conclusão:** 2026-05-18

#### Objetivo segundo o MANUAL-ALUNO.md

Instalar o Kyverno no cluster e criar 3 ClusterPolicies de validação:
1. `disallow-latest-tag` — rejeitar pods com imagem sem tag ou com tag `:latest`
2. `disallow-root-user` — rejeitar pods que rodam como `runAsUser=0`
3. `require-labels` — exigir labels `app`, `team` e `env` em todos os workloads dos namespaces tipsbank

#### Critérios de aceite do manual

- Kyverno instalado e saudável no cluster.
- `kubectl get cpol` mostra as 3 políticas com `READY=True`.
- `kubectl run teste-latest --image=nginx:latest` → erro de admissão (bloqueado).
- `kubectl run teste-sem-tag --image=nginx` → erro de admissão (bloqueado).
- `kubectl run pod-ruim-root --image=... --overrides='{"spec":{"securityContext":{"runAsUser":0}}}'` → bloqueado.
- `kubectl run teste-ok --image=nginx:1.27` → permitido.
- `kubectl get policyreport -A` mostra todos workloads tipsbank-* com status PASS.

#### Status dos critérios

| Critério | Status | Evidência |
|---|---|---|
| Kyverno instalado e saudável | **Atendido** | Screenshot 120258 — helm install + 4 pods Running |
| 3 policies `READY=True` | **Atendido** | Screenshot 180951 — `kubectl get cpol` mostra as 3 |
| `teste-latest` bloqueado | **Atendido** | Screenshot 173028 — HTTP 403 admission webhook |
| `teste-sem-tag` bloqueado | **Atendido** | Screenshot 173028 — admission controller rejeitou |
| `pod-ruim-root` bloqueado | **Atendido** | Screenshot 175912 — `disallow-root-user` enforcement |
| `teste-ok` permitido | **Atendido** | Pod criado sem rejeição (saída do terminal, sessão) |
| PolicyReport PASS | **Atendido** | Screenshot 180951 — `policyreport -A` tipsbank-* PASS |

---

#### Passo 1 — Instalação do Kyverno via Helm

Kyverno é um admission controller nativo do Kubernetes. Funciona como um `ValidatingWebhookConfiguration` registrado no kube-apiserver: toda requisição de criação/update de recurso passa pelo webhook antes de ser gravada no etcd.

```bash
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm install kyverno kyverno/kyverno -n kyverno --create-namespace \
  --set admissionController.replicas=1 \
  --set backgroundController.enabled=true \
  --set reportsController.enabled=true
```

![[imagens/Captura de tela 2026-05-18 120258.png]]

**Componentes instalados:**
- `kyverno-admission-controller` — intercepta requisições de admission (cria/atualiza recursos)
- `kyverno-background-controller` — varre recursos existentes periodicamente → gera PolicyReport
- `kyverno-cleanup-controller` — gerencia CleanupPolicy (não usada nesta etapa)
- `kyverno-reports-controller` — agrega resultados em PolicyReport/ClusterPolicyReport

> **WARNING** no install: `Setting the admission controller replica count below 2 means Kyverno is not running in high availability mode.` Normal para cluster de lab com 2 workers.
>
> **WARNING**: `PodSecurityStandards are disabled by default. To enable them, set '--enableDefaultPolicies=true'.` Não é necessário para este projeto — usamos ClusterPolicies customizadas.

![[imagens/Captura de tela 2026-05-18 120316.png]]

Todos os pods `tipsbank-*` continuaram Running após a instalação — o Kyverno não interferiu com workloads existentes porque as políticas ainda não existiam.

---

#### Passo 2 — ClusterPolicy: `disallow-latest-tag`

**Arquivo:** `k8s/kyverno/disallow-latest-tag.yaml`

Esta policy tem **duas regras independentes** que cobrem casos distintos:

**Regra 1 — `require-image-tag`** (validate por pattern):
```yaml
validate:
  pattern:
    spec:
      containers:
        - image: "*:*"
      =(initContainers):
        - image: "*:*"
```
Exige que toda imagem tenha o formato `nome:tag`. O padrão `*:*` significa "qualquer coisa antes do `:` e qualquer coisa depois". Se a imagem for `nginx` (sem `:`), o pattern não bate → pod rejeitado.

**Regra 2 — `disallow-tag-latest`** (validate por deny.conditions):
```yaml
validate:
  deny:
    conditions:
      any:
        - key: "{{ images.containers.*.tag }}"
          operator: AnyIn
          value:
            - latest
```
Usa a variável de contexto `{{ images.containers.*.tag }}` — Kyverno extrai as tags de todas as imagens do pod em tempo de admissão e retorna uma lista. Se qualquer tag for `latest`, a condição `AnyIn` é verdadeira → pod rejeitado.

**Por que duas regras e não uma?**

São mecanismos diferentes para problemas diferentes:
- `image: nginx` (sem tag) → Docker resolve para `:latest` implicitamente, mas a string não contém `:latest`. A variável `{{ images.*.tag }}` retornaria `latest` — mas para chegar aqui a imagem precisa ter passado pela regra 1 primeiro. Na prática, usar as duas garante cobertura total.
- `image: nginx:latest` → passa na regra 1 (tem `:`), é bloqueada pela regra 2.
- `image: nginx:1.27.1` → passa nas duas.

---

#### Passo 3 — ClusterPolicy: `disallow-root-user`

**Arquivo:** `k8s/kyverno/disallow-root-user.yaml`

```yaml
validate:
  pattern:
    spec:
      =(securityContext):
        =(runAsUser): ">0"
      containers:
        - =(securityContext):
            =(runAsUser): ">0"
      =(initContainers):
        - =(securityContext):
            =(runAsUser): ">0"
```

**Ponto crítico: o anchor condicional `=(campo):`**

O `=( )` significa "se este campo existir, aplique a restrição; se não existir, ignore". Sem ele:
- Postgres roda como UID 999 mas **não declara** `runAsUser` explicitamente no spec → pattern obrigatório quebraria o StatefulSet.
- A maioria dos pods tipsbank não declara `securityContext` no nível do Pod.

Com `=(runAsUser): ">0"`: se o campo existir, precisa ser maior que zero. Se não existir, o pod passa — a restrição é sobre declaração explícita de root, não sobre ausência de contexto de segurança.

**Teste de bloqueio:**

```bash
kubectl run pod-ruim-root \
  --image=nginx:1.27 \
  --restart=Never \
  -n tipsbank-contas \
  --overrides='{"spec":{"securityContext":{"runAsUser":0}}}'
```

![[imagens/Captura de tela 2026-05-18 175912.png]]

Output: `Error from server: admission webhook "validate.kyverno.svc-fail" denied the request. rule disallow-root-user failed at path /spec/securityContext/runAsUser/`

---

#### Passo 4 — ClusterPolicy: `require-labels`

**Arquivo:** `k8s/kyverno/require-labels.yaml`

```yaml
rules:
  - name: require-app-team-env
    match:
      any:
        - resources:
            kinds:
              - Deployment
              - StatefulSet
              - DaemonSet
            namespaces:
              - tipsbank-contas
              - tipsbank-transacoes
              - tipsbank-auditoria
              - tipsbank-web
    validate:
      pattern:
        metadata:
          labels:
            app: "?*"
            team: "?*"
            env: "?*"
```

O pattern `"?*"` exige string não-vazia: `?` = pelo menos 1 caractere, `*` = qualquer sequência adicional.

**Scope intencional:** a policy só valida os 4 namespaces de aplicação do TipsBank. `tipsbank-monitoring` foi excluído porque o `kube-prometheus-stack` é gerenciado pelo Helm e não tem labels `team`/`env` — alterar isso quebraria o upgrade do chart.

---

#### Testes de compliance — outputs dos comandos

```bash
# BLOQUEADO — sem tag
kubectl run teste-sem-tag --image=nginx --restart=Never -n tipsbank-contas
# Error: admission webhook denied [...] rule require-image-tag failed

# BLOQUEADO — :latest explícito
kubectl run teste-latest --image=nginx:latest --restart=Never -n tipsbank-contas
# Error: admission webhook denied [...] rule disallow-tag-latest

# BLOQUEADO — runAsUser=0
kubectl run pod-ruim-root --image=nginx:1.27 --restart=Never -n tipsbank-contas \
  --overrides='{"spec":{"securityContext":{"runAsUser":0}}}'
# Error: admission webhook denied [...] rule disallow-root-user

# PERMITIDO — tag específica, sem root
kubectl run teste-ok --image=nginx:1.27 --restart=Never -n tipsbank-contas
# pod/teste-ok created
```

![[imagens/Captura de tela 2026-05-18 173028.png]]

---

#### Estado final das policies e PolicyReports

```bash
kubectl get cpol
```

Output:
```
NAME                 ADMISSION   BACKGROUND   READY   AGE     MESSAGE
disallow-latest-tag  true        true         True    60m     Ready
disallow-root-user   true        true         True    3h      Ready
require-labels       true        true         True    30m     Ready
```

![[imagens/Captura de tela 2026-05-18 180951.png]]

O `kyverno-background-controller` varreu todos os recursos existentes e gerou PolicyReports por namespace. Resultado: **FAIL=0 em todos os 4 namespaces de aplicação**.

![[imagens/Captura de tela 2026-05-18 201923.png]]

```bash
kubectl get policyreport -n tipsbank-contas
```
```
NAME                                   KIND          NAME                          PASS   FAIL   WARN   ERROR   SKIP   AGE
18addcdb-4927-4ddd-8936-0bcd4a718447   Deployment    api-contas                    4      0      0      0       0      7h49m
238fc93a-2c92-4ec4-b112-90efa6741797   ReplicaSet    api-contas-64554bbd           3      0      0      0       0      7h49m
494ea847-c531-45e4-9c58-5752708f81bf   Pod           postgres-replica-0            3      0      0      0       0      7h49m
591c8f32-acd0-4e71-aa57-3a55896df8bd   Pod           api-contas-67dcb8b76c-fbfkm   3      0      0      0       0      7h49m
69bb76ea-0b05-4794-abde-a43169e1618e   Pod           postgres-0                    3      0      0      0       0      7h49m
9f183207-5241-4844-8249-65efe5be2fa2   StatefulSet   postgres-replica              4      0      0      0       0      7h49m
c3882251-a0ef-4caf-9918-4b32efa87016   StatefulSet   postgres                      4      0      0      0       0      7h49m
[... demais ReplicaSets com PASS=3, FAIL=0]
```

```bash
kubectl get policyreport -n tipsbank-transacoes
```
```
NAME                                   KIND         NAME                              PASS   FAIL   WARN   ERROR   SKIP   AGE
54beadd3-1348-49eb-aa09-eb27c0d4692a   Deployment   api-transacoes                    4      0      0      0       0      7h49m
57b53c87-dbe8-43b8-a379-c08de48f4103   ReplicaSet   api-transacoes-659558d96c         3      0      0      0       0      7h49m
90ac9b2d-30f4-4752-a6e1-1ebddcae8d6d   Pod          api-transacoes-659558d96c-h7wfl   3      0      0      0       0      7h49m
910c5ef1-5459-456c-a2bb-9ed7b8cbd57a   Pod          api-transacoes-659558d96c-ktvwr   3      0      0      0       0      7h47m
e9205fec-3dc3-4662-991c-faaf6eeb8dec   Pod          api-transacoes-659558d96c-tdhnl   3      0      0      0       0      138m
[... demais ReplicaSets com PASS=3, FAIL=0]
```

```bash
kubectl get policyreport -n tipsbank-auditoria
```
```
NAME                                   KIND         NAME                         PASS   FAIL   WARN   ERROR   SKIP   AGE
65e9bdb0-30f0-494a-ba6f-679437c8c3b4   Deployment   auditoria                    4      0      0      0       0      7h49m
21c23924-6f3a-4e4c-a6ae-e764fef0d475   Pod          auditoria-69dffc8c99-f45jp   3      0      0      0       0      7h49m
ec19ea15-83f1-46fd-b44f-d58b1468c3ba   Pod          auditoria-69dffc8c99-q6sfq   3      0      0      0       0      7h49m
[... demais ReplicaSets com PASS=3, FAIL=0]
```

```bash
kubectl get policyreport -n tipsbank-web
```
```
NAME                                   KIND         NAME                   PASS   FAIL   WARN   ERROR   SKIP   AGE
ec5c23f1-b566-4a2b-9fa4-bcd4f6fb30e8   Deployment   web                    4      0      0      0       0      7h50m
17245ec8-7acf-4b0c-b4c2-26710976720b   Pod          web-744bdd6fd8-bgw6j   3      0      0      0       0      7h50m
ca48ac98-ea5f-49e6-a8df-542554a676cf   Pod          web-744bdd6fd8-dm246   3      0      0      0       0      7h50m
[... demais ReplicaSets com PASS=3, FAIL=0]
```

**Por que Deployments/StatefulSets têm PASS=4 e Pods/ReplicaSets têm PASS=3?**

Não é inconsistência — é a arquitetura de autogen do Kyverno:

- `disallow-latest-tag` e `disallow-root-user` têm regras que fazem match em `Pod`. O Kyverno gera automaticamente regras `autogen-*` para Deployment/StatefulSet/DaemonSet a partir delas — então esses recursos também são avaliados.
- `require-labels` faz match direto em Deployment/StatefulSet/DaemonSet. Não gera autogen para Pod (autogen só vai de Pod → recursos de nível acima, nunca o contrário). Pods não têm as labels `app/team/env` diretamente — a verificação é feita no template do Deployment.
- Resultado: Pods e ReplicaSets passam em 3 regras. Deployments e StatefulSets passam em 4.

**Confirmação técnica crítica: `postgres` e `postgres-replica` (StatefulSet) → PASS=4**

Isso valida que o anchor condicional `=(runAsUser): ">0"` funcionou como esperado. O PostgreSQL roda como UID 999 mas **não declara** `runAsUser` explicitamente no pod spec — o campo simplesmente não existe no manifest. O `=( )` instruiu o Kyverno: "se o campo `runAsUser` existir, exija `>0`; se não existir, ignore". Postgres passa. Um pod com `runAsUser: 0` explícito seria bloqueado.

---

#### Problemas encontrados no caminho

##### Bug 1 — Manifest híbrido em `disallow-latest-tag` (versão inicial)

**O que foi feito de errado:**

```yaml
# ERRADO — versão inicial com 1 regra híbrida
rules:
  - name: require-image-tag       # ← nome da regra 1
    validate:
      deny:                       # ← abordagem da regra 2
        conditions:
          any:
            - key: "{{ images.containers.*.tag }}"
              operator: AnyIn
              value:
                - latest
```

Esta versão misturou o **nome** da primeira regra com o **mecanismo** da segunda. Consequência: a policy só bloqueava `:latest` explícito. O comando `kubectl run teste-sem-tag --image=nginx` passava sem rejeição — a imagem `nginx` sem tag chegava ao cluster.

**Por que isso aconteceu:** as duas abordagens — `pattern` e `deny.conditions` — são mutuamente exclusivas e cobrem casos diferentes. Colocar o nome de uma com o corpo da outra cria uma policy que só faz metade do trabalho.

**Como foi corrigido:** o manifest foi reescrito com as duas regras separadas. A regra `require-image-tag` usa `validate.pattern` para exigir o formato `nome:tag`. A regra `disallow-tag-latest` usa `validate.deny.conditions` para checar o valor da tag via JMESPath.

---

##### Bug 2 — `require-labels` com escopo cluster-wide (v1)

**O que foi feito de errado:**

```yaml
# ERRADO — match sem filtro de namespace
match:
  any:
    - resources:
        kinds:
          - Deployment
          - StatefulSet
          - DaemonSet
        # sem namespaces: → match em TODOS os namespaces
```

Resultado imediato ao aplicar:

```
Warning: PolicyViolation tipsbank-contas/api-contas: [require-app-team-env] fail
Warning: PolicyViolation tipsbank-web/web: [require-app-team-env] fail
Warning: PolicyViolation kube-system/kube-proxy: [require-app-team-env] fail
Warning: PolicyViolation calico-system/calico-node: [require-app-team-env] fail
Warning: PolicyViolation kyverno/kyverno-admission-controller: [require-app-team-env] fail
Warning: PolicyViolation metallb-system/controller: [require-app-team-env] fail
Warning: PolicyViolation cert-manager/cert-manager: [require-app-team-env] fail
Warning: PolicyViolation ingress-nginx/ingress-nginx-controller: [require-app-team-env] fail
Warning: PolicyViolation tipsbank-monitoring/kube-prometheus-stack-grafana: [require-app-team-env] fail
# ... dezenas de violations em recursos de sistema
```

**Por que isso é um problema:** recursos de sistema (kube-proxy, calico-node, kyverno, metallb, cert-manager, kube-prometheus-stack) são gerenciados por Helm ou pelo próprio Kubernetes e não devem receber labels de time/ambiente de negócio. Tentar adicionar `team: sre` a um DaemonSet do Calico causaria conflito no próximo `helm upgrade`.

**Como foi corrigido:** v2 adicionou o filtro `namespaces:` restringindo a política exatamente aos 4 namespaces de aplicação do TipsBank. O namespace `tipsbank-monitoring` foi explicitamente excluído porque o `kube-prometheus-stack` é Helm-managed.

![[imagens/Captura de tela 2026-05-18 175912.png]]

O `kubectl delete cpol require-labels && kubectl apply -f require-labels.yaml` foi necessário para forçar a re-avaliação com o UID correto — sem o delete, o Kyverno manteria o PolicyReport antigo com as violations de sistema.

---

#### Lição técnica: background scan vs admission enforcement

Um ponto que causou confusão inicial: os workloads existentes (api-contas, api-transacoes, etc.) **não foram derrubados** quando as policies foram aplicadas com `validationFailureAction: Enforce`.

Isso é por design do Kyverno:
- O **admission webhook** só age em requisições novas (CREATE, UPDATE). Pods em Running não passam por ele novamente só por existirem.
- O **background scanner** avalia os recursos existentes e gera `PolicyReport` com os resultados, mas **não mata pods** — ele é read-only.

Para forçar a re-validação de um pod existente, é necessário recriá-lo (delete + recreate, ou rollout restart no Deployment).

---

### Etapa 4.2 — Kyverno: Mutate (injetar securityContext)

**Data de conclusão:** 2026-05-19

#### Objetivo segundo o MANUAL-ALUNO.md

O Kyverno injeta automaticamente `runAsNonRoot: true`, `readOnlyRootFilesystem: true` e `allowPrivilegeEscalation: false` em qualquer pod novo criado nos namespaces TipsBank — sem precisar declarar o securityContext em cada Deployment individualmente.

#### Critérios de aceite do manual

- Pod criado sem securityContext recebe o contexto mutado pelo Kyverno
- Todas as 3 APIs do TipsBank continuam funcionando com root filesystem read-only

#### Status dos critérios

| Critério | Status | Evidência |
|---|---|---|
| Pod sem securityContext recebe mutação | **Atendido** | `kubectl get pod teste-mutate -o jsonpath='{.spec.containers[0].securityContext}'` → 3 campos injetados |
| 3 APIs funcionando com readOnlyRootFilesystem | **Atendido** | Todos os pods Running após rollout restart; `curl https://tipsbank.staypuff.info/healthz` → ok |

---

#### Passo 1 — Corrigir o log-forwarder (ajuste necessário antes da policy)

Antes de criar a ClusterPolicy de Mutate, foi necessário corrigir o sidecar `log-forwarder` no deployment `api-transacoes`. O container usava `busybox:1.36` sem nenhum `securityContext` declarado — o container runtime usa o UID padrão da imagem, que para o busybox é UID 0 (root).

Quando a policy de mutate injetou `runAsNonRoot: true`, o kubelet rejeitou o container com:

```
Warning  Failed  kubelet  Error: container has runAsNonRoot and image will run as root
(pod: "api-transacoes-554f5844b6-zdk6k_tipsbank-transacoes", container: log-forwarder)
```

O pod ficou em `CreateContainerConfigError` repetidamente — o container `api-transacoes` principal subia (Running), mas o sidecar ficava em `Waiting`. O rolling update ficou travado: o novo ReplicaSet não conseguia escalar, o antigo não era descomissionado.

**Fix**: adicionar `securityContext.runAsUser: 65532` ao container `log-forwarder` no manifest. UID 65532 é o mesmo usado pelo container principal `api-transacoes` (imagem Distroless). O `sh` e o `tail -F` funcionam perfeitamente como qualquer UID não-root — nenhuma mudança de comportamento.

```yaml
# k8s/tipsbank-transacoes/transacoes-deployment.yaml
containers:
  - name: log-forwarder
    image: busybox:1.36
    securityContext:
      runAsUser: 65532    # ← linha adicionada
    command: [...]
```

```bash
kubectl apply -f k8s/tipsbank-transacoes/transacoes-deployment.yaml
# → deployment.apps/api-transacoes configured
```

**Por que UID 65532 especificamente?** Por consistência com o container principal. O `api-transacoes` (Distroless) cria `/var/log/app/app.log` com permissão `0644` (owner=rw, others=r). O log-forwarder com UID 65532 acessa o arquivo como owner — permissão `rw-`. Mesmo sem `fsGroup`, `0644` é legível por qualquer UID (`others readable`). O `tail -F` só lê do arquivo, nunca cria temporários — `readOnlyRootFilesystem: true` é seguro.

---

#### Passo 2 — ClusterPolicy: `mutate-security-context`

**Arquivo:** `k8s/kyverno/mutate-security-context.yaml`

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: mutate-security-context
  labels:
    rule: mutate-security-context
    app.kubernetes.io/part-of: tipsbank
  annotations:
    policies.kyverno.io/title: Mutate Security Context
    policies.kyverno.io/category: Security
    policies.kyverno.io/severity: High
    policies.kyverno.io/description: Injeta runAsNonRoot, readOnlyRootFilesystem e allowPrivilegeEscalation em tipsbank.
spec:
  rules:
    - name: inject-security-context
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - tipsbank-contas
                - tipsbank-transacoes
                - tipsbank-auditoria
                - tipsbank-web
      mutate:
        foreach:
          - list: "request.object.spec.containers[]"
            patchStrategicMerge:
              spec:
                containers:
                  - (name): "{{ element.name }}"
                    securityContext:
                      +(runAsNonRoot): true
                      +(readOnlyRootFilesystem): true
                      +(allowPrivilegeEscalation): false
```

**Anatomia técnica:**

| Elemento | Função |
|---|---|
| `foreach` + `list: "request.object.spec.containers[]"` | Itera sobre cada container em `spec.containers` — exclui `initContainers` (campo separado) |
| `(name): "{{ element.name }}"` | Anchor de matching — instrui o strategic merge a aplicar o patch no container com aquele nome específico, não em todos |
| `+(campo): valor` | Anchor de adição condicional — insere o campo **apenas se ele não estiver declarado**; respeita valores já existentes no manifest |
| `patchStrategicMerge` | Mecanismo de patch que entende a semântica do Kubernetes (arrays de containers têm chave `name`) |

**Escopo técnico da policy:** a regra itera sobre `spec.containers[]`. Os `initContainers[]` não são mutados por esta policy; nesta etapa o aceite foi validado nos containers principais e no pod de teste criado sem `securityContext`.

**Por que `+()` e não o campo direto?** `+(runAsNonRoot): true` adiciona se ausente; se o manifest já tiver `runAsNonRoot: false` (caso específico de um container que explicitamente precisa de comportamento diferente), o valor é preservado. `runAsNonRoot: true` sem `+` sobrescreveria sempre, podendo quebrar casos de uso legítimos.

**Fluxo de admissão — por que Mutate roda antes de Validate:**

```
kubectl apply
    ↓
kube-apiserver
    ↓
[Mutating Webhooks]  ← Kyverno Mutate injeta securityContext
    ↓
[Validating Webhooks] ← Kyverno Validate checa o recurso já mutado
    ↓
etcd
```

A policy `disallow-root-user` da Etapa 4.1 valida que `runAsUser ≠ 0`. Com o Mutate rodando primeiro, o securityContext chega ao webhook de validação já com os campos corretos — as duas layers se complementam.

```bash
kubectl apply -f k8s/kyverno/mutate-security-context.yaml
# clusterpolicy.kyverno.io/mutate-security-context created

kubectl get cpol mutate-security-context
# NAME                      ADMISSION   BACKGROUND   READY   AGE   MESSAGE
# mutate-security-context   true        true         True    28s   Ready
```

**Autogen do Kyverno:** assim como na Etapa 4.1, o Kyverno gerou automaticamente as regras equivalentes para `Deployment`, `StatefulSet`, `DaemonSet`, `Job`, `CronJob` — visíveis em `kubectl describe cpol mutate-security-context` na seção `Status.Autogen`.

---

#### Passo 3 — Teste de mutação com pod simples

```bash
kubectl run teste-mutate \
  --image=felipestaypuff/tipsbank-api-contas:v1.0.0 \
  --restart=Never \
  -n tipsbank-contas
# pod/teste-mutate created

kubectl get pod teste-mutate -n tipsbank-contas \
  -o jsonpath='{.spec.containers[0].securityContext}' | jq
```

**Output:**
```json
{
  "allowPrivilegeEscalation": false,
  "readOnlyRootFilesystem": true,
  "runAsNonRoot": true
}
```

O manifest do pod `teste-mutate` não declarou nenhum `securityContext`. Todos os 3 campos foram injetados pelo Kyverno antes de chegar ao etcd — transparente para quem fez o deploy.

```bash
kubectl delete pod teste-mutate -n tipsbank-contas
# pod "teste-mutate" deleted
```

---

#### Passo 4 — Rollout restart em todos os deployments

O Kyverno Mutate só age em requisições novas (CREATE/UPDATE). Pods já em Running não são afetados retroativamente. Para que os workloads existentes recebam a injeção, é necessário recriar os pods via `rollout restart`.

```bash
kubectl rollout restart deployment/api-contas -n tipsbank-contas
kubectl rollout status deployment/api-contas -n tipsbank-contas
# Waiting for deployment "api-contas" rollout to finish: 1 old replicas are pending termination...
# deployment "api-contas" successfully rolled out

kubectl rollout restart deployment/auditoria -n tipsbank-auditoria
kubectl rollout status deployment/auditoria -n tipsbank-auditoria
# deployment "auditoria" successfully rolled out

kubectl rollout restart deployment/api-transacoes -n tipsbank-transacoes
kubectl rollout status deployment/api-transacoes -n tipsbank-transacoes
# deployment "api-transacoes" successfully rolled out
```

**Por que auditoria não quebra com `readOnlyRootFilesystem: true`?**

A auditoria escreve em `/data` — mas `/data` é um **volume NFS montado separadamente** (PVC `auditoria-pvc`). O root filesystem do container (`/`) fica read-only. Volumes externos (PVC, emptyDir, ConfigMap) possuem suas próprias permissões independentes do root filesystem.

---

#### Passo 5 — Web deployment: `emptyDir` para `/tmp` (nginx)

O nginx-unprivileged escreve arquivos temporários em `/tmp` (`nginx.pid`, `proxy_temp`, etc.). Com `readOnlyRootFilesystem: true` injetado, o container falhou ao tentar criar esses arquivos.

**Fix**: montar um `emptyDir` em `/tmp` no web deployment:

```yaml
containers:
  - name: web
    volumeMounts:
      - name: tmp-dir
        mountPath: /tmp    # ← necessário para nginx com readOnlyRootFilesystem
volumes:
  - name: tmp-dir
    emptyDir: {}
```

```bash
kubectl apply -f k8s/tipsbank-web/web-deployment.yaml
kubectl rollout restart deployment/web -n tipsbank-web
# deployment "web" successfully rolled out

curl -sk https://tipsbank.staypuff.info/healthz
# ok
```

`emptyDir` existe enquanto o pod existe e é descartado quando o pod morre — adequado para dados temporários do processo nginx.

---

#### Verificação final — securityContext injetado em produção

```bash
# api-contas (container sem securityContext no manifest original)
kubectl get pod -n tipsbank-contas -l app=api-contas \
  -o jsonpath='{.items[0].spec.containers[0].securityContext}' | jq
```
```json
{
  "allowPrivilegeEscalation": false,
  "readOnlyRootFilesystem": true,
  "runAsNonRoot": true
}
```

```bash
# api-transacoes log-forwarder (runAsUser declarado + campos injetados pelo Kyverno)
kubectl get pod -n tipsbank-transacoes -l app=api-transacoes \
  -o jsonpath='{.items[0].spec.containers[1].securityContext}' | jq
```
```json
{
  "allowPrivilegeEscalation": false,
  "readOnlyRootFilesystem": true,
  "runAsNonRoot": true,
  "runAsUser": 65532
}
```

```bash
# Estado final de todos os pods
kubectl get pod -n tipsbank-contas
# NAME                          READY   STATUS    RESTARTS   AGE
# api-contas-69dcd554b7-jbrpg   1/1     Running   0          40m
# api-contas-69dcd554b7-t8q98   1/1     Running   0          40m
# postgres-0                    1/1     Running   0          2d9h
# postgres-replica-0            1/1     Running   0          9d

kubectl get pod -n tipsbank-transacoes
# NAME                              READY   STATUS    RESTARTS   AGE
# api-transacoes-54fbdf557d-j8dh4   2/2     Running   0          38m
# api-transacoes-54fbdf557d-j94bw   2/2     Running   0          38m
# api-transacoes-54fbdf557d-nm4sr   2/2     Running   0          38m

kubectl get pod -n tipsbank-auditoria
# NAME                         READY   STATUS    RESTARTS   AGE
# auditoria-7b59664544-8bbmr   1/1     Running   0          39m
# auditoria-7b59664544-t7442   1/1     Running   0          40m

kubectl get pod -n tipsbank-web
# NAME                   READY   STATUS    RESTARTS   AGE
# web-8584b5698b-pqnjf   1/1     Running   0          15m
# web-8584b5698b-r54jp   1/1     Running   0          15m

# Estado final das 4 ClusterPolicies
kubectl get cpol
# NAME                      ADMISSION   BACKGROUND   READY   AGE     MESSAGE
# disallow-latest-tag       true        true         True    26h     Ready
# disallow-root-user        true        true         True    30h     Ready
# mutate-security-context   true        true         True    91m     Ready
# require-labels            true        true         True    25h     Ready
```

---

#### Problemas encontrados no caminho

##### Bug — `CreateContainerConfigError` no sidecar log-forwarder

**Sintoma**: Após aplicar o deployment sem `runAsUser` no log-forwarder com a policy de mutate já ativa, o pod ficou em estado misto: container `api-transacoes` `Running/Ready`, container `log-forwarder` em `Waiting/CreateContainerConfigError`.

**Diagnóstico** via `kubectl describe pod`:
```
Warning  Failed  kubelet  Error: container has runAsNonRoot and image will run as root
(pod: "api-transacoes-554f5844b6-zdk6k_tipsbank-transacoes", container: log-forwarder)
```

**Causa raiz**: O Kyverno injetou `runAsNonRoot: true` no log-forwarder. O container runtime (containerd) verificou o UID padrão da imagem `busybox:1.36` — que é UID 0 (root). Com `runAsNonRoot: true` e UID efetivo = 0, o runtime recusa iniciar o container — isso é um mecanismo de segurança do próprio Linux container runtime, não do Kubernetes.

**Impacto no rolling update**: Com `maxUnavailable: 0` e `maxSurge: 1`, o Kubernetes não derrubou os pods antigos enquanto os novos não ficassem Ready. O resultado foi um rolling update travado: o novo ReplicaSet tinha 1 pod em `1/2 Running` (log-forwarder aguardando), o antigo mantinha 3 pods running. Após vários `kubectl apply` e diagnóstico, o manifeste foi corrigido com `runAsUser: 65532` e o deployment funcionou.

**Fix aplicado**: `securityContext.runAsUser: 65532` no container `log-forwarder`. Após o fix, o rolling update completou com sucesso — confirmado em `kubectl get pod -n tipsbank-transacoes -w`.

---

#### Lição técnica: Mutate não retroage e não derruba pods existentes

O Kyverno Mutate age **exclusivamente em requisições de admission** (CREATE, UPDATE). Pods já em Running nunca passam novamente pelo webhook de admissão enquanto estão saudáveis.

Isso tem implicações práticas importantes em produção:
- Após criar uma policy de Mutate, os workloads existentes **não recebem** a injeção automaticamente
- O `kyverno-background-controller` faz **background scan** nos recursos existentes e gera `PolicyReport`, mas é **read-only** — não modifica nem mata pods
- Para garantir que todos os pods estejam com o securityContext injetado, é necessário `rollout restart` em cada deployment — o que recria os pods e faz cada novo pod passar pelo webhook de admissão

---

### Etapa 4.3 — Kyverno: Generate (NetworkPolicy automática por namespace)

**Data de conclusão:** 2026-05-23

#### Objetivo segundo o MANUAL-ALUNO.md

Quando qualquer namespace novo é criado no cluster, o Kyverno cria automaticamente uma `NetworkPolicy` `default-deny-ingress` nele. Uma segunda policy garante que apenas imagens do registry confiável (`felipestaypuff/*`) sejam permitidas nos namespaces TipsBank.

#### Critérios de aceite do manual

- `kubectl create ns novo-teste` gera automaticamente uma NetPol lá dentro
- Tentativa de usar imagem de registry externo (ex: `docker.io/nginx`) é rejeitada, mas `felipestaypuff/*` passa

#### Status dos critérios

| Critério | Status | Evidência |
|---|---|---|
| `create ns` gera NetPol automaticamente | **Atendido** | `kubectl get netpol -n teste-deny` → `default-deny-ingress` com 11s de AGE |
| Registry externo bloqueado | **Atendido** | `kubectl run --image=nginx:1.27` → admission webhook negou com `check-trusted-registry` |
| Registry próprio aceito | **Atendido** | `kubectl run --image=felipestaypuff/tipsbank-api-contas:v1.0.0` → `pod/teste-ok created` |
| 6 ClusterPolicies `READY=True` | **Atendido** | `kubectl get cpol` mostra 6 policies com `True` |

![[Captura de tela 2026-05-23 190213.png]]

---

#### Passo 1 — ClusterPolicy `generate-default-deny-netpol`

**Arquivo:** `k8s/kyverno/generate-default-deny-netpol.yaml`

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-default-deny-netpol
  labels:
    rule: generate-default-deny-netpol
    app.kubernetes.io/part-of: tipsbank
spec:
  rules:
    - name: generate-netpol-default-deny
      match:
        any:
          - resources:
              kinds:
                - Namespace
      generate:
        apiVersion: networking.k8s.io/v1
        kind: NetworkPolicy
        name: default-deny-ingress
        namespace: "{{request.object.metadata.name}}"
        synchronize: true
        data:
          metadata:
            labels:
              app.kubernetes.io/managed-by: kyverno
          spec:
            podSelector: {}
            policyTypes:
              - Ingress
```

**Anatomia técnica:**

| Campo | Significado |
|---|---|
| `kinds: Namespace` | Trigger: qualquer `CREATE Namespace` dispara esta rule |
| `namespace: "{{request.object.metadata.name}}"` | JMESPath: o namespace target é o nome do Namespace recém-criado |
| `synchronize: true` | Kyverno recria o recurso se deletado; atualiza se a policy mudar |
| `podSelector: {}` + `policyTypes: Ingress` sem regras | Default-deny all ingress |

**Por que `synchronize: true` importa em produção:** se alguém deletar a `NetworkPolicy` gerada, o Kyverno a recria automaticamente. Se a spec da policy for alterada (ex: adicionar Egress), todos os recursos gerados são atualizados em todos os namespaces. O recurso é "owned" pela policy — deletar a `cpol` remove todas as NetPols geradas.

```bash
kubectl apply -f k8s/kyverno/generate-default-deny-netpol.yaml
# clusterpolicy.kyverno.io/generate-default-deny-netpol created
```

---

#### Passo 2 — Teste da geração automática

```bash
kubectl create namespace teste-deny
# namespace/teste-deny created

kubectl get netpol -n teste-deny
# NAME                   POD-SELECTOR   AGE
# default-deny-ingress   <none>         11s

kubectl describe netpol default-deny-ingress -n teste-deny
# Name:         default-deny-ingress
# Namespace:    teste-deny
# Created on:   2026-05-23 16:43:13 -0300 -03
# Labels:       app.kubernetes.io/managed-by=kyverno
#               generate.kyverno.io/policy-name=generate-default-deny-netpol
#               generate.kyverno.io/trigger-kind=Namespace
#               generate.kyverno.io/trigger-uid=4dd93e42-ece9-406d-9465-470ab0030743
# Spec:
#   PodSelector:     <none> (isolates all pods)
#   Allowing ingress traffic: <none> (Selected pods are isolated for ingress connectivity)
#   Not affecting egress traffic
#   Policy Types: Ingress

kubectl delete namespace teste-deny
# namespace "teste-deny" deleted
```

**Nota importante:** namespaces existentes (`tipsbank-contas`, etc.) não recebem a policy retroativamente. O Generate reage apenas a eventos `CREATE` novos — as NetPols manuais da Etapa 2.5 continuam válidas para os namespaces já existentes.

---

#### Passo 3 — ClusterPolicy `allow-trusted-registry`

**Arquivo:** `k8s/kyverno/allow-trusted-registry.yaml`

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: allow-trusted-registry
  labels:
    rule: allow-trusted-registry
    app.kubernetes.io/part-of: tipsbank
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-trusted-registry
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - tipsbank-contas
                - tipsbank-transacoes
                - tipsbank-auditoria
                - tipsbank-web
      validate:
        message: "Imagem nao vem de registry confiavel. Use felipestaypuff/* ou busybox:*."
        foreach:
          - list: "request.object.spec.containers[]"
            deny:
              conditions:
                all:
                  - key: "{{ element.image }}"
                    operator: NotIn
                    value:
                      - "felipestaypuff/*"
                      - "busybox:*"
          - list: "request.object.spec.initContainers[]"
            deny:
              conditions:
                all:
                  - key: "{{ element.image }}"
                    operator: NotIn
                    value:
                      - "felipestaypuff/*"
                      - "busybox:*"
```

**Por que dois `foreach`:** `spec.containers[]` e `spec.initContainers[]` são listas independentes no Pod spec. Os deployments TipsBank usam `busybox:1.36` como initContainer — sem o segundo foreach, qualquer imagem passaria como initContainer sem validação.

**Como o glob matching funciona:** `felipestaypuff/*` (com `/*`) é um glob que bate em qualquer imagem do usuário. `felipestaypuff` sem o `/*` é literal e não bate em nenhuma imagem com namespace. `busybox:*` cobre qualquer tag do busybox.

```bash
kubectl apply -f k8s/kyverno/allow-trusted-registry.yaml
# clusterpolicy.kyverno.io/allow-trusted-registry created
```

---

#### Passo 4 — Teste de bloqueio e permissão

```bash
# BLOQUEADO — nginx não está nos registries confiáveis
kubectl run teste-registry \
  --image=nginx:1.27 \
  --restart=Never \
  -n tipsbank-contas
# Error from server: admission webhook "validate.kyverno.svc-fail" denied the request:
# resource Pod/tipsbank-contas/teste-registry was blocked due to the following policies
# allow-trusted-registry:
#   check-trusted-registry: 'validation error: Imagem nao vem de registry confiavel.
#     Use felipestaypuff/* ou busybox:*. rule check-trusted-registry failed at path
#     /spec/containers/0/image/'

# PERMITIDO — felipestaypuff/* está na lista
kubectl run teste-ok \
  --image=felipestaypuff/tipsbank-api-contas:v1.0.0 \
  --restart=Never \
  -n tipsbank-contas
# pod/teste-ok created

kubectl delete pod teste-ok -n tipsbank-contas
# pod "teste-ok" deleted
```

---

#### Verificação final — 6 ClusterPolicies ativas

```bash
kubectl get cpol
# NAME                           ADMISSION   BACKGROUND   READY   AGE     MESSAGE
# allow-trusted-registry         true        true         True    91s     Ready
# disallow-latest-tag            true        true         True    3h35m   Ready
# disallow-root-user             true        true         True    3h35m   Ready
# generate-default-deny-netpol   true        true         True    137m    Ready
# mutate-security-context        true        true         True    3h35m   Ready
# require-labels                 true        true         True    3h35m   Ready

# Confirmar que namespaces existentes NÃO receberam a NetPol gerada
kubectl get netpol -n tipsbank-contas
# NAME                               POD-SELECTOR     AGE
# allow-api-contas-to-postgres       app=api-contas   18d
# allow-dns-egress-contas            <none>           18d
# allow-ingress-to-api-contas        app=api-contas   18d
# allow-ingress-to-postgres          app=postgres     18d
# allow-locust-ingress-to-contas     app=api-contas   2d
# allow-prometheus-tipsbank-contas   app=api-contas   9d
# default-deny-all                   <none>           18d
# (sem default-deny-ingress gerada pelo Kyverno — namespace é pré-existente)

# Confirmar que namespace novo recebe NetPol automática
kubectl create ns teste-final-4-3
kubectl get netpol -n teste-final-4-3
# NAME                   POD-SELECTOR   AGE
# default-deny-ingress   <none>         6s
kubectl delete ns teste-final-4-3
```

---

#### Problema encontrado no caminho

##### Bug — `variable 'element.image' present outside of foreach` na validação da policy

**Sintoma**: `kubectl apply -f k8s/kyverno/allow-trusted-registry.yaml` retornou erro de admission do próprio Kyverno (o webhook `validate-policy.kyverno.svc` valida as ClusterPolicies antes de persistir).

```
Error from server: admission webhook "validate-policy.kyverno.svc" denied the request:
variable 'element.image' present outside of foreach at path /validate/message
```

**Causa raiz**: O campo `validate.message` estava usando `{{ element.image }}` como variável dinâmica. Mas `element` é uma variável de contexto que só existe **dentro** do bloco `foreach` — no nível da iteração de cada item da lista. O `message` fica no escopo da regra inteira, fora do foreach, onde `element` não existe.

**Fix**: substituir `{{ element.image }}` por texto estático na `message`:
```yaml
# ERRADO
message: "Imagem '{{ element.image }}' nao vem de registry confiavel."

# CORRETO
message: "Imagem nao vem de registry confiavel. Use felipestaypuff/* ou busybox:*."
```

`{{ element.image }}` dentro do bloco `conditions` (dentro do foreach) continua correto — lá ele tem o contexto da iteração.

---

#### Lição técnica: Generate vs Mutate vs Validate — onde cada um age

```
kubectl apply / kubectl create
        ↓
kube-apiserver
        ↓
[Mutating Webhooks]    ← Kyverno Mutate: modifica o recurso antes de gravar
        ↓
[Validating Webhooks]  ← Kyverno Validate: aceita ou rejeita o recurso
        ↓
etcd  ←————————  Kyverno Generate: lê o evento persistido e cria recursos novos
```

O Generate é o único que não age no pipeline de admissão. Ele é assíncrono — o Kyverno Background Controller observa eventos no etcd e reage a eles criando novos recursos. Por isso ele não pode rejeitar a criação do namespace (só pode criar coisas em resposta a ela).

---

### Etapa 4.4 — RBAC: 4 perfis com certificados X.509

**Data de conclusão:** 2026-05-24

#### Objetivo segundo o MANUAL-ALUNO.md

Criar 4 usuários humanos com certificado X.509 assinado pela CA do cluster, cada um com permissões distintas via Role/ClusterRole. Gerar um kubeconfig por usuário. Adicionar 2 ServiceAccounts (uma por API).

#### Critérios de aceite do manual

- `kubectl --kubeconfig=op-contas.kubeconfig get pods -n tipsbank-contas` → 200
- `kubectl --kubeconfig=op-contas.kubeconfig get pods -n tipsbank-transacoes` → **Forbidden**
- `kubectl --kubeconfig=auditor.kubeconfig get pods -A` → lista todos
- `kubectl --kubeconfig=auditor.kubeconfig delete pod X` → **Forbidden** (readonly)

#### Status dos critérios

| Critério | Status | Evidência |
|---|---|---|
| operador-contas lista pods em tipsbank-contas | **Atendido** | Output 1 — 4 pods listados |
| operador-contas bloqueado em tipsbank-transacoes | **Atendido** | Output 2 — Forbidden |
| auditor-global lista todos os namespaces | **Atendido** | Output 3 — `get pods -A` retorna todos |
| auditor-global bloqueado ao deletar pod | **Atendido** | Output 4 — Forbidden |
| sre com acesso cluster-admin | **Atendido** | Output 5 — `get nodes` retorna os 3 nodes |
| ServiceAccounts criadas | **Atendido** | Output 6 — `api-contas-sa` e `api-transacoes-sa` |
| 4 kubeconfigs gerados em k8s/rbac/kubeconfigs/ | **Atendido** | Output 7 — `ll` mostra os 4 arquivos |

---

#### Output 1 — kubectl apply -f k8s/rbac (todos os recursos criados)

```
k apply -f k8s/rbac
clusterrole.rbac.authorization.k8s.io/auditor-global created
clusterrolebinding.rbac.authorization.k8s.io/auditor-global created
role.rbac.authorization.k8s.io/operador-contas created
role.rbac.authorization.k8s.io/operador-transacoes created
rolebinding.rbac.authorization.k8s.io/operador-contas created
rolebinding.rbac.authorization.k8s.io/operador-transacoes created
serviceaccount/api-contas-sa created
serviceaccount/api-transacoes-sa created
error: error validating "k8s/rbac/clusterrolebinding-sre.yaml": error validating data: apiVersion not set
```

*(1ª aplicação falhou no sre — apiVersion faltando. Corrigido e reaplicado:)*

```
k apply -f k8s/rbac
clusterrole.rbac.authorization.k8s.io/auditor-global unchanged
clusterrolebinding.rbac.authorization.k8s.io/auditor-global unchanged
clusterrolebinding.rbac.authorization.k8s.io/sre created
role.rbac.authorization.k8s.io/operador-contas unchanged
role.rbac.authorization.k8s.io/operador-transacoes unchanged
rolebinding.rbac.authorization.k8s.io/operador-contas unchanged
rolebinding.rbac.authorization.k8s.io/operador-transacoes unchanged
serviceaccount/api-contas-sa unchanged
serviceaccount/api-transacoes-sa unchanged
```

---

#### Output 2 — operador-contas: acesso permitido em tipsbank-contas

```
k --kubeconfig=k8s/rbac/kubeconfigs/op-contas.kubeconfig get pods -n tipsbank-contas
NAME                          READY   STATUS    RESTARTS       AGE
api-contas-6f7f9d6c64-256ph   1/1     Running   1 (106m ago)   28h
api-contas-6f7f9d6c64-9m765   1/1     Running   1 (103m ago)   28h
postgres-0                    1/1     Running   1 (106m ago)   25h
postgres-replica-0            1/1     Running   4 (103m ago)   3d22h
```

**Resultado:** 4 pods listados ✅ — Role `operador-contas` funcionando no namespace correto.

---

#### Output 3 — operador-contas: Forbidden em tipsbank-transacoes

```
k --kubeconfig=k8s/rbac/kubeconfigs/op-contas.kubeconfig get pods -n tipsbank-transacoes
Error from server (Forbidden): pods is forbidden: User "operador-contas" cannot list resource "pods" in API group "" in the namespace "tipsbank-transacoes"
```

**Resultado:** Isolamento de namespace funcional ✅ — Role scoped apenas a `tipsbank-contas`.

---

#### Output 4 — auditor-global: get pods -A (acesso cluster-wide readonly)

```
k --kubeconfig=k8s/rbac/kubeconfigs/auditor.kubeconfig get pods -A
NAMESPACE             NAME                                                       READY   STATUS    RESTARTS
calico-system         calico-kube-controllers-597ff8fcc5-ttv4v                   1/1     Running   2
calico-system         calico-node-b58jm                                          1/1     Running   16
...
tipsbank-contas       api-contas-6f7f9d6c64-256ph                                1/1     Running   1
tipsbank-contas       api-contas-6f7f9d6c64-9m765                                1/1     Running   1
tipsbank-contas       postgres-0                                                 1/1     Running   1
tipsbank-contas       postgres-replica-0                                         1/1     Running   4
tipsbank-transacoes   api-transacoes-776f74779b-422h4                            2/2     Running   2
tipsbank-transacoes   api-transacoes-776f74779b-h5ntm                            2/2     Running   2
tipsbank-transacoes   api-transacoes-776f74779b-ssdrb                            2/2     Running   7
tipsbank-web          web-8584b5698b-pqnjf                                       1/1     Running   4
tipsbank-web          web-8584b5698b-r54jp                                       1/1     Running   4
[... todos os namespaces listados]
```

**Resultado:** ClusterRole `auditor-global` com acesso de leitura em todos os namespaces ✅

---

#### Output 5 — auditor-global: Forbidden ao tentar deletar

```
k --kubeconfig=k8s/rbac/kubeconfigs/auditor.kubeconfig delete pod -n tipsbank-contas postgres-0
Error from server (Forbidden): pods "postgres-0" is forbidden: User "auditor-global" cannot delete resource "pods" in API group "" in the namespace "tipsbank-contas"
```

**Resultado:** ClusterRole readonly funcionando — `delete` não está nos verbos permitidos ✅

---

#### Output 6 — sre: acesso cluster-admin (get nodes)

```
k --kubeconfig=k8s/rbac/kubeconfigs/sre.kubeconfig get nodes
NAME         STATUS   ROLES           AGE   VERSION
tb-master1   Ready    control-plane   28d   v1.35.4
tb-worker1   Ready    worker          28d   v1.35.4
tb-worker2   Ready    worker          28d   v1.35.4
```

**Resultado:** ClusterRoleBinding `sre` → `cluster-admin` funcionando ✅

---

#### Output 7 — ServiceAccounts criadas

```
kubectl get sa -n tipsbank-contas api-contas-sa
NAME            AGE
api-contas-sa   59m

kubectl get sa -n tipsbank-transacoes api-transacoes-sa
NAME                AGE
api-transacoes-sa   60m
```

**Resultado:** 2 ServiceAccounts criadas, uma por namespace de API ✅

---

#### Output 8 — kubeconfigs gerados (ls k8s/rbac/kubeconfigs/)

```
cd k8s/rbac/kubeconfigs && ll
.rwxrwxrwx 5.6k felipe 24 May 17:34  auditor.kubeconfig
.rwxrwxrwx 5.7k felipe 24 May 17:34  op-contas.kubeconfig
.rwxrwxrwx 5.7k felipe 24 May 17:34  op-transacoes.kubeconfig
.rwxrwxrwx 5.6k felipe 24 May 17:34  sre.kubeconfig
```

**Resultado:** 4 kubeconfigs com cert+chave embutidos (embed-certs=true), em `k8s/rbac/kubeconfigs/` ✅

---

#### Bug encontrado no caminho

**Sintoma:** `k apply -f k8s/rbac` retornou erro somente no `clusterrolebinding-sre.yaml`:

```
error: error validating "k8s/rbac/clusterrolebinding-sre.yaml": error validating data: apiVersion not set
```

**Causa raiz:** O heredoc do `clusterrolebinding-sre.yaml` foi criado com `apiVersion` faltando no campo `apiVersion:` — provavelmente erro de digitação no `cat > ... << 'EOF'` onde o campo ficou vazio ou com espaço em branco.

**Fix:** Corrigir o YAML adicionando `apiVersion: rbac.authorization.k8s.io/v1` e reaplicar. Os outros 8 recursos já existiam (`unchanged`) — somente o `sre` foi criado na segunda passagem.

Git commit: `semana 4.4 correção ClusterRollingBind-sre`

---

#### Recursos criados na etapa

| Tipo | Nome | Namespace |
|---|---|---|
| Role | `operador-contas` | `tipsbank-contas` |
| Role | `operador-transacoes` | `tipsbank-transacoes` |
| RoleBinding | `operador-contas` | `tipsbank-contas` |
| RoleBinding | `operador-transacoes` | `tipsbank-transacoes` |
| ClusterRole | `auditor-global` | cluster-wide |
| ClusterRoleBinding | `auditor-global` | cluster-wide |
| ClusterRoleBinding | `sre` → `cluster-admin` | cluster-wide |
| ServiceAccount | `api-contas-sa` | `tipsbank-contas` |
| ServiceAccount | `api-transacoes-sa` | `tipsbank-transacoes` |

Arquivos em `k8s/rbac/` commitados em 4 commits separados por tipo de recurso.

---

### Etapa 4.5 — Helm Chart Umbrella

**Data de conclusão:** 2026-06-01

#### Objetivo segundo o MANUAL-ALUNO.md

Um único `helm install tipsbank` sobe o banco inteiro (app + monitoring + policies + RBAC) num cluster vazio. Publicar o chart como OCI no ghcr.io.

#### Critérios de aceite do manual

- `helm lint` passa limpo
- `helm template` renderiza todos os manifests corretamente
- Instalação num cluster limpo sobe **tudo** em menos de 10 min
- `helm upgrade` funciona sem derrubar tráfego (rolling update preservado)
- `helm rollback` também
- Chart publicado num repositório remoto acessível

#### Status dos critérios

| Critério | Status | Evidência |
|---|---|---|
| `helm lint` passa limpo | **Atendido** | `1 chart(s) linted, 0 chart(s) failed` |
| `values.yaml` com registry, réplicas e tags parametrizados | **Atendido** | `helm template -f values-prod.yaml` → imagens com tag v1.0.0/v2.0.0 |
| `values-dev.yaml` → replicas=1 e tags dev | **Atendido** | `helm template -f values-dev.yaml` → replicas: 1, tag: dev |
| `values-prod.yaml` → replicas=2 e tags prod | **Atendido** | `helm template -f values-prod.yaml` → replicas: 2 |
| log-forwarder condicional desabilitado em dev | **Atendido** | `grep "log-forwarder"` → não aparece como container |
| Chart publicado OCI no ghcr.io | **Atendido** | `helm show chart oci://ghcr.io/felipesoaresti/helm-charts/tipsbank --version 1.0.0` |

---

#### Output 1 — helm lint limpo

```
helm lint .
==> Linting .
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

---

#### Output 2 — helm template -f values-dev.yaml

```
helm template tipsbank . -f values-dev.yaml | grep -E "replicas:|image:"
          image: busybox:1.36
  replicas: 1
          image: docker.io/felipestaypuff/tipsbank-auditoria:dev
  replicas: 1
          image: busybox:1.36
          image: docker.io/felipestaypuff/tipsbank-api-contas:dev
  replicas: 1
          image: busybox:1.36
          image: busybox:1.36
          image: docker.io/felipestaypuff/tipsbank-api-transacoes:dev
  replicas: 1
          image: busybox:1.36
          image: busybox:1.36
          image: busybox:1.36
          image: docker.io/felipestaypuff/tipsbank-web:dev
  replicas: 1
          image: postgres:16-alpine
  replicas: 1
          image: postgres:16-alpine
```

---

#### Output 3 — helm template -f values-prod.yaml

```
helm template tipsbank . -f values-prod.yaml | grep -E "replicas:|image:"
          image: busybox:1.36
  replicas: 2
          image: docker.io/felipestaypuff/tipsbank-auditoria:v1.0.0
  replicas: 2
          image: busybox:1.36
          image: docker.io/felipestaypuff/tipsbank-api-contas:v1.0.0
  replicas: 2
          image: busybox:1.36
          image: busybox:1.36
          image: docker.io/felipestaypuff/tipsbank-api-transacoes:v2.0.0
          image: busybox:1.36
  replicas: 2
          image: busybox:1.36
          image: busybox:1.36
          image: busybox:1.36
          image: docker.io/felipestaypuff/tipsbank-web:v1.0.0
  replicas: 1
          image: postgres:16-alpine
  replicas: 1
          image: postgres:16-alpine
```

---

#### Output 4 — sidecar log-forwarder condicional (desabilitado em dev)

```
helm template tipsbank . -f values-dev.yaml | grep "log-forwarder"
        container: api-transacoes # exclui o sidecar log-forwarder
                container!~"log-forwarder|init-.*"
# → aparece apenas em comentários de PrometheusRule/Kyverno — NÃO como container
```

---

#### Output 5 — Publicação OCI e verificação

```
helm push tipsbank-1.0.0.tgz oci://ghcr.io/felipesoaresti/helm-charts
# Pushed: ghcr.io/felipesoaresti/helm-charts/tipsbank:1.0.0
# Digest: sha256:7416d94e4bd99a7cb25e65028d08749eee04beb622263b33f41fc5b274c04c85

helm show chart oci://ghcr.io/felipesoaresti/helm-charts/tipsbank --version 1.0.0
Pulled: ghcr.io/felipesoaresti/helm-charts/tipsbank:1.0.0
Digest: sha256:7416d94e4bd99a7cb25e65028d08749eee04beb622263b33f41fc5b274c04c85
apiVersion: v2
appVersion: 1.0.0
description: TipsBank — Banco Digital da Linuxtips - Projeto Final DK8S
name: tipsbank
type: application
version: 1.0.0
```

**Package público:** https://github.com/users/felipesoaresti/packages/container/helm-charts%2Ftipsbank

---

#### Bugs encontrados no caminho

##### Bug 1 — `function "element" not defined` em mutate-security-context.yaml:32

**Causa:** O Kyverno usa `{{ element.name }}` como JMESPath. O Helm processa tudo em `templates/` como Go template — tentou executar `element` como função Go, que não existe.

**Fix:** Escapar com `{{ "{{" }} element.name {{ "}}" }}` — o Helm renderiza isso como o literal `{{ element.name }}` que o Kyverno lê corretamente.

##### Bug 2 — `undefined variable "$labels"` em prometheusrule-tipsbank-slo.yaml

**Causa:** PrometheusRule usa `{{ $labels.deployment }}` e `{{ $value | humanizeDuration }}` nas annotations — novamente o Helm tentando executar `$labels` como variável Go.

**Fix:** Mesmo padrão de escape: `{{ "{{" }} $labels.deployment {{ "}}" }}`.

##### Bug 3 — `nil pointer evaluating interface {}.enabled` em NOTES.txt:2

**Causa:** O scaffold do `helm create` gerou um `NOTES.txt` referenciando `.Values.httpRoute.enabled`, `.Values.ingress.enabled`, `.Values.service.type` — todos removidos quando o `values.yaml` foi reescrito para TipsBank.

**Fix:** Substituir todo o conteúdo do NOTES.txt por texto específico do TipsBank.

##### Bug 4 — `invalid map key` em postgres-statefull.yaml (e 3 Deployments)

**Causa:** `replicas: { { .Values.postgres.image } }` — espaços dentro das chaves. O Helm exige `{{` sem espaço. Com espaço, o YAML trata como mapa literal, não como template.

**Fix:** `sed -i 's/{ { /{{ /g; s/ } }/}}/g'` nos 4 arquivos afetados.

##### Bug 5 — 403 `owner not found` no `helm push` para ghcr.io

**Causa:** `helm registry login ghcr.io -u felipestaypuff` — username errado. O Docker Hub usa `felipestaypuff`, mas o GitHub (ghcr.io) usa `felipesoaresti`. São registries completamente independentes.

**Fix:** Re-login com `-u felipesoaresti` + push para `oci://ghcr.io/felipesoaresti/helm-charts`.

---

#### Lição técnica: Go template engine vs Kyverno/Prometheus templates

O Helm renderiza TUDO dentro de `templates/` como Go template. Qualquer `{{ }}` é interpretado — seja Kyverno JMESPath, PrometheusRule annotation ou qualquer texto com chaves duplas.

A solução é o padrão de escape:
```
{{ "{{" }} expressão {{ "}}" }}
```
O Helm avalia `{{ "{{" }}` como a string literal `{{`, e `{{ "}}" }}` como `}}`. O YAML resultante entregue ao Kubernetes contém `{{ expressão }}` exatamente como Kyverno/Prometheus esperam.

Detalhes completos da estrutura e passos em [[Semana-4/Etapa-4.5-Helm-Umbrella]].

---

#### Complemento da Etapa 4.5 — Validação em cluster limpo (`tb-lab-master`) + correção para 1.0.1

**Data:** 2026-06-09

O manual não para em `helm lint` e `helm template`: ele pede install real em cluster limpo, upgrade sem derrubar tráfego, rollback e chart publicado. Então a versão `1.0.0`, que já passava nos testes estáticos, foi validada num cluster dedicado (`tb-lab-master`). Aí apareceram 5 bugs que só surgem quando o Kubernetes tenta criar os recursos de verdade. Foram corrigidos e publicados na versão `1.0.1`.

##### Cluster de teste

```
$ ssh tb-lab-master 'kubectl get nodes -o wide'
NAME             STATUS   ROLES           AGE   VERSION   INTERNAL-IP
tp-lab-master    Ready    control-plane   ~4h   v1.35.5   192.168.3.44
tp-lab-worker1   Ready    <none>          ~4h   v1.35.5   192.168.3.45
tp-lab-worker2   Ready    <none>          ~4h   v1.35.5   192.168.3.46
```

Pré-requisitos já instalados via Helm (operators/CRDs que o chart consome): `kyverno`, `kube-prometheus-stack` (ns `tipsbank-monitoring`), `ingress-nginx`, `csi-driver-nfs`, `metallb`. StorageClasses do cluster: `nfs-retain`, `nfs-delete` (provisioner `nfs.csi.k8s.io`, server `192.168.3.11:/mnt/nfs-data/k8s`).

> **Conclusão sobre "cluster limpo":** não pode ser literalmente vazio — o chart depende de CRDs externos (`ClusterPolicy` Kyverno, `ServiceMonitor`/`PrometheusRule` Prometheus) e de uma StorageClass NFS. "Limpo" = com os operators/CRDs presentes, **sem** o app TipsBank.

##### Problemas encontrados no install limpo da 1.0.0 e soluções

| # | Bug | Sintoma | Correção (1.0.1) |
|---|---|---|---|
| 1 | `allow-trusted-registry` (Enforce) não libera `postgres:*` e o glob `felipestaypuff/*` não casa `docker.io/felipestaypuff/*` | `FailedCreate ... validate.kyverno.svc-fail denied`; PolicyViolation em todas as imagens. Só não quebrou no install porque Helm aplica a policy **depois** dos workloads → qualquer restart/drain seria bloqueado | glob `"*felipestaypuff/* \| postgres:* \| busybox:*"` |
| 2 | postgres sem `PGDATA` em subdir, PVC montado direto em `/var/lib/postgresql/data` | `initdb: could not change permissions of directory ... Operation not permitted` (chmod da raiz do mount NFS) → CrashLoopBackOff | `env: PGDATA=/var/lib/postgresql/data/pgdata` |
| 3 | `auditoria.pvc.storageClass` era value morto (template hardcodava `nfs-tp-data`) | override ignorado | template fiado: `storageClassName: {{ .Values.auditoria.pvc.storageClass }}` |
| 4 | `postgres-statefull-replica.yaml` (resíduo da 4.5) hardcodava `nfs-tp-data`, não parametrizado | PVC Pending | arquivo removido |
| 5 | default `postgres.pvc.storageClass: nfs-homelab` não-portável | PVC Pending em cluster novo | `values-lab.yaml` por ambiente (override `nfs-retain`) |

##### Ajustes de cluster necessários

- **Webhook Kyverno em timeout no burst:** `validate-policy.kyverno.svc` com `timeoutSeconds=10` e `failurePolicy=Fail`; o burst de ~88 recursos satura o admission controller single-replica → a criação de uma das 6 ClusterPolicies estourava (`context deadline exceeded`), reproduzível. Mitigação: admission controller **2 réplicas** + webhook **30s**. (Config do cluster Kyverno, não do chart.)
- StorageClass `nfs-tp-data` (que o chart espera para a auditoria) não existia → criada como clone do `nfs-retain`.

##### Bug que travou o `helm package` da 1.0.1

```
$ helm lint .
[ERROR] templates/postgres/postgres-statefull.yaml: unable to parse YAML:
  yaml: invalid map key: map[interface {}]interface {}{".Values.postgres.image":...}
```

Causa: um editor com *format-on-save* (Prettier/extensão YAML) "embelezou" `{{ }}` para `{ { } }` nas linhas templated. O Helm deixou de enxergar Go template e o parser YAML passou a tratar aquilo como mapa inválido. Correção aplicada: restaurar `{{ }}` e evitar formatador YAML automático nesses manifests Helm.

##### Evidência — install limpo 1.0.1

```
$ helm install tipsbank oci://ghcr.io/felipesoaresti/helm-charts/tipsbank --version 1.0.1 \
    --set postgres.pvc.storageClass=nfs-retain
NAME: tipsbank   STATUS: deployed   REVISION: 1     # 23s
$ kubectl get cpol --no-headers | wc -l
6

# 10/10 pods Running em ~2m20s (install + ready ~3 min, dentro dos 10 min)
tipsbank-contas       postgres-0                    1/1   Running
tipsbank-contas       api-contas (x2)               1/1   Running
tipsbank-transacoes   api-transacoes (x3)           2/2   Running   # c/ sidecar log-forwarder
tipsbank-auditoria    auditoria (x2)                1/1   Running
tipsbank-web          web (x2)                      1/1   Running
```

##### Evidência — compliance sem violações nos namespaces da aplicação

```
$ for ns in tipsbank-contas tipsbank-transacoes tipsbank-auditoria tipsbank-web; do
    echo "$ns: fail=$(kubectl get policyreport -n $ns -o jsonpath='...summary.fail...')"; done
tipsbank-contas: fail=0
tipsbank-transacoes: fail=0
tipsbank-auditoria: fail=0
tipsbank-web: fail=0
```

##### Evidência — Postgres sobrevive a restart com policy ativa

```
$ kubectl delete pod -n tipsbank-contas postgres-0
$ # recriado e READY em ~30s — NÃO bloqueado pelo allow-trusted-registry; PGDATA subdir reusa o data dir
postgres-0   1/1   Running   0   37s
```

##### Evidência — `helm upgrade` rolling e `helm rollback`

```
$ helm upgrade tipsbank oci://.../tipsbank --version 1.0.1 \
    --set postgres.pvc.storageClass=nfs-retain --set web.replicas=3
STATUS: deployed   REVISION: 2        # web 2->3 rolling, sem derrubar tráfego

$ helm rollback tipsbank 1
Rollback was a success! Happy Helming!

$ helm history tipsbank
1   superseded   Install complete
2   superseded   Upgrade complete
3   deployed     Rollback to 1        # web volta a 2/2; tudo Running

# estado final pós-rollback: api-contas 2/2, postgres 1/1, api-transacoes 3/3, web 2/2
```

##### Critérios de aceite da 4.5 — status final

| Critério | Resultado |
|---|---|
| `helm lint` limpo | **Atendido** |
| `helm template` renderiza todos os manifests | **Atendido** — 88 recursos renderizados |
| Instala em cluster limpo em menos de 10 min | **Atendido** — cerca de 3 min |
| `helm upgrade` sem derrubar tráfego | **Atendido** — rolling update preservado |
| `helm rollback` funcional | **Atendido** — revision 3 voltou para a revision 1 |
| Chart publicado em repositório remoto acessível | **Atendido** — `ghcr.io/felipesoaresti/helm-charts/tipsbank:1.0.1` |

Conclusão técnica: a `1.0.0` provava que o chart renderizava; a `1.0.1` provou que ele instala, opera, faz upgrade e faz rollback num cluster sem TipsBank preexistente. É exatamente o tipo de evidência que o critério do manual queria pegar.

---

### Etapa 4.6 — Teste de Compliance Final

**Data de conclusão:** 2026-06-09

#### Objetivo segundo o MANUAL-ALUNO.md

Rodar uma checklist de compliance como se fosse auditoria: imagem confiável, nenhum pod root, probes, resources, Kyverno ativo, NetworkPolicies presentes e imagens assinadas. Também registrar 3 manifestos ruins bloqueados pelo Kyverno e documentar a nuance do `web`.

#### Critérios de aceite do manual

- Os 7 comandos de compliance colados no `EVIDENCIAS.md` com saída esperada.
- Registro de 3 tentativas de aplicar manifest ruim e ver o Kyverno bloqueando.
- Nuance do `web` documentada: nonroot/minimal, mas não Distroless no sentido estrito.

#### Status dos critérios

Checklist rodada nos dois clusters: lab `tb-lab-master` (Helm `1.0.1`) e prod `tb-master1` (ambiente construído nas semanas anteriores). O foco foi nos namespaces da aplicação: `tipsbank-contas`, `tipsbank-transacoes`, `tipsbank-auditoria` e `tipsbank-web`.

| Critério | Lab | Prod | Status |
|---|---|---|---|
| Imagens de registry confiável | nenhuma fora do padrão aceito | nenhuma fora do padrão aceito | **Atendido** |
| Nenhum pod rodando como root | `[]` | `[]` | **Atendido** |
| Probes nos containers principais | liveness presente | liveness presente | **Atendido** |
| `resources.limits` | todos com limits | todos com limits | **Atendido** |
| Kyverno ativo | 6 policies Ready | 6 policies Ready | **Atendido** |
| NetworkPolicies | 7/6/5/5 | 7/7/5/5 | **Atendido** |
| Cosign verify | OK | OK | **Atendido** |

#### Evidência 1 — Nenhuma imagem fora do registry confiável

```
# imagens nos ns tipsbank-* (lab e prod):
busybox:1.36
felipestaypuff/tipsbank-api-contas:v1.0.0        (prod: forma curta | lab: docker.io/felipestaypuff/...)
felipestaypuff/tipsbank-api-transacoes:v2.0.0
felipestaypuff/tipsbank-auditoria:v1.0.0
felipestaypuff/tipsbank-web:v1.0.0
postgres:16-alpine
# grep -vE "felipestaypuff/|busybox|postgres:"  → (nenhuma fora do confiavel)
```

#### Evidência 2 — Nenhum pod rodando como root

```
# lab e prod:
[]
```

#### Evidência 3 — Cobertura de probes

```
# lab + prod — todos os containers PRINCIPAIS: liveness=true
tipsbank-auditoria/auditoria [auditoria] liveness=true
tipsbank-contas/api-contas [api-contas] liveness=true
tipsbank-transacoes/api-transacoes [api-transacoes] liveness=true
tipsbank-transacoes/api-transacoes [log-forwarder] liveness=false   # sidecar — não precisa
tipsbank-web/web [web] liveness=true
tipsbank-contas/postgres [postgres] liveness=true
# (prod ainda tem tipsbank-contas/postgres-replica [postgres-replica] liveness=true)
```

Observação: o `log-forwarder` aparece sem liveness porque é sidecar simples de `tail -F`, não uma API. O critério foi aplicado aos containers principais dos workloads e ao Postgres.

#### Evidência 4 — Cobertura de `resources.limits`

```
# lab + prod — todos os containers: limits=true (inclusive o sidecar log-forwarder)
```

#### Evidência 5 — Policies Kyverno ativas

```
# lab (3h) e prod (17d) — 6 policies, todas ADMISSION=true BACKGROUND=true READY=True:
allow-trusted-registry  disallow-latest-tag  disallow-root-user
generate-default-deny-netpol  mutate-security-context  require-labels
```

#### Evidência 6 — NetworkPolicies nos namespaces `tipsbank-*`

```
                contas  transacoes  auditoria  web
lab           :   7         6          5        5
prod          :   7         7          5        5
```

#### Evidência 7 — Imagens assinadas com Cosign

```
OK   docker.io/felipestaypuff/tipsbank-api-contas:v1.0.0
OK   docker.io/felipestaypuff/tipsbank-api-transacoes:v2.0.0
OK   docker.io/felipestaypuff/tipsbank-auditoria:v1.0.0
OK   docker.io/felipestaypuff/tipsbank-web:v1.0.0
# assinatura presente no registry, validada contra cosign.pub (claims + transparency log)
```

#### Evidência 8 — 3 manifestos ruins bloqueados pelo Kyverno

```
# A. Pod runAsUser=0  → admission webhook "validate.kyverno.svc-fail" denied:
disallow-root-user: 'Container/Pod não podem rodar como root (runAsUser=0).'

# B. Imagem :latest  → denied:
disallow-latest-tag: "Tag ':latest' não é permitida"

# C. Imagem nginx:1.25 (registry não-confiável)  → denied:
allow-trusted-registry: 'Imagem nao vem de registry confiavel. Use felipestaypuff/*, postgres:* ou busybox:*'
```

#### Nuance do `web`

O `web` usa `nginx-unprivileged` (Alpine, uid 101). Ele é nonroot e minimal, mas não é Distroless no sentido estrito, porque a base Alpine ainda possui componentes como shell. Portanto, a leitura correta do critério é:

- APIs Python (`api-contas`, `api-transacoes`, `auditoria`): Distroless.
- Frontend `web`: alternativa nonroot/minimal.
- Controles de compliance aplicados integralmente ao `web`: não roda como root, não usa `:latest`, tem resources e tem probes.

#### Divergências lab x prod — não são violações

| Item | Lab (Helm 1.0.1) | Prod (mão) |
|---|---|---|
| Forma da imagem | `docker.io/felipestaypuff/*` | `felipestaypuff/*` (curta) |
| `postgres-replica` | removido (1.0.1) | ainda presente (resíduo) |
| StorageClass | nfs-retain / nfs-tp-data | nfs-homelab |
| Origem dos recursos | 100% Helm | aplicados na mão |

Conclusão técnica: as diferenças são de ambiente e forma de implantação, não de controle. O que o manual cobra — compliance final verificável — ficou verde nos dois clusters.

---

### Etapa 4.7 — Vídeo demo final

**Status:** pendente de evidência do link público/unlisted.

#### Objetivo segundo o MANUAL-ALUNO.md

Gravar um vídeo de 10 a 15 minutos mostrando a entrega completa: install via Helm, pods subindo, Grafana, transferência, Locust/HPA, Kyverno bloqueando pod ruim, canary, RBAC negando ação indevida, rollback e uninstall.

#### Critérios de aceite do manual

- Vídeo acessível por link público ou unlisted.
- Os 10 pontos do roteiro aparecem no vídeo.
- Áudio audível e explicação clara do que está sendo mostrado.

#### Status dos critérios

| Critério | Status | Evidência |
|---|---|---|
| Link público/unlisted | **Pendente** | Não encontrei link de vídeo nos arquivos de `docs/` |
| 10 pontos do roteiro | **Pendente** | Existe roteiro em `Semana-4/Etapa-4.7-Video-Demo.md`, mas falta evidência do vídeo publicado |
| Áudio e explicação | **Pendente** | Depende do vídeo final |

#### Comandos/dados para complementar depois

Quando o vídeo estiver publicado, adicionar aqui:

```text
Link do vídeo:
Timestamps dos 10 pontos do manual:
1. helm install tipsbank:
2. pods subindo:
3. Grafana:
4. transferencia:
5. Locust + HPA:
6. Kyverno bloqueando pod ruim:
7. Canary:
8. RBAC Forbidden:
9. Rollback:
10. helm uninstall:
```
