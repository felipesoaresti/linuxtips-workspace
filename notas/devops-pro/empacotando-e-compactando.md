# Empacotando e compactando

_Exportado em 09/04/2026_

TAR:
empacotar --> colocar na caixa
compactar --> colocar na caixa e deixar menor
tar -c(criar)z(gzipar)v(verbose)(file) backup-projeto.tar(empacotar).gz(compactar) projeto/
tar -czvf backup-projeto.tar.gz projeto/  -->criar arquivo
tar -t --> para ver o conteúdo
tar -tzf nome-arquivo 
tar -x(desempacotar)zf
tar -xzvf backup -projeto.tar.gz -C bkp/ --> descompactar o arquivo no local (criando diretorio)

type --> j = bz2 / z = gz
gzip --> compactar( ) /(-d) descompactar 
bzip2 --> igual gzip
dd if=/dev/zero of=girus bs=1M count=5
time --> qnt tempo demora



