# Procurando arquivos e diretórios e wildcards

_Exportado em 09/04/2026_

arq-{1,2,3}.txt poderia ser arq-{1..3}.txt
arq-{10..20}.txt - sequencial blocos
mkdir conf && cp /etc/*.conf conf/
* - qualquer coisa --> a frente
? - substitui um caracter 
arq-[1-5].txt - Pega cada caracter
cp arq-2.txt{,.bkp}
FIND: 
find /etc -name nome-do-arquivo
find /etc -(i)name nome-do-arquivo -type {d,f,b,c,l} -size +(-)10k(tamanho do arquivo)
find -mtime +20 --> dias 
-delete --> deleta o arquivo encontrado no find
-exec  ls -lha {} \; --> Executa com o que achar
-exec echo "Achei: {} \:"
ls -lhad(d=diretorio) [aA]rquivo - linux case-sensitive
which --> buscar
file --> tipo de arquivo 




