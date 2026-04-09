# O Resgate do Servidor Legacy
Você acabou de herdar um servidor que está com o disco quase cheio e uma organização de arquivos caótica. Sua missão é organizar a casa, investigar logs e preparar o terreno para uma automação, tudo isso usando os atalhos de produtividade que você aprendeu.
---
## Instrucoes

## Desafio: O Resgate do Servidor "Legacy"

**IMPORTANTE!**
Adicionar no arquivo notas-DLCN-modulo-1.txt um resumo do que você fez durante o desafio abaixo, adicione como você se sentiu com o nível do desafio e o qual ficou confortavel com o conteúdo. Adicione o que você aprendeu, e se quiser tirar nota máxima, explique o que é cada coisa que você aprendeu! :)

**Contexto:** Você acabou de herdar um servidor que está com o disco quase cheio e uma organização de arquivos caótica. Sua missão é organizar a casa, investigar logs e preparar o terreno para uma automação, tudo isso usando os atalhos de produtividade que você aprendeu.

### Parte 1: Investigação e Diagnóstico
1.  **Onde estou?** Confirme seu diretório atual e liste **todos** os arquivos (incluindo ocultos) em formato legível para humanos, ordenando pelo **tamanho** do arquivo.
2.  **Exploração FHS:** Sem sair do seu diretório `home`, liste o conteúdo de `/var/log` para ver qual arquivo de log parece ser o maior.
3.  **DNA do Sistema:** Descubra qual é a distribuição Linux e a versão do Kernel rodando nessa máquina consultando os arquivos dentro de `/etc` e `/proc`.

### Parte 2: Operação "Faxina e Organização"
Execute as tarefas abaixo usando o **mínimo de comandos possível** (use o `mkdir -p` e chaves `{}` se souber, ou apenas a lógica do `-p`):

1.  **Estrutura Nova:** Crie a seguinte estrutura dentro do seu home:
    `backups/config/ssh` e `backups/logs/old`.
2.  **Preservação:** Copie o arquivo de configuração do servidor SSH (`/etc/ssh/sshd_config`) para a pasta `backups/config/ssh/` que você acabou de criar.
3.  **Movimentação Relativa:** Entre na pasta `backups/logs/old`. A partir daí, usando **caminho relativo**, crie um arquivo vazio chamado `placeholder.txt` dentro da pasta `backups/config/`.
4.  **O "Pulo do Gato":** Use o comando `cd -` para voltar ao diretório anterior e depois `cd ~` para voltar ao home.

### Parte 3: Produtividade e Segurança
1.  **Histórico Ninja:** Use o `Ctrl+R` para encontrar o comando que você usou para copiar o arquivo do SSH e execute-o novamente, mas desta vez mude o destino para `/tmp`.
2.  **Alias de Resgate:** Crie um alias temporário chamado `cadê` que execute o comando `pwd`.
3.  **Simulação de Perigo:** * Crie uma pasta chamada `PERIGO`.
    * Tente removê-la com `rm PERIGO`. 
    * O que aconteceu? Por que falhou? 
    * Agora remova-a da forma correta para diretórios.

---

## 📝 Questões de Reflexão (Teoria)

1.  Se um desenvolvedor te disser: *"O banco de dados parou de gravar dados porque o disco encheu"*, em qual diretório do FHS você começaria a procurar por arquivos de dados pesados e logs antigos?
2.  Qual a diferença prática entre `cd ..` e `cd /`?
3.  Por que o uso do `Tab` é considerado uma "medida de segurança" além de ser um recurso de velocidade?

---

### 💡 Dica de Ouro:
Tente realizar todo o desafio **sem usar o mouse** para nada. Se errar um comando longo, não use a seta para a esquerda; use `Ctrl+A` ou `Ctrl+W`. Sinta o terminal!
## Arquivos para editar

- `notas-DLCN-modulo-1.txt`

## Conteudo inicial dos arquivos

### `notas-DLCN-modulo-1.txt`

```yaml
# Adicione suas notas abaixo! Capriche! :)
```

---
*Desafio LINUXtips - devops-pro*