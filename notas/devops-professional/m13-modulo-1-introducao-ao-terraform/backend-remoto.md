# Backend remoto

_Atualizado em 17/07/2026_

state file --> deve ser configurado no backend - esse arquivo local geralmente é: terraform.tfstate (local) é usado caso não configure antes o backend.tf

.gitignore --> arquivos listados aqui não serão commitados e nem vão para o git --> devem ser inseridos: state-file e a pasta .terraform 

pq não usar state file local:
 - conflitos entre alterações
 - recursos criados sem controle compartilhado
 - colaboração dificultosa
 - risco de perdder o estado ( perca do arquivo)
 - exposição acidental de informações sensíveis

 .terraform.lock.hcl --> registra as versões e informações dos providers e plugins usados --> este arquivo deve ser versionado.

terraform {
  backend "s3" {
    bucket = "mybucket" (nome do seu bucket S3 onde o state file ficará armazenado)
    key    = "path/to/my/key" (caminho do arquivo dentro do bucket)
    region = "us-east-1" (região onde o buckert foi criado)
  }
}


