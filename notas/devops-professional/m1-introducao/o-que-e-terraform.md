# O que é terraform?

_Atualizado em 16/07/2026_


Terraform Core
Binario é um executavel - Binário de linha de comando 
   - ler e interpretar arquivos de Configuração e modulos.
   - gerenciar o estado dos recursos (state)
   - Executar o plano
   - Comunicar-se com os plugins via RPC ( Remote procedure Call)

Terraform Plugins 
Cada plugin implementa a lógica do provider / serviço
   - Inicializa as bibliotecas para as chamadas à API
   - Autenticação com o provedor de Infra ou serviço
   - Definição dos recursos gerenciados e data sources 
   - Funções auxiliares para simplificar a lógica nas configuraçoes 

Lê os arquivos terraform - Tipo HCL - Hashicorp Configuration language ( YAML melhorado ) 
   - Argumentos: atribuem um valor a um nome (image_id = "abc123")
   - Blocos: containers para outros conteúdos, tipo - corpo --> delimitado por { } ex: 
resource "aws_instance" "example" { ... }
Arquitetura baseada em plugins 
Atua de forma descritiva - ( informa o que vc quer )
State file ( Armazena o que foi feito )
   - mapeamento do mundo real --> precisa mapear para saber os recursos disponiveis.
   - metadados --> dependencia entre recursos ( manter um hostórico das dependencias 
   - Performance --> Importante  na performance por que mantem um histórico que acompanha o estado atual da infra.

Bucket S3 - O ideal onde arnmazenar o state file.
Terraform é agnóstico em relação a provedores

Terraform Fluxo de Trabalho 

- Write  ( escrita ) 
   definicção dos recursos em arquivos de configuração HCL, independente de provedores e serviços.
- Plan ( planejamento ) 
   Plano de execução criado com a descrição da infraestrutura criada, atualizada ou destruída, com base na infra existente e na configuração.
- Apply ( aplicação ) 
   Após aprovar o plano, o terraform executa as operações propostas na ordem correta, respeitando as dependencias entre recursos. 

Infraestrutura Mutável --> Servidor criado e modificado ao longo do tempo. ( o problema que com o tempo a máquina pode se tornar única, dificil de reproduzir e dificil de entender - snowflake ("floco de neve")

Infraestrutura imutável --> Ao invés de modificar a máquina existente vc cria uma nova máquinacom a configuração desejada e só passa a uar qnd ela estiver pronta.









