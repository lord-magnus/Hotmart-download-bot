# Bot para download de cursos da Hotmart (popularmente conhecido como KatoMart :purple_heart:)

## O que faz?
Esse programinha tem como objetivo fazer o download de cursos completos da Hotmart Club na qualidade mais alta, e isso é feito consumindo sua API. Ao invés de ter de usar algo como por exemplo o [Tubedigger](https://www.tubedigger.com/) ou algum outro método manual maçante para fazer o download de cursos é possível simplesmente colocar seu login (ou de outra pessoa xd) nesse script, apertar enter e ir dormir enquanto o curso é baixado.

## Da legalidade...
Sim, é um programa super legal :). Piada de lado, é literalmente o mesmo cenário de você fazer o download do curso inteiro usando alguma outra ferramenta, ou, na pior das hipóteses, gravar a tela. Você é responsável pelo conteúdo extraído da plataforma e o que quer que você faça com ele. **Não que tenha alguma forma deles saberem que veio de você, se me entende, ~500 cursos baixados com sucesso aqui ;p**

## Funcionalidades:
- [x] Download de curso da plataforma mantendo a estrutura original do mesmo ¹ ² ³;
- [x] Download de todos os cursos de determinada conta de forma sequencial;
- [x] Verificação para 'resumir' downloads encerrados de forma prematura ⁴
- [ ] Encoding de video para reduzir o tamanho final;
- [ ] Edição de arquivos PDF automatica para remover dados do comprador;
- [ ] Permitir a seleção de qualidade ao invés de sempre baixar a mais alta;
- [ ] Download de módulo/aula seletivo;
- [ ] Suporte para controle por Telegram/Discord;
- [ ] Envio de arquivos para a nuvem automaticamente;    

¹: A numeração as vezes sai incorreta, parecendo haver lacunas, porém, o conteúdo está correto. A numeração é na realidade o atributo 'position' dado pela plataforma, eles ordenam no front-end seguindo ordem ascendente.  
²: Essa versão não baixa aulas bloqueadas (:lock:).  
³: Aulas do player **Wistia** são puladas, preciso de um curso que utilize esse player para implementar no programa.  
⁴: Caso o download seja encerrado de forma prematura (terminal fechado por exemplo), uma pasta temporária com nome aleatório deverá ser excluída manualmente pelo usuário.
## Como utilizar:
*Primeiramente*, o programa é feito em [Python](https://www.python.org/), então obviamente você deve o ter instalado em sua máquina. Segundamente você deve instalar o [FFMPEG](http://ffmpeg.org/).
### Se estiver no Windows...
- Vá no site de um developer, localize a **release-full**, baixe e descompacte para uma pasta que você não irá mexer/mudar de lugar.
- Na pesquisa do sistema, procure por "Variáveis de Ambiente" (caso seu sistema esteja em inglês, procure por "Environment Variables"), clique no resultado e na janela que abrir, no botão destacado em azul no canto inferior direito para editar. **MUITO CUIDADO A PARTIR DAQUI!**
 - Na tabela com o nome de Sistema, encontre a linha do "PATH" (o nome é o mesmo em inglês), e clique para editar.
 - **Não exclua nada!** Pois isso pode fazer com que o Windows não encontre aplicativos que você usa, assim invalidando sua instalação. SImplesmente clique para navegar e vá até a pasta extraída anteriormente, você deve selecionar a pasta "bin" (que possui o ffmpeg.exe).
 - Abra um CMD novo (ou reinicie um que já estava aberto) e digite "ffmpeg", caso apareça as informações do programa você fez de forma correta, caso apareça que "comando não reconhecido" tente reiniciar a máquina, se mesmo assim não funcionar, verifique qual pasta você adicionou no PATH e o conteúdo da mesma.
 ### Se estiver no Linux...
 - sudo apt-get install ffmpeg.  
 ¯\\\_(ツ)_/¯
 ### Após instalar o FFMPEG...
 - Baixe/clone o repositório (botão verde lá em cima :p );
 - Navegue até a pasta pelo terminal (comando 'cd');
 - Instale as dependências Python utilizando o comando `pip install -r requirements.txt`
- Execute o programinha pelo comando `python KatoMart.py`, ou o nome que você salvou o arquivo .py, ele irá perguntar seu Email e Senha da Hotmart, basta digitar e após isso ele irá listar os cursos disponíveis na conta.
- Divirta-se.

# Caso encontre problemas ou tenha sugestões...
Utilize a aba de Issues aqui no GitHub para deixar a informação/opinião pública. Ou se preferir, entre em contato comigo pelo [Telegram](https://t.me/katomaro)