# Caça aos Arquivos Críticos
O FS tá caótico depois do incidente. Use find/grep/locate/wildcards pra achar e arquivar o que importa.
---
## Instrucoes

# 🔍 Caça aos Arquivos Críticos

> **Cenário:** O servidor sofreu um incidente ontem. Configs, logs, backups
> e arquivos sensíveis foram espalhados em paths inusitados durante a
> recuperação corrida. Você tá no time de cleanup. Use o que aprendeu no
> Módulo 2 (find, grep, locate, wildcards, atalhos) pra **encontrar e
> consolidar** o que importa.

## Suas missões

1. **Ache o arquivo de payroll.csv** — sabe-se que está em algum lugar
   "escondido" dentro de `/var/spool/`.
2. **Liste todos os arquivos modificados nas últimas 24h** em `/var/log/`.
3. **Busque o conteúdo `JWT_SECRET=`** em qualquer arquivo do sistema (recursivo)
   pra achar config exposta.
4. **Identifique** os symlinks em `/opt/legacy/2025/` e mostra o real
   destino.
5. **Compare** os 3 arquivos `configA*` por hash pra ver quais são iguais.
6. **Compacte** os logs do `/var/log/app-*.log` num tar.gz único.

## Como entregar

Cole no painel de evidências o **comando exato** que você rodou + output
relevante.

## Dicas

- `find` é o canivete suíço. `find -name`, `find -mtime`, `find -type l`,
  `find -exec`.
- `grep -r` percorre dir. `grep -l` lista só o nome do arquivo.
- `locate` precisa de `updatedb` — já rodamos pra você no setup.
- `md5sum` ou `sha256sum` rápido pra comparar.
- Curingas: `*` casa qualquer coisa, `?` casa um char, `[abc]` casa um
  desses. Cuidado com aspas: `find . -name "*.log"` (com aspas) vs
  `find . -name *.log` (sem — shell expande primeiro!).

---
*Desafio LINUXtips - devops-pro*