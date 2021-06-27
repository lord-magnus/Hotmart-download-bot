# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#            Esse script faz parte de um projeto bem maior, solto no momento pq quero feedback, de tudo.              #
#         Também preciso que ele seja testado contra diversos cursos e que os problemas sejam apresentados.           #
#                                          Meu telegram: @katomaro                                                    #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# Antes de mais nada, instale o FFMPEG no sistema (adicionando-o às variáveis de ambiente)
# Após isso, verifique se instalou as dependências listadas abaixo, pelo pip:
# m3u8, beautifulsoup4, youtube_dl
# Feito isso, só rodar esse .py
# Features esperadas nessa versão:
# # Baixa apenas coisas que não tiveram o download completado anteriormente (com algumas excessões, tipo links.txt)
# # (Se a conexão for perdida em um download do vimeo/youtube, arquivos residuais ficaram na pasta, devem ser apagados
# # Ou seja, aulas hospedadas na hotmart, no vimeo e no youtube
# # Baixa os anexos, salva os links (leitura complementar) e as descrições
# # Mantém tudo salvo na organização da plataforma (<<DEVE SER VERIFICADA A ORDENAÇÃO DE MÓDULOS)
#
# Se algo de estranho acontecer ou se precisar de ajuda, chama no telegram
# # Possivelmente precisarei dos arquivos "log.txt" e do "debug.txt", saiba que o log na pasta raiz tem info de login usada
# # Já o "log.txt" dentro da pasta do curso apenas indica as ações do bot, fácil para acompanhar junto com o "debug.txt"


import time
import datetime
import requests
import m3u8  # pip install m3u8
import re
import os
from bs4 import BeautifulSoup  # pip install beautifulsoup4
import youtube_dl  # pip install youtube_dl
import subprocess
import glob


def loga(curso, status, msg):
    with open(curso+"/log.txt", "a", encoding="utf-8") as logz:
        logz.write(f"[{datetime.datetime.today().replace(microsecond=0)}] {status}: {msg}\n")


def autenticacao(**kwargs):
    if not os.path.exists('temp'):
        os.makedirs('temp')
    for f in glob.glob("temp/*"):
        os.remove(f)
    authMart = requests.session()
    authMart.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36'
    email = kwargs.get("email", None)
    if email is None:
        email = str(input("Qual o email de login?\n"))
    senha = kwargs.get("senha", None)
    if senha is None:
        senha = str(input("Qual a senha de login?\n"))
    data = {'username': email, 'password': senha, 'grant_type': 'password'}

    loga(".", "INFO", f"Tentando autenticar na hotmart com o payload {str(data)}")

    authSparkle = authMart.post('https://api.sparkleapp.com.br/oauth/token', data=data)

    if authSparkle.status_code == 200:
        loga(".", "INFO", f"Autenticação bem sucedida!")
    else:
        loga(".", "ERROR", f"Autenticação falhou. Código do erro:{authSparkle.status_code}")
        loga(".", "ERROR", f"{authSparkle.text}")
    authSparkle = authSparkle.json()

    try:
        params = {'token': authSparkle['access_token']}
    except KeyError:
        print("Email ou senha inválido, saindo")
        loga(".", "ERROR", f"Token não encontrado! User pode ter errado a senha.")
        loga(".", "ERROR", f"{authSparkle}")
        exit(13)
    authMart.headers.clear()
    authMart.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36'
    authMart.headers['authorization'] = 'Bearer ' + str(authSparkle['access_token'])
    return authMart, params


