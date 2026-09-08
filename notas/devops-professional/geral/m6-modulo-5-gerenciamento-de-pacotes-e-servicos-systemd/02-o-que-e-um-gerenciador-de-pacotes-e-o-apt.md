# O que é um gerenciador de pacotes e o APT

_Atualizado em 08/09/2026_

Repositórios:

- APT / YUM - DNF --> Possue chave GPG para garantir a procedencia do pacote.

Sources List.

Main - softwares livres, suportado oficialmente pela distro. é o padrão do sistemam recebe update por 5 anos LTS 
Restricted - drivers / softwares proprietários - código fechado mas necessário para o funcionamento da distro
Universe - é mantido pela comunidade, milhares de pacotes open source, mas sem suporte oficial 
Multiverse  contem softwares com licenças restritivas ou problemáticas. Use por sua conta e risco 

Lembrar de habilitar o Universe em servers minimals 
PPA - Personal Package Archives - repositórios mantidos por terceiros (um dev, um projeto, uma empresa) confiança externa a distro
 "sudo add-apt-repository ppa:nginx/stable"




