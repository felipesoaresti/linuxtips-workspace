# Evidências — Caça aos Arquivos Críticos

> Submetido em 2026-06-09T13:18:08.498Z

## ⬜ Achou payroll-2026.csv com find (path completo) **(obrigatório)**

- **id:** `find-payroll`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find /var/spool -name '*.csv'

_Sem evidência registrada._

## ⬜ Listou arquivos /var/log modificados nas últimas 24h **(obrigatório)**

- **id:** `find-mtime`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find /var/log -mtime -1

_Sem evidência registrada._

## ⬜ Buscou JWT_SECRET= em todo / **(obrigatório)**

- **id:** `grep-recursivo`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** grep -r 'JWT_SECRET=' /opt /etc

_Sem evidência registrada._

## ⬜ Identificou symlink em /opt/legacy/2025/ **(obrigatório)**

- **id:** `symlink-detect`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** ls -l ou find -type l + readlink

_Sem evidência registrada._

## ⬜ Comparou os 3 configA* por md5/sha256 **(obrigatório)**

- **id:** `comparar-hashes`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** md5sum /etc/configA.conf /var/backups/orphan/configA.bak /tmp/configA.tmp

_Sem evidência registrada._

## ⬜ Usou wildcard em find COM aspas (passa pro find, não pra shell) **(obrigatório)**

- **id:** `wildcard-correto`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find . -name '*.log' (com aspas!)

_Sem evidência registrada._

## ⬜ Empacotou /var/log/app-*.log em .tar.gz **(obrigatório)**

- **id:** `tar-arquivo`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** tar -czf logs.tar.gz /var/log/app-*.log

_Sem evidência registrada._

## ⬜ Usou find -exec pra ação composta (bônus)

- **id:** `find-exec`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find ... -exec ls -l {} +

_Sem evidência registrada._

## ⬜ Filtrou via head/tail/sort/wc

- **id:** `head-tail-sort`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** head -n 5, sort | uniq -c

_Sem evidência registrada._

## ⬜ Relatório do que achou onde

- **id:** `relatorio`
- **tipo:** Resposta em texto 📝
- **dica:** tabela markdown ou narrativa

_Sem evidência registrada._
