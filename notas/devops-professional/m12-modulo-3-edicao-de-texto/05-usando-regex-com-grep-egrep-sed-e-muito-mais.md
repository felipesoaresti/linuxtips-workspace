# Usando Regex com grep, egrep, sed e muito mais

_Atualizado em 20/08/2026_

Regex

grep -a "ssh" auth.log
zgrep -a "ssh" auth.log
egrep = -E do grep 
grep "[0-5]" dmesg

grep -E '[0-9]+\.[0-9]+\.'[0-9]+\.[0-9]+'
grep -aE '[0-9]$'
grep -E '(Starting|Finished)' syslog
grep -v '^#' /etc/adduser.conf
grep -v '^#' /etc/adduser.conf | grep -v '^$'
sed 's/palavra-atual/palavra-antiga/g'
sed 's/[0-9]/X/g' adduser.conf > outro-arquivo


.       → Qualquer caractere (um só)
*       → Zero ou mais do caractere anterior
+       → Um ou mais do caractere anterior (regex estendido)
^       → Início da linha
$       → Fim da linha
[abc]   → Qualquer um dos caracteres entre colchetes
[0-9]   → Qualquer dígito
[a-z]   → Qualquer letra minúscula
\       → Escape (trata o próximo caractere como literal)
|       → OU (regex estendido)
()      → Agrupamento (regex estendido)
 
# Linhas que COMEÇAM com "error"
grep '^error' /var/log/app.log

# Linhas que TERMINAM com um número
grep '[0-9]$' /var/log/app.log

# Linhas que contêm um IP (padrão simplificado)
grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' /var/log/nginx/access.log

# Linhas com "error" OU "fatal" OU "critical"
grep -E '(error|fatal|critical)' /var/log/app.log

# Linhas que NÃO são comentários (não começam com #)
grep -v '^#' /etc/nginx/nginx.conf

# Linhas não vazias e não comentários (config limpa)
grep -v '^#' /etc/nginx/nginx.conf | grep -v '^$'

# Remover espaços em branco no final das linhas
sed 's/[[:space:]]*$//' arquivo.txt

# Trocar qualquer sequência de dígitos por "XXX"
sed 's/[0-9]\+/XXX/g' arquivo.txt


