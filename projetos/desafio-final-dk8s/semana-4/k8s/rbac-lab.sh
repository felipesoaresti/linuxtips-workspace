#!/usr/bin/env bash
set -e
mkdir -p /tmp/tipsbank-certs-lab && cd /tmp/tipsbank-certs-lab

# CA e endpoint do LAB (extraídos do kubeconfig atual)
kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > cluster-ca.crt
APISERVER=$(kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.server}')
echo ">> APISERVER do lab: $APISERVER"

for U in operador-contas operador-transacoes auditor-global sre; do
    case $U in
      operador-contas)     KC=op-contas-lab.kubeconfig ;;
      operador-transacoes) KC=op-transacoes-lab.kubeconfig ;;                                                                                                                                                           auditor-global)      KC=auditor-lab.kubeconfig ;;
      sre)                 KC=sre-lab.kubeconfig ;;
    esac

openssl genrsa -out "$U.key" 2048
openssl req -new -key "$U.key" -out "$U.csr" -subj "/CN=$U/O=tipsbank"

kubectl delete csr "$U" --ignore-not-found

cat <<CSR | kubectl apply -f -
  apiVersion: certificates.k8s.io/v1
  kind: CertificateSigningRequest
  metadata:
    name: $U
  spec:
    request: $(base64 -w 0 "$U.csr")
    signerName: kubernetes.io/kube-apiserver-client
    expirationSeconds: 31536000
    usages:
    - client auth
CSR

  kubectl certificate approve "$U"
  kubectl get csr "$U" -o jsonpath='{.status.certificate}' | base64 -d > "$U.crt"

  kubectl config set-cluster tp-lab --certificate-authority=cluster-ca.crt --embed-certs=true --server="$APISERVER" --kubeconfig="$KC"
  kubectl config set-credentials "$U" --client-certificate="$U.crt" --client-key="$U.key" --embed-certs=true --kubeconfig="$KC"
  kubectl config set-context "$U@tp-lab" --cluster=tp-lab --user="$U" --kubeconfig="$KC"
  kubectl config use-context "$U@tp-lab" --kubeconfig="$KC" >/dev/null
  echo ">> OK: $KC"
  done
