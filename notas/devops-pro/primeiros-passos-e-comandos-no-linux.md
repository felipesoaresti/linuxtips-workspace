# Primeiros passos e comandos no Linux

_Exportado em 03/04/2026_

Tipos de arquibo: 
- - arquivo comum 
d - diretório
l - link simbólico 
c - caracter -> tudo que transfere informação 
b - bloco -> armazenamento de informação - pen drive, HD
Terminal - Dispositivo de caracter - tty - console - crtl + alt + F1...... 

bin - executaveis binarios
etc - configuração do sistema
dev - dispositivos
home - diretorio de usuarios
lib - bibliotecas nome.so.versão - librs.so.1 - usadas por varios executaveis
lib/modules - modulos do kernel 
media - CDROM por exemplo - as vezes medias externas - Ubuntu por ex.
mnt - ponto de montagem
opt - Instalação de out of distro ( checkmk kkkkk trampo pouco utilizado nada .)
proc - diretorio dinamico, informação do sistema 
run - informação do processo que esta sendo executado ( tempo real)
sbin - binarios - root 
sys - Informações de sistema  do kernel ( diretorio com arquivos "dinamico" )
tmp - reboot já era / informações de processos/ volátil no boot
usr - não é default - para todos - segunda estrutura  - qualquer usuario para usar - existe sbin nesse diretorio
var - arquivos variáveis - 

### Comandos 

head -20 - (cabeçalho) 20 linhas
ls -lha - listagem,human,ocultos
/etc/os-release - configuração da sitro instalada da distro instalada
tar -czf nome.arquivo / c- create | z - gzip | f - nome do arquivo criado
tar -xzf nome.arquivo / e - extract | z - gzip | f - nome do arquivo extrair
find /var/log -type f -name  "*.log" 
mkdir -p projeto-devops/{app/{src,config},infra/{terraform,ansible},logs,docs}



  

