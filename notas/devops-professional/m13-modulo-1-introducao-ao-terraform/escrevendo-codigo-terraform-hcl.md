# Escrevendo código terraform (HCL)

_Atualizado em 17/07/2026_

resource - Bloco de código terraform - Crie um recurso novo  ( ex: resource de VM )
data - Bloco de código terraform - Busca a informação de recurso existente 

AMI - Padrão de imagem da AWS - Máquina nova id da AMI - lembrar um snapshot

Documentação Oficial 

https://developer.hashicorp.com/terraform/docs
/*
resource "aws_vpc" "main" {
  cidr_block = var.base_cidr_block
}

<BLOCK TYPE> "<BLOCK LABEL>" "<BLOCK LABEL>" {
  # Block body
  <IDENTIFIER> = <EXPRESSION> # Argument
}

*\

