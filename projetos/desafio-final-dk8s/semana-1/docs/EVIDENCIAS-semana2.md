---
tags: [tipsbank, evidencias, semana-2, dk8s]
created: 2026-05-01
updated: 2026-05-05
status: concluído
semana: 2
---

# TipsBank — Evidências Semana 2: Exposição e Segurança de Rede

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

`curl` sem `-k` funcionando. Browser mostra 🔒 sem aviso. Cert emitido via DNS-01 (Cloudflare cria TXT `_acme-challenge.*` → Let's Encrypt valida → emite).

**Nota:** `limit-req-status-code` é configuração global do ConfigMap do ingress-nginx (não annotation por Ingress).
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

A annotation `nginx.ingress.kubernetes.io/limit-req-status-code: "429"` **não existe** como configuração por Ingress. O `limit-rps` injeta `limit_req` no bloco `location` do nginx.conf gerado (escopo por rota), mas o status code de rejeição é a diretiva `limit_req_status` no bloco `http {}` (escopo global) — que o ingress-nginx mapeia para o ConfigMap do controller.

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

**Problema com Cloudflare e rate limiting por IP:**

Nos primeiros testes com `hey -n 100 -c 10` todos os requests retornaram 200, mesmo com `limit-rps: 50` configurado. O motivo: com Cloudflare Tunnel, o nginx-ingress vê **todos os requests chegando do mesmo IP** — o IP interno do tunnel (não o IP real do cliente). A diretiva `limit_req_zone` do nginx usa `$binary_remote_addr` como chave, que neste cenário é sempre o IP do Cloudflare Tunnel.

Consequências práticas:
1. **Todos os usuários compartilham um único bucket de rate limit** — 50 req/s globais, não por usuário
2. **O rate limit é mais fácil de atingir em testes locais** (100% do tráfego vem de um IP) e mais difícil de calibrar para produção real
3. Em produção com Cloudflare, a correção é usar o header `CF-Connecting-IP` como chave: configurar `use-forwarded-headers: "true"` no ConfigMap + `forwarded-for-header: "CF-Connecting-IP"` para que o nginx use o IP real do cliente como chave do rate limiter

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

| # | Problema | Causa | Solução |
|---|---|---|---|
| 1 | `eksctl create cluster` → `AccessDeniedException: eks:DescribeClusterVersions` | IAM user `eks-tipsbank` sem permissões EKS | Inline policy com `eks:*`, `ssm:GetParameter`, `autoscaling:*`, `ecr:*` |
| 2 | `ebs-csi-controller` CrashLoopBackOff | OIDC não habilitado no cluster → service account sem credenciais AWS | `eksctl utils associate-iam-oidc-provider` + `eksctl create iamserviceaccount` + `rollout restart` |
| 3 | `postgres-0` Pending | StatefulSet com `storageClassName: local-path` (não existe no EKS) | Alterado para `gp2` no manifest adaptado |
| 4 | `postgres-0` CrashLoopBackOff após bind do EBS | EBS ext4 cria `lost+found` na raiz do volume → initdb recusa diretório não-vazio | Adicionado `PGDATA=/var/lib/postgresql/data/pgdata` (subdiretório limpo) |
| 5 | PVC `auditoria-pvc` ProvisioningFailed | EFS CSI Driver v3.0.1: bug no modo `efs-ap` — campo `permissions` não é passado ao `CreateAccessPoint` | Abandonado dynamic provisioning; criado PV estático com `volumeHandle: fs-0d5b539e1d48f267d` (sem Access Point) |
| 6 | Frontend "offline" (nginx 502, DNS timeout) | nginx `resolver 10.96.0.10` (CoreDNS homelab) inacessível do EKS — CoreDNS do EKS é `10.100.0.10` | Novo ConfigMap com `resolver 10.100.0.10` + `rollout restart` do Deployment web |

**Nota sobre `subPath` e hot-reload de ConfigMap:** o volumeMount da web usa `subPath`, o que impede o Kubernetes de atualizar o arquivo automaticamente ao mudar o ConfigMap. O pod precisa de `rollout restart` após qualquer atualização de ConfigMap.

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

> **Nota:** O context do cluster kubeadm local ainda está nomeado `tipsbank` (pendente renomear para `kubeadm-local` com `kubectl config rename-context tipsbank kubeadm-local`). O context `eks-tipsbank` está corretamente configurado e funcional.

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

> [!WARNING] Custos AWS ativos
> O cluster EKS (`tipsbank`, `us-east-1`) gera custos enquanto ativo (~$0.10/h control plane + instâncias EC2 + NLB + EFS). Destruir com `eksctl delete cluster --name tipsbank --region us-east-1` após concluir as evidências.


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

Split dentro da faixa esperada (~90/10). Variação normal — distribuição probabilística.

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

| # | Problema | Causa | Solução |
|---|---|---|---|
| 1 | Pod v2 retornando `version: v1` | Env var `APP-VERSION` (hífen) é inválida em Linux — ignorada. `APP_VERSION` do ConfigMap sobrescrevia com `v1` | Remover entrada inválida e adicionar `APP_VERSION: "v2"` como `value` direto |
| 2 | Ingress canary com `spec.spec` duplicado | Campo inválido copiado por engano | Removido — `spec:` só aparece uma vez |
| 3 | `X-Canary: always` não forçava v2 | `canary-by-header-value: "true"` substitui os valores padrão `always`/`never` | Usar `X-Canary: true` (valor configurado) |
| 4 | `/pix` retornando 404 | Imagem buildada antes de adicionar o endpoint ao `main.py` | Adicionar endpoint, rebuildar e repushar `v2.0.0` |
| 5 | `curl -H " X-Canary: true"` (espaço no header) não funcionou | Espaço antes do nome do header — nginx não reconhece, cai no weight | Header names são whitespace-sensitive |


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
# Teste via ClusterIP (bypass DNS — Alpine/musl tem bug com ndots:5)
kubectl debug -it auditoria-659555485f-hqzjc \
  --image=curlimages/curl --target=auditoria \
  -n tipsbank-auditoria --profile=netadmin \
  -- curl -m 5 http://10.110.102.200:8080/health/live

# Teste via DNS com trailing dot (força lookup absoluto, bypassa search domains)
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

NetworkPolicy bloqueou o TCP:8080 — auditoria não está na whitelist de ingress do tipsbank-contas. ✅

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

allow-transacoes-to-contas liberou o egress TCP:8080. ✅

#### Critério 3 — pods NÃO acessam IPs externos (timeout esperado)

```bash
# Proxmox host 1
kubectl debug -it api-contas-65d86d5dc7-d6lt6 \
  --image=curlimages/curl --target=api-contas \
  -n tipsbank-contas --profile=netadmin \
  -- curl -m 5 http://192.168.3.11:8006

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

default-deny bloqueou egress para IPs externos não permitidos. ✅

#### Smoke test — aplicação continua funcionando após as policies

```bash
curl -s -o /dev/null -w "%{http_code}" https://app.tipsbank.staypuff.info
```

**Output:**
```
200
```

Ingress → web → APIs: fluxo completo funcionando com zero-trust ativo. ✅

**Problemas encontrados:**

| # | Problema | Causa | Solução |
|---|---|---|---|
| 1 | `curl: (6) Could not resolve host` com curlimages/curl | Alpine/musl + ndots:5 + 4 search domains: musl desiste antes do lookup absoluto | Trailing dot no FQDN (`svc.cluster.local.`) ou usar ClusterIP direto |
| 2 | DNS egress com `namespaceSelector: kube-system` bloqueava novos containers | Calico avalia antes do DNAT — query vai para ClusterIP `10.96.0.10`, não ao pod real do coredns | Regra DNS port-only (sem `to:`): `To: <any>` |
| 3 | `--profile=legacy` deprecated no kubectl debug | K8s depreciou o perfil legacy | Usar `--profile=netadmin` ou `--profile=general` |


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

---
