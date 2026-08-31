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
SUID - somente para executaveis / executado como dono do arquivo - 4 - 4644
SGID - somente para executiveis - executado como grupo dono do arquivo - 2 - 2644
em diretorio:
chmod 0755 - desabilitar - chmod g-s ou chmod u-s
 
Stick bit - funciona em diretorio -  t habilitado somente o dono pode deletar - 1 - 4+2+1 = 7
chmod 7777 limao 








 


