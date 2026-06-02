# Evidências — Caça aos Arquivos Críticos

> Submetido em 2026-06-02T10:52:21.191Z

## ✅ Achou payroll-2026.csv com find (path completo) **(obrigatório)**

- **id:** `find-payroll`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find /var/spool -name '*.csv'

```
root@lab-4d80677f-22957:/lab# find /var/spool/ -name payroll-2026.csv
/var/spool/cron/.hidden/payroll-2026.csv
root@lab-4d80677f-22957:/lab#
```

## ✅ Listou arquivos /var/log modificados nas últimas 24h **(obrigatório)**

- **id:** `find-mtime`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find /var/log -mtime -1

```
root@lab-4d80677f-22957:/lab# find /var/log -mtime -1 -type f
/var/log/apt/eipp.log.xz
/var/log/apt/term.log
/var/log/apt/history.log
/var/log/alternatives.log
/var/log/app-23.log
/var/log/app-26.log
/var/log/dpkg.log
/var/log/app-mixed.log
root@lab-4d80677f-22957:/lab#
```

## ✅ Buscou JWT_SECRET= em todo / **(obrigatório)**

- **id:** `grep-recursivo`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** grep -r 'JWT_SECRET=' /opt /etc

```
root@lab-4d80677f-22957:/lab# grep -r 'JWT_SECRET=' /opt /etc
/opt/legacy/2024/.config-secret:JWT_SECRET=NaoFacaIssoEmProducao
root@lab-4d80677f-22957:/lab#
```

## ✅ Identificou symlink em /opt/legacy/2025/ **(obrigatório)**

- **id:** `symlink-detect`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** ls -l ou find -type l + readlink

```
ls -l /opt/legacy/2025
total 0
lrwxrwxrwx 1 root root 40 Jun  2 10:43 relatorio-financeiro.csv -> /var/spool/cron/.hidden/payroll-2026.csv
root@lab-4d80677f-22957:/lab#
```

## ✅ Comparou os 3 configA* por md5/sha256 **(obrigatório)**

- **id:** `comparar-hashes`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** md5sum /etc/configA.conf /var/backups/orphan/configA.bak /tmp/configA.tmp

```
root@lab-4d80677f-22957:/lab# find / -iname  "configA*" -type f
/var/backups/orphan/configA.bak
/etc/configA.conf
/tmp/configA.tmp
root@lab-4d80677f-22957:/lab# md5sum /var/backups/orphan/configA.bak /etc/configA.conf /tmp/configA.tmp
985c9535907a133d64a0dce2fcb05391  /var/backups/orphan/configA.bak
985c9535907a133d64a0dce2fcb05391  /etc/configA.conf
7c98ffff5669fb0be30c59e342b9bf54  /tmp/configA.tmp
root@lab-4d80677f-22957:/lab#
```

## ✅ Usou wildcard em find COM aspas (passa pro find, não pra shell) **(obrigatório)**

- **id:** `wildcard-correto`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find . -name '*.log' (com aspas!)

```
root@lab-4d80677f-22957:/lab# find /var/log/ -name 'app-*.log' 
/var/log/app-28.log
/var/log/app-2.log
/var/log/app-17.log
/var/log/app-6.log
/var/log/app-18.log
/var/log/app-21.log
/var/log/app-24.log
/var/log/app-27.log
/var/log/app-23.log
/var/log/app-8.log
/var/log/app-12.log
/var/log/app-19.log
/var/log/app-10.log
/var/log/app-26.log
/var/log/app-16.log
/var/log/app-1.log
/var/log/app-3.log
/var/log/app-25.log
/var/log/app-mixed.log
/var/log/app-5.log
/var/log/app-11.log
/var/log/app-7.log
/var/log/app-22.log
/var/log/app-30.log
/var/log/app-13.log
/var/log/app-4.log
/var/log/app-14.log
/var/log/app-20.log
/var/log/app-29.log
/var/log/app-9.log
/var/log/app-15.log
root@lab-4d80677f-22957:/lab#
```

## ✅ Empacotou /var/log/app-*.log em .tar.gz **(obrigatório)**

- **id:** `tar-arquivo`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** tar -czf logs.tar.gz /var/log/app-*.log

