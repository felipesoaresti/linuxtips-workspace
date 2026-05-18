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
