# Descomplicando as permissões no Linux

_Atualizado em 31/08/2026_

vim  :!ls -lha 

-rw-:r--:r-- 644

significado das letras:
r - ler o arquivo - valor 4
w - permissão de escrita - valor 2
x - permissão de execução - valor 1
- - sem permissão - valor 0

Primeiro caracter: qual o tipo de arquivo
   - arquivo comum
   l link simbóilico
   c disp caractere
   b disp bloco
   d diretorio
   s socket

rw- : as permissões do dono do arquivo
r-- : as permissões do grupo dono
r-- : as permissões dos outros 

chmod - mudar as permissões
chown - mudar o dono e grupo 
chgrp - mudar o grupo 

modo simbólico : - rwx:rw-:r-x ->  765
chmod com modo simbólico:
u - dono do arquivo
g - grupo do arquivo
o - outros
a - all / todos

operacões
+ adiciona permissão
- remove permissão
= deixa igualao pedido as permissões

chmod o+w teste
chmod g-w teste
chmod a=rwx teste

chmod ug=rw teste
chmod 644 teste
chmod 555 teste  / diretorio precisa ter execução 
chmod -R 555 /dir1
chown juca teste
chown juca:fuca arquivo
chown -R :fuca arquivo
chgrp ---> muda somente o grupo 








                     








