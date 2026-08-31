# As permissões especiais SUID, SGID e Stickbit

_Atualizado em 31/08/2026_

umask 0002
arquivo comum: 666
diretorio:777

umask: 0002 - define as permissões na hora da ciração do arquivo

0666-0002= umask 0664
0666-0022= umask 0644
0777-0022= umask 0755(diretorios=0777)

definidos onde? 
/etc/login.defs
/etc/profile
bashrc - arquivos de configuração bash

Permissões Especiais 
SUID - somente para executaveis / executado como dono do arquivo 
SGID - somente para arquivos executaveis  
Stick bit 








 