def listacursos(authMart, params):
    produtos = authMart.get('https://api-sec-vlc.hotmart.com/security/oauth/check_token', params=params).json()['resources']

    loga(".", "INFO", f"Listando produtos da conta.")

    cursosValidos = []
    for i in produtos:
        try:
            if i['resource']['status'] == "ACTIVE" and "STUDENT" in i['roles']:
                dominio = i['resource']['subdomain']
                authMart.headers['origin'] = f'https://{dominio}.club.hotmart.com'
                authMart.headers['referer'] = f'https://{dominio}.club.hotmart.com'
                authMart.headers['club'] = dominio
                i["nome"] = re.sub(r'[<>:"/\\|?*]', '', authMart.get('https://api-club.hotmart.com/hot-club-api/rest/v3/membership?attach_token=false').json()['name']).strip()
                cursosValidos.append(i)
        except KeyError:
            loga(".", "WARN", f"Produto presumido como inválido.")
            loga(".", "WARN", f"{i}")
            continue
    for i, curso in enumerate(cursosValidos, start=1):
        print(i, curso['nome'])
    opcao = int(input('Qual curso deseja baixar?\n'))-1
    nmcurso = cursosValidos[opcao]['nome']

    loga(".", "INFO", f"Iniciando download do curso {nmcurso}")
    loga(".", "INFO", f"{cursosValidos[opcao]}")

    if not os.path.exists('Cursos/' + nmcurso):
        os.makedirs('Cursos/' + nmcurso)
    dominio = cursosValidos[opcao]['resource']['subdomain']
    authMart.headers['origin'] = f'https://{dominio}.club.hotmart.com/'
    authMart.headers['referer'] = f'https://{dominio}.club.hotmart.com/'
    authMart.headers['club'] = dominio
    curso = authMart.get('https://api-club.hotmart.com/hot-club-api/rest/v3/navigation').json()
    estrutura = {}
    tempAula =[]
    aulas =[]
    tempAnexo =[]
    tempLink = []
    x = 0

    loga('Cursos/' + nmcurso, "INFO", "Estrutura obtida com sucesso, criando dicionário")

    for modulo in curso['modules']:
        estrutura[modulo['moduleOrder']] = {re.sub(r'[<>:"/\\|?*]', '', modulo['name']).strip(): []}
        for i in modulo['pages']:
            x += 1
            print("Aulas contabilizadas:", x)
            aulas = [i['pageOrder'], re.sub(r'[<>:"/\\|?*]', '', i['name']).strip(), i['hash'], {'videos': []}, {'anexos': []}, {'links': []}]
            aula = authMart.get(f'https://api-club.hotmart.com/hot-club-api/rest/v3/page/{i["hash"]}').json()
            try:
                for video in aula['mediasSrc']:
                    tempAula = [re.sub(r'[<>:"/\\|?*]', '', video['mediaName']).strip(), video['mediaCode'], video['mediaSrcUrl']]
                    aulas[3]['videos'].append(tempAula)
            except KeyError:
                pass
            try:
                for anexo in aula['attachments']:
                    tempAnexo = [anexo['fileMembershipId'], re.sub(r'[<>:"/\\|?*]', '', anexo['fileName']).strip()]
                    aulas[4]['anexos'].append(tempAnexo)
            except KeyError:
                pass
            try:
                for link in aula['complementaryReadings']:
                    tempLink = [re.sub(r'[<>:"/\\|?*]', '', link['articleName']).strip(), link['articleUrl']]
                    aulas[5]['links'].append(tempLink)
            except KeyError:
                pass
            estrutura[modulo['moduleOrder']][re.sub(r'[<>:"/\\|?*]', '', modulo['name']).strip()].append(aulas)

    # Dump do dict caso algo estranho ocorra a pessoa possa mandar, usar prettify.py para ver a monstruosidade
    with open('Cursos/' + nmcurso + '/debug.txt', 'a', encoding='utf-8') as debug:
        debug.write(str(curso['modules'])+'\n\n\n'+str(estrutura))

    loga('Cursos/' + nmcurso, "INFO", "Dicionário criado com sucesso, dumpado como debug.txt")
    loga('Cursos/' + nmcurso, "INFO", f"Total de aulas no curso {nmcurso} {str(x)}")

    for modulo in estrutura:
        for aulas in estrutura[modulo]:
            if not os.path.exists('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas):
                os.makedirs('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas)

                loga('Cursos/' + nmcurso, "INFO", f"Criada a pasta do módulo {str(modulo)}. {aulas}")

            for aula in estrutura[modulo][aulas]:
                print("Verificando a aula\n\t" + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1])
                if not os.path.exists('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1]):

                    os.makedirs('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1])

                    loga('Cursos/' + nmcurso, "INFO", f"Criada a pasta da aula {str(aula[0])}. {aula[1]}")

                try:
                    desct = authMart.get(f'https://api-club.hotmart.com/hot-club-api/rest/v3/page/{aula[2]}').json()['content']
                    with open('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + "/descricao.html", 'w', encoding='utf-8') as dd:
                        dd.write(str(desct))
                        loga('Cursos/' + nmcurso, "INFO", f"Descrição salva com sucesso, aula {str(aula[0])}. {aula[1]}")
                except KeyError:
                    print("Aula sem descrição/não textual")
                except:
                    print("Erro ao salvar descrição, churrasque-se")
                    loga('Cursos/' + nmcurso, "ERROR", f"Falha ao salvar a descrição da aula {str(aula[0])}. {aula[1]}")

                if not aula[3]['videos']:

                    loga('Cursos/' + nmcurso, "WARN", "Aula não continha dicionário de videos, verificando por externos, verificar se é textual")

                    try:
                        pjson = BeautifulSoup(authMart.get(f'https://api-club.hotmart.com/hot-club-api/rest/v3/page/{aula[2]}').json()['content'], features="html.parser")
                        viframe = pjson.findAll("iframe")
                        for x, i in enumerate(viframe, start=1):
                            if 'player.vimeo' in i.get("src"):
                                youtube_dl.utils.std_headers['Referer'] = f"https://{dominio}.club.hotmart.com/"
                                
                                loga('Cursos/' + nmcurso, "INFO", f"Vídeo encontrado! {i.get('src')}")

                                if '?' in i.get("src"):
                                    linkV = i.get("src").split('?')[0]
                                else:
                                    linkV = i.get("src")
                                if linkV[-1] == "/":
                                    linkV = linkV.split("/")[-1]

                            elif 'vimeo.com' in i.get("src"):
                                youtube_dl.utils.std_headers['Referer'] = f"https://{dominio}.club.hotmart.com/"
                                
                                loga('Cursos/' + nmcurso, "INFO", f"Vídeo encontrado! {i.get('src')}")

                                vimeoID = i.get("src").split('vimeo.com/')[1]
                                if "?" in vimeoID:
                                    vimeoID = vimeoID.split("?")[0]
                                linkV = "https://player.vimeo.com/video/"+vimeoID

                            elif "wistia.com" in i.get("src"):

                                loga('Cursos/' + nmcurso, "ERROR", f"WISTIA! Vídeo encontrado! {i.get('src')}")

                                # Método de download caiu, era pelo bin :( Ajuda noix Telegram: @katomaro
                                pass

                            elif "youtube.com" in i.get("src") or "youtu.be" in i.get("src"):

                                loga('Cursos/' + nmcurso, "INFO", f"Vídeo encontrado! {i.get('src')}")

                                linkV = i.get("src")

                            if not os.path.isfile('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/' + f"aula-{str(x)}.mp4"):
                                print("Baixando aula externa\n\t" + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1])
                                ydl_opts = {"format": "best", 'outtmpl': 'Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/' + f"aula-{str(x)}.mp4"}
                                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                    ydl.download([linkV])
                                    loga('Cursos/' + nmcurso, "INFO", f"Vídeo externo baixado com sucesso.")
                            else:
                                print("Aula já presente, pulando")
                                loga('Cursos/' + nmcurso, "INFO", "Aulá já presente! Pulada")

                    except:

                        loga('Cursos/' + nmcurso, "WARN", "Plataforma não retornou vídeos, verificar se é postagem (aula textual)")

                        pass

                else: #0 nome, 1 id, 2 link
                    for x, i in enumerate(aula[3]['videos'], start=1):
                        if not os.path.isfile('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/' + f"aula-{str(x)}.mp4"):
                            print("Tentando baixar aula da hotmart\n\t" + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1])
                            loga('Cursos/' + nmcurso, "INFO", f"Tentando baixar a aula {str(x)} ({aula[1]})")

                            mediaUrl = i[2]
                            authMart.get(mediaUrl)
                            videoHash = i[1]
                            teste = authMart.get(f"https://contentplayer.hotmart.com/video/{videoHash}/hls/master.m3u8")
                            masterPlaylist = m3u8.loads(teste.text)
                            res = []
                            for playlist in masterPlaylist.playlists:
                                res.append(playlist.stream_info.resolution)
                            res.sort(reverse=True)
                            for playlist in masterPlaylist.playlists:
                                if playlist.stream_info.resolution == res[0]:
                                    highestQual = playlist.uri
                            highqual = authMart.get(f"https://contentplayer.hotmart.com/video/{videoHash}/hls/{highestQual}")

                            loga('Cursos/' + nmcurso, "INFO", f"Melhor qualidade encontrada {str(highestQual).split('/')[0]}p")

                            with open('temp/dump.m3u8', 'w') as dump:
                                dump.write(highqual.text)
                            targetm3u8 = m3u8.loads(highqual.text)
                            key = None
                            for segment in targetm3u8.segments:
                                key = segment.key.uri
                                uri = segment.uri
                                frag = authMart.get(f"https://contentplayer.hotmart.com/video/{videoHash}/hls/{highestQual.split('/')[0]}/{uri}")
                                with open("temp/"+uri, 'wb') as sfrag:
                                    sfrag.write(frag.content)
                            print("Segmentos baixados")
                            fragkey = authMart.get(f"https://contentplayer.hotmart.com/video/{videoHash}/hls/{highestQual.split('/')[0]}/{key}")
                            with open("temp/"+str(key), 'wb') as skey:
                                skey.write(fragkey.content)
                            print("Chave de decodificação baixada, concatenando...")
                            ffmpegcmd = 'ffmpeg -hide_banner -loglevel error -allowed_extensions ALL -i temp/dump.m3u8 -preset ultrafast  "Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/' + f'aula-{str(x)}.mp4"'

                            loga('Cursos/' + nmcurso, "INFO", "Iniciando o FFMPEG")

                            subprocess.run(ffmpegcmd)
                            print("Download da aula concluído, limpado pasta temporária...")

                            loga('Cursos/' + nmcurso, "INFO", "FFMPEG concluído, aula baixada.")

                            time.sleep(1)
                            for f in glob.glob("temp/*"):
                                os.remove(f)

                            loga('Cursos/' + nmcurso, "INFO", "Pasta temporária limpa")
                        else:
                            print("Aula já presente, pulando")
                            loga('Cursos/' + nmcurso, "INFO", "Aulá já presente, pulada")

                if aula[4]['anexos']:  #0 id 1 nome
                    print("Anexos encontrados para a aula\n\t" + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1])
                    if not os.path.exists('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/Materiais'):
                        os.makedirs('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/Materiais')
                        loga('Cursos/' + nmcurso, "INFO", f"Anexo detectado, pasta criada na aula {str(aula[0])}. {aula[1]}")
                    for i in aula[4]['anexos']:
                        if not os.path.isfile('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/Materiais/'+i[1]):
                            loga('Cursos/' + nmcurso, "INFO", f"Baixando o anexo {i[1]}")
                            try:
                                anexo = authMart.get(f'https://api-club.hotmart.com/hot-club-api/rest/v3/attachment/{i[0]}/download').json()
                                anexo = requests.get(anexo['directDownloadUrl'])
                            except KeyError:
                                vrum = requests.session()
                                vrum.headers.update(authMart.headers)
                                lambdaUrl = anexo['lambdaUrl']
                                vrum.headers['token'] = anexo['token']
                                anexo = requests.get(vrum.get(lambdaUrl).text)
                                del vrum
                            with open('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + '/Materiais/'+i[1], 'wb') as ann:
                                ann.write(anexo.content)
                            loga('Cursos/' + nmcurso, "INFO", f"Anexo baixado com sucesso {i[1]}")
                            print(f"Anexo baixado com sucesso: {i[1]}")
                        else:
                            print(f"Anexo já existente, pulado, {i[1]}")
                            loga('Cursos/' + nmcurso, "INFO", f"Anexo já existente {i[1]}")

                if aula[5]['links']:  #0 nome 1 url
                    print("Salvando links encontrados para a aula\n\t" + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1])
                    loga('Cursos/' + nmcurso, "INFO", f"Links detectados para a aula {str(aula[0])}{aula[1]}")
                    with open('Cursos/' + nmcurso + '/' + str(modulo) + '. ' + aulas + '/' + str(aula[0]) + '. ' + aula[1] + "/links.txt", "a", encoding="utf-8") as linkz:
                        for i in aula[5]['links']:
                            linkz.write(f"{i[0]}: {i[1]}\n")
                    loga('Cursos/' + nmcurso, "INFO", "Links salvos")


# login = {"email": "EMAIL@EMAIL", "senha": "SENHA"}
login = {"Info": "Pode colocar o email/senha ali em cima e apagar esse dicionário para deixar os dados salvos no script",
          "autor": "Telegram: @katomaro"}


listacursos(*autenticacao(**login))