```
root@lab-4d80677f-22957:/lab# tar czf logs.tar.gz /var/log/app-*.log
tar: Removing leading `/' from member names
tar: Removing leading `/' from hard link targets
root@lab-4d80677f-22957:/lab# ll
bash: ll: command not found
root@lab-4d80677f-22957:/lab# ls -lha 
total 12K
drwxr-xr-x 1 estudante estudante 4.0K Jun  2 10:51 .
drwxr-xr-x 1 root      root      4.0K Jun  2 10:43 ..
-rw-r--r-- 1 root      root       923 Jun  2 10:51 logs.tar.gz
```

## ✅ Usou find -exec pra ação composta (bônus)

- **id:** `find-exec`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** find ... -exec ls -l {} +

```
root@lab-4d80677f-22957:/lab# find /var/log -name 'app-*.log' -exec ls -lh {} +
-rw-r--r-- 1 root root    6 May  5 10:43 /var/log/app-1.log
-rw-r--r-- 1 root root    7 May 28 10:43 /var/log/app-10.log
-rw-r--r-- 1 root root    7 May 29 10:43 /var/log/app-11.log
-rw-r--r-- 1 root root    7 Jun  1 10:43 /var/log/app-12.log
-rw-r--r-- 1 root root    7 May  8 10:43 /var/log/app-13.log
-rw-r--r-- 1 root root    7 May 27 10:43 /var/log/app-14.log
-rw-r--r-- 1 root root    7 May 20 10:43 /var/log/app-15.log
-rw-r--r-- 1 root root    7 May 18 10:43 /var/log/app-16.log
-rw-r--r-- 1 root root    7 May 22 10:43 /var/log/app-17.log
-rw-r--r-- 1 root root    7 May 20 10:43 /var/log/app-18.log
-rw-r--r-- 1 root root    7 May 11 10:43 /var/log/app-19.log
-rw-r--r-- 1 root root    6 May 10 10:43 /var/log/app-2.log
-rw-r--r-- 1 root root    7 May 28 10:43 /var/log/app-20.log
-rw-r--r-- 1 root root    7 May 13 10:43 /var/log/app-21.log
-rw-r--r-- 1 root root    7 May  9 10:43 /var/log/app-22.log
-rw-r--r-- 1 root root    7 Jun  2 10:43 /var/log/app-23.log
-rw-r--r-- 1 root root    7 May 28 10:43 /var/log/app-24.log
-rw-r--r-- 1 root root    7 May 30 10:43 /var/log/app-25.log
-rw-r--r-- 1 root root    7 Jun  2 10:43 /var/log/app-26.log
-rw-r--r-- 1 root root    7 May 12 10:43 /var/log/app-27.log
-rw-r--r-- 1 root root    7 May 31 10:43 /var/log/app-28.log
-rw-r--r-- 1 root root    7 May 22 10:43 /var/log/app-29.log
-rw-r--r-- 1 root root    6 May 29 10:43 /var/log/app-3.log
-rw-r--r-- 1 root root    7 May 28 10:43 /var/log/app-30.log
-rw-r--r-- 1 root root    6 May 21 10:43 /var/log/app-4.log
-rw-r--r-- 1 root root    6 May 10 10:43 /var/log/app-5.log
-rw-r--r-- 1 root root    6 May  8 10:43 /var/log/app-6.log
-rw-r--r-- 1 root root    6 May 20 10:43 /var/log/app-7.log
-rw-r--r-- 1 root root    6 May  5 10:43 /var/log/app-8.log
-rw-r--r-- 1 root root    6 May 30 10:43 /var/log/app-9.log
-rw-r--r-- 1 root root 1.1K Jun  2 10:43 /var/log/app-mixed.log
```

## ✅ Filtrou via head/tail/sort/wc

- **id:** `head-tail-sort`
- **tipo:** Comando rodado no terminal ⌨️
- **dica:** head -n 5, sort | uniq -c

```
root@lab-4d80677f-22957:/lab# ls /var/log/app-*.log | sort | head -n 5
/var/log/app-1.log
/var/log/app-10.log
/var/log/app-11.log
/var/log/app-12.log
/var/log/app-13.log
root@lab-4d80677f-22957:/lab#
```

## ✅ Relatório do que achou onde

- **id:** `relatorio`
- **tipo:** Resposta em texto 📝
- **dica:** tabela markdown ou narrativa

Encontrei o arquivo payroll-2026.csv em /var/spool/cron/.hidden/payroll-2026.csv. Arquivos modificados há menos de 1 dia em /var/log Compactei os logs app-*.log com tar usando: tar -czf logs.tar.gz /var/log/app-*.log
grep para buscar JWT_SECRET= no sistema. O comando gerou avisos de "erros" então usei a saida do 2> /dev/null
