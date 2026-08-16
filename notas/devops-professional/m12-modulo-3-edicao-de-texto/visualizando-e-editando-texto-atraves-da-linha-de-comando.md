# Visualizando e editando texto através da linha de comando

_Atualizado em 16/08/2026_

cat -> ver o conteúdo do arquivo
cat -n --> coloca o numero de linhas 

cat > arquivo.txt - criar/digitar o arquivo 
Ctrl + C - para de editar
cat >>> adiciona no final da linha!  
------------------------------------------------------------------------------
 
wc -l -->  quantas linhas 
wc -c -> quantos caracteres
wc -p -> quantas palavras

more/less -> paginadores - less usa setas
less +F arquivo.txt -> transforma em um tail -f mais poderoso 
pausa com o Ctrl + C /  F -> retorna ao modo Follow 
 
( /palavra busca palavra / n --> proxima palavra / N --> palavra anterior )
Você também pode digitar o numero da linha

tail -> final do arquivo ( 10 ultimas linhas )
tail -n ?? -> traz o números de linhas finais
tail -f ->  mostra a linha atualizada - usado para ver logs

seq 1 50 > sequencia.txt -> sequencia de numeros / letras

head -> primeiras linhas ( 10 primeiras linhas )
head -n ?? -> tras o numeros de linhas iniciais  

diff -> compara dois arquivos e ve a diferença entre eles
diff numeros1.txt numeros2.txt
diff -u -> ( mostra a diferença usando sinais - e + )

^     início da linha
$     fim da linha
.     qualquer caractere
*     zero ou mais ocorrências
[ ]   conjunto de caracteres



   





  
 





 

