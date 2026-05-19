---
tags: [tipsbank, evidencias, semana-4, dk8s, kyverno]
created: 2026-05-18
updated: 2026-05-18
status: em-andamento
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
kubectl run teste-ok --image=nginx:1.27 --restart=Never -n default
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
