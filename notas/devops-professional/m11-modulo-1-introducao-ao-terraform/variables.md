# Variables

_Atualizado em 30/07/2026_

- deixam o código mais limpo e reutilizável 
- o mesmocódigo podem ser usado mais vezes

variavel "image_id" (nome-da-variavel) {
  type = string 
}

- Para acessar a variável ela deve ser informada no código:  
    ami = var.image_id

- Pode-se informar a variavel por linha de comando: 
    terraform plan -out plano -var 'image_id=ami-abc123'

- O argumento 'default' define valor padrão.
    variable "image_id" {
      type = string 
      default = "ami-123456"
    }

- 'type' - Tipo de argumento é aceito pela variável / informa o tipo
- 'description' - permite documentar a variável
- 'sensitive' - torna o valor da variável sensivel e não sera exposta nos 'plan' e nos logs 

- Arquivos .tfvars - forma de passar valores de variáveis usando arquivos
    image_id = 'ami-abc123'
  Para usar o arquivo : 
    terraform plan -out plano -var-file teste.tfvar

- Arquivo terraform.tfvars --> carregado automaticamente pelo terraform, se existir os valores dessas variaveis serão carregados automaticamente.
    image_id = "ami-terraform-tfvars"
  Outro arquivo carregado automaticamente é o:  .auto.tfvars
    testing.auto.tfvars
  Isso é útil para separar valores pot ambiente e contexto

- Valores passados por variáveis de ambiente, usamos o prefixo: TF_VAR 
    export TF_VAR_image_id="ami-env-var"
  Funciona apenas no terminal onde foi definida

- Precedência de valores:
    Variáveis de ambiente;
    Arquivo terraform.tfvars;
    Arquivos *.auto.tfvars;
    opção -var;
    opção -var-file;

 


  
   
      









