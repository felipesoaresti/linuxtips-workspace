# Usando Regex com grep, egrep, sed e muito mais

_Atualizado em 19/08/2026_

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

 




