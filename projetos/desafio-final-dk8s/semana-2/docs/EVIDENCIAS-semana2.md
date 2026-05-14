---
tags: [tipsbank, evidencias, semana-2, dk8s]
created: 2026-05-01
updated: 2026-05-13
status: concluído
semana: 2
---

# TipsBank — Evidências Semana 2: Exposição e Segurança de Rede

## Semana 2 — Exposição e Segurança de Rede

### Etapa 2.1 — Ingress Nginx + múltiplos hosts

**Data de conclusão:** 2026-04-29

#### Objetivo segundo o MANUAL-ALUNO.md

Expor a SPA e as APIs pelo Ingress Nginx usando hostnames e roteamento por paths.

#### Critérios de aceite do manual

- `kubectl get ingress -A` mostra Ingress com address preenchido.
- Host do app retorna HTML da SPA.
- Host da API com `/contas/contas` lista contas.
- `/etc/hosts` ou DNS local aponta os hosts para o controller.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Ingress com address | **Parcialmente atendido** | Setup e screenshots mostram MetalLB/IP do controller; falta output direto de `kubectl get ingress -A`. |
| HTML da SPA | **Atendido** | `curl` em `app.tipsbank.staypuff.info` retorna title/logo da SPA. |
| API por path | **Atendido** | `curl` em `/contas/contas` retorna contas via Ingress. |
| Resolução local | **Atendido com desvio documentado** | Foi usado Pi-hole/DNS real apontando para `192.168.3.110`, em vez de `/etc/hosts`. |

#### Observações de alinhamento com o manual

- O manual usa `*.tipsbank.local`; o lab usou `*.tipsbank.staypuff.info`, mantendo o mesmo objetivo técnico.

Nesta etapa a aplicação saiu do acesso por `port-forward` e passou a ter entrada HTTP de verdade no cluster. O objetivo foi separar o host do frontend (`app`) do host das APIs (`api`) e deixar o Ingress Nginx fazer o roteamento por hostname e path.

**Setup:**
- MetalLB instalado via Helm · IP Pool: `192.168.3.200-209` · IP alocado: `192.168.3.110`
- Ingress Nginx Controller instalado via Helm · `type: LoadBalancer` · EXTERNAL-IP: `192.168.3.110`
- DNS Pi-hole: `app.tipsbank.staypuff.info` e `api.tipsbank.staypuff.info` → `192.168.3.110`
- Ingresses criados: `tipsbank-web` (frontend), `tipsbank-contas`, `tipsbank-transacoes`, `tipsbank-auditoria`

#### Critério 1 — Frontend SPA acessível via hostname

Esse teste confirma que o DNS interno do homelab aponta para o LoadBalancer do Ingress e que o Nginx entrega a SPA corretamente.

```bash
curl -s http://app.tipsbank.staypuff.info/ | grep -i "tipsbank\|title"
```

**Output:**
```
<title>TipsBank — Internet Banking de Luxo</title>
        <img src="/img/logo-banco.png" alt="TipsBank" />
```

#### Critério 2 — API contas via Ingress com path routing

Aqui a validação é do roteamento por path. A requisição chega em `api.tipsbank.staypuff.info`, o Ingress identifica o prefixo `/contas` e encaminha para o Service da `api-contas`.

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

---

### Etapa 2.2 — TLS + recursos avançados do Ingress

**Data de conclusão:** 2026-05-01

#### Objetivo segundo o MANUAL-ALUNO.md

Adicionar HTTPS com cert-manager e recursos avançados do Ingress: Basic Auth, rate limit e affinity cookie.

#### Critérios de aceite do manual

- `curl -k https://app.tipsbank.local/` retorna 200.
- `/contas/admin/contas` retorna 401 sem credencial e 200 com credencial.
- Rajada com `hey`/`ab` mostra 429 após rate limit.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| HTTPS do app/API | **Atendido** | Certificado Let's Encrypt real, `certificate READY=True` e curl/browser sem erro. |
| Basic Auth | **Atendido** | Sem credencial retorna 401; com `admin:senha123` retorna JSON das contas. |
| Rate limit 429 | **Atendido** | `hey` mostra 261 respostas 200 e 739 respostas 429. |

#### Observações de alinhamento com o manual

- O manual aceita issuer self-signed/local; a evidência usa Let's Encrypt DNS-01 via Cloudflare, mais próximo de ambiente real.

