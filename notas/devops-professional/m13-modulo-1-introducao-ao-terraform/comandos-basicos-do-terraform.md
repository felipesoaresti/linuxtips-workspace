# Comandos básicos do terraform

_Atualizado em 17/07/2026_

terraform init --> inicia o diretório de trabalho do terraform
  - pasta criada --> .terraform ( providers, plugins e etc)
terraform init -upgrade --> verifica se tem versões mais novas dos providers e módulos utilizados 
Arquivo de lock --> registra informações sobre os providers utilizados, incluindo versões e hashes - garante consistencia de versões
Provider --> componente usado para se comunicar com o provedor de serviço 

Olhar a documentação para exportar credenciais, cada provider usa de uma forma
export AWS_ACCESS_KEY_ID="sua-access-key"
export AWS_SECRET_ACCESS_KEY="secret-key"
export AWS_REGION="us-east-1" - caso não defina 


terraform plan -->  Plano de trabalho do terraform ( oque ele fará )
terraform plan -out arq-1 --> salva o arquivo do plano
  - Ele compara: o que esta escrito no código
  - O que esta registrado no State File
  - O que existe no provedor

pode indicar recursos: 
  - criados
  - alterados
  - destruídos
  - mantidos sem mudança

'+' - recurso que sera criado
'-' - recurso que será destruído 
outros símbolos podem indicar alterações ou substituições

terraform apply --> terraform aplica (executa o plano) coloca-se o nome do plano e ele aplica o plano específico, se não ele vai gerar um novo plano e aplicar
terraform destroy --> destroi os recursos criados.
terraform plan -destroy -out destruir --> não é muito usal, mas cria um plano pra destruir os recursos / terraform apply destruir








