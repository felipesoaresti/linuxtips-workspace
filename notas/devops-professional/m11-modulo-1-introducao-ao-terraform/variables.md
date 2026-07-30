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

- 
      