Depois do HTTP básico, o foco foi aproximar o lab de um cenário mais real: TLS válido, autenticação simples para rota administrativa, rate limit e afinidade por cookie. Não é para fingir que Basic Auth resolve segurança bancária, mas é um bom exercício de controle no Ingress.

**Setup:**
- TLS: cert-manager + ClusterIssuer `prod-letsencrypt-cloudflare` (Let's Encrypt DNS-01 via API Cloudflare)
- Certificados: Let's Encrypt reais, browser-trusted, renovação automática em 30 dias antes do vencimento
- Rate limit: `limit-rps: "50"` no Ingress frontend + `limit-req-status-code: "429"` no ConfigMap global
- Basic Auth: Secret `basic-auth` no namespace `tipsbank-contas` + Ingress dedicado para `/contas/admin`
- Affinity Cookie: `TIPSBANK_AFFINITY` com `Max-Age=172800` no Ingress de transações

#### Critério 1 — HTTPS funcionando com cert Let's Encrypt real

O certificado foi emitido via DNS-01, então o Let's Encrypt não depende de acessar o cluster por HTTP para validar o domínio. Isso combina bem com homelab, NAT e ambientes onde o endpoint ainda está sendo organizado.

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

A rota administrativa foi separada para exigir credencial no próprio Ingress. Sem usuário e senha, o Nginx barra a chamada antes de ela chegar na aplicação; com credencial correta, o tráfego segue para a `api-contas`.

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

O teste com `hey` força uma rajada acima do limite configurado. A distribuição com respostas `200` e `429` mostra que o Ingress não derrubou o serviço; ele apenas passou a recusar o excesso de requisições, que é exatamente o comportamento esperado para proteger a aplicação.

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

| Chave                   | Tipo | Default | Descrição                                                 |
| ----------------------- | ---- | ------- | --------------------------------------------------------- |
| `limit-req-status-code` | int  | **503** | HTTP status code retornado quando o rate limit é excedido |

Patch aplicado:
```bash
kubectl patch configmap ingress-nginx-controller -n ingress-nginx \
  --type merge \
  -p '{"data":{"limit-req-status-code":"429"}}'
kubectl rollout restart deployment ingress-nginx-controller -n ingress-nginx
```



#### Critério 4 — Affinity Cookie em transações

A afinidade por cookie foi aplicada na rota de transações para manter o cliente preso ao mesmo backend por um período. Isso é útil quando existe estado local, cache quente ou comportamento que ainda não está totalmente stateless. Aqui o objetivo foi validar a mecânica no Ingress.

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

---

### Etapa 2.3 — Cluster EKS Paralelo

**Data de conclusão:** 2026-05-03

#### Objetivo segundo o MANUAL-ALUNO.md

Replicar o TipsBank em um cluster EKS criado via `eksctl`, com app e Ingress funcionando em DNS real.

#### Critérios de aceite do manual

- `kubectl config get-contexts` mostra dois contexts funcionando.
- `kubectl --context eks-tipsbank get nodes` retorna nodes do EKS.
- TipsBank acessível via HTTPS com DNS real.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Dois contexts | **Atendido** | Output mostra `eks-tipsbank` e contextos locais no kubeconfig. |
| Nodes EKS | **Atendido** | Dois nodes EKS Ready em `us-east-1`. |
| HTTPS/DNS real | **Atendido** | Health checks HTTPS e certificados READY no EKS. |

Aqui eu subi um EKS paralelo para provar que os manifestos e o desenho da aplicação não estavam presos ao homelab. A ideia foi levar o mesmo TipsBank para AWS, aceitar as diferenças de infraestrutura e documentar os ajustes necessários sem maquiar os tropeços.

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

O primeiro critério foi manter os dois mundos acessíveis no mesmo kubeconfig. Isso evita misturar evidências: cada comando deixa claro se está falando com homelab ou EKS.

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

Com os nodes `Ready`, o plano de controle da AWS e os managed node groups estavam prontos para receber os workloads. Também validei versão do Kubernetes, runtime e IPs para registrar exatamente o ambiente usado.

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

Esse critério fecha o teste de portabilidade: aplicação acessível por DNS público, TLS válido, Services respondendo e storage persistente ligado no EKS. Ou seja, não foi só "subiu pod"; o fluxo externo da aplicação também funcionou.

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

---

### Etapa 2.4 — Canary de Transações

**Data de conclusão:** 2026-05-04

#### Objetivo segundo o MANUAL-ALUNO.md

Publicar `api-transacoes:v2` e usar Canary Ingress para dividir tráfego, mantendo opção de direcionar por header.

#### Critérios de aceite do manual

- Health de transações retorna `version: v1` ou `version: v2` em proporção aproximada 9:1.
- `kubectl rollout undo` funciona nos Deployments.
- Header `X-Canary: true` direciona para v2 como extra.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| Split 9:1 | **Atendido** | Amostras de 100 requisições mostram distribuição próxima de 90/10. |
| rollout undo | **Atendido** | `kubectl rollout undo deployment/api-transacoes-v2` executado e histórico exibido. |
| Header canary | **Atendido** | `X-Canary: true` retorna `version: v2` e endpoint `/pix`. |

#### Observações de alinhamento com o manual

- O manual sugere 1000 requisições; a evidência usa amostras de 100. A proporção ficou estável, mas um teste de 1000 deixaria a amostra estatisticamente mais forte.

Nesta etapa publiquei uma v2 da `api-transacoes` sem substituir a v1 de uma vez. O canary permitiu mandar uma fatia pequena do tráfego por peso e, ao mesmo tempo, forçar 100% para v2 com header. É o tipo de controle que ajuda a testar mudança com calma antes de abrir para todo mundo.

**Setup:**
- Deployment `api-transacoes-v2` (1 réplica) com imagem `felipestaypuff/tipsbank-api-transacoes:v2.0.0`
- Service `api-transacoes-v2` ClusterIP porta 8080
- Ingress canário `tipsbank-api-transacoes-canary` com `canary-weight: "10"` + `canary-by-header-value: "true"`
- Endpoint novo: `GET /pix` (mock) disponível apenas na v2

#### Critério 1 — Split ~90/10 por peso

O loop de 100 requisições dá uma amostra prática da distribuição. Não precisa bater exatamente 90/10 em toda rodada, porque é balanceamento probabilístico, mas as amostras ficaram próximas o suficiente para validar a configuração.

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

O header é o caminho controlado para teste funcional. Com ele, dá para validar a nova versão sem depender da sorte do peso do canary.

```bash
curl -sk -H "X-Canary: true" https://api.tipsbank.staypuff.info/transacoes/health/live
```

**Output:**
```json
{"status":"ok","version":"v2"}
```

#### Critério 3 — Endpoint `/pix` acessível via v2

O endpoint `/pix` serviu como prova objetiva de que a requisição caiu na v2. Como esse endpoint não existe na v1, a resposta confirma que o roteamento por header está chegando no backend novo.

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

---

### Etapa 2.5 — NetworkPolicy Zero-Trust

**Data de conclusão:** 2026-05-05

#### Objetivo segundo o MANUAL-ALUNO.md

Aplicar default-deny nos namespaces e liberar somente os fluxos necessários para a aplicação funcionar.

#### Critérios de aceite do manual

- Auditoria tentando acessar `api-contas` recebe timeout.
- `api-transacoes` acessa `api-contas` com 200.
- Saída para IP não permitido é bloqueada.

#### Status dos critérios

| Critério | Status | Evidência neste arquivo |
|---|---|---|
| auditoria -> api-contas bloqueado | **Atendido** | Testes por ClusterIP e DNS terminam em timeout. |
| transacoes -> api-contas liberado | **Atendido** | Curl a partir de `api-transacoes` retorna `{"status":"ok"}`. |
| Egress externo bloqueado | **Atendido no homelab** | Teste para IP externo do homelab retorna timeout; no EKS o manual sugere também `169.254.169.254`. |

#### Observações de alinhamento com o manual

- A evidência documenta refinamento importante de DNS: regra restrita a CoreDNS via `namespaceSelector + podSelector`, em vez de liberar porta 53 para qualquer destino.

A proposta aqui foi trocar o modelo "todo mundo fala com todo mundo" por allowlist explícita entre namespaces. Depois do `default-deny`, só os fluxos necessários para o TipsBank continuaram liberados. É segurança de rede com o mínimo de conversa permitida, do jeito que um ambiente sensível pede.

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

#### Critério 2 — transações ACESSA api-contas (200 esperado)

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

`allow-transacoes-to-contas` liberou o egress TCP:8080. Esse é o caminho esperado: transações precisa consultar contas para validar origem, destino e saldo antes de concluir a operação.

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

Esse smoke test é importante porque política de rede boa não é a que bloqueia tudo e quebra a aplicação. Ela precisa bloquear o tráfego indevido e preservar o caminho crítico do produto.

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
