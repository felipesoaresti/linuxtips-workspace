# Providers

_Atualizado em 28/07/2026_

Provider é o responsável por viabilizar a comunicação com provedores/sistemas externos
Terraform registry é onde encontramos a documentação dos providers. 
- Provider é instalado na hora e com o terraform init 
  * .teraform/ --> onde ficam os arquivos dos providers baixados ( -update para atualizar )
  * terraform trabalha com cache para os providers - reduz consumo de banda
  * Categorias de Providers 
      Official - mantidos pela Hashicorp
      Partner - mantidos por parceiros 
      Community - mantidos pela comunidade 
      Archived - Arquivados / Descontinuados 

provider "aws" {
  region = "us-east-1"
}

PROVIDER BLOCK

- região
- endpoint 
- credenciais
- perfil
- configurações específicas da plataforma
              
     


