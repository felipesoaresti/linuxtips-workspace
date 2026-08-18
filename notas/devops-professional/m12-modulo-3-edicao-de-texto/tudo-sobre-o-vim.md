# Tudo sobre o VIM

_Atualizado em 18/08/2026_

i - Inserção!
y-y --> copiar linha  
y-w --> copiar palavra
y-c --> copiar caracter
p - paste -> colar

d d -> remover linha
d-w --> remove palavra
p ---> cola o que removeu 

O - começa a inserir na linha de cima 
o - começa inserir na linha de baixo 
I - começa inserir no inicio da linha 
a - começa inserir um caracter depois 
A - começa inserir no final da linha  

ctrl v - visual bloco
v - modo visual - para copiar é bem legal
V - modo visual line - copia de linha em linha  

u - restaura o que vc fez
ctrl + r - refaz o que vc fez

:w nome_do_arquivo - salva o arquivo com o nome
:q - quit
:wq - salvar e sair 
!- confirma 
e! - força 

:e giropops.txt - edita o giropops.txt
:o arquivo.txt - edita o arquivo.txt
:r giropops.txt - adiciona o conteúdo do arquivo no atual
 
ZZ - salva e sai

/ - pesquisa  
n = next pra baixo  
N - next pra cima

:%s/fusca/fuca feliz/g - muda tudo 
:3s/fusca/fuca/g - muda somente na linha 3
:3,5s/vim/vasco/g - linha 3 ate a 5
 
: set number - set nu - linhas numeradas
: set nonumber set nonu - remove linhas numeradas

: set hlsearch - destaque na busca
: set nohlsearch - remove o destaque 

: set showmode - aparecer mode
: set noshowmode - não aparecer mode

: set ignorecase - ignorar case sensitive
: set noignorecase - não ignorar case sensitive (melhor)

: set incsearch - modo de incrementar ao buscar

: syntax on - modo sintaxe / coloração

: set tabstop=2 - setar o tamanho do tab

: split arquivo.txt - horizontal
: vsplit - vertical 
ctrl ww - para alternar entre arquivos

.vimrc - arquivo de configuração do vim 

  




 



