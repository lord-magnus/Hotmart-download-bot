# coding=utf-8

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#            Esse script faz parte de um projeto bem maior,                   #
#             solto no momento pq quero feedback, de tudo.                    #
#         Também preciso que ele seja testado contra diversos cursos          #
#               e que os problemas sejam apresentados.                        #
#                      Meu telegram: @katomaro                                #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# Antes de mais nada, instale o FFMPEG no sistema 
# (adicionando-o às variáveis de ambiente)
#
# Após isso, verifique se instalou as dependências listadas abaixo, pelo pip:
# m3u8, beautifulsoup4, youtube_dl
#
# Feito isso, só rodar esse .py

# Features esperadas nessa versão:
#   • Baixa apenas coisas que não tiveram o download completado anteriormente 
#       (com algumas excessões, tipo links.txt)
#   • Se a conexão for perdida em um download do vimeo/youtube, 
#       arquivos residuais ficaram na pasta, devem ser apagados
#   • Ou seja, aulas hospedadas na hotmart, no vimeo e no youtube
#   • Baixa os anexos, salva os links (leitura complementar) e as descrições
#   • Mantém tudo salvo na organização da plataforma
#       (<<DEVE SER VERIFICADA A ORDENAÇÃO DE MÓDULOS)

# Se algo de estranho acontecer ou se precisar de ajuda, chama no telegram.
#
# Possivelmente precisarei dos arquivos "log.txt" e do "debug.txt", 
# saiba que o log na pasta raiz tem info de login usada. 
# Já o "log.txt" dentro da pasta do curso apenas indica as ações do bot,
# fácil para acompanhar junto com o "debug.txt".

import random
import string
import datetime
import requests
import re
import glob
import youtube_dl
import os
import time
import m3u8
import json
import subprocess
import sys

from bs4 import BeautifulSoup

from requests import HTTPError, Timeout
from requests.exceptions import ChunkedEncodingError, ContentDecodingError

from AnsiEscapeCodes import Colors

# GLOBALS
userEmail = input("Qual o seu Email da Hotmart?\n")
userPass = input("Qual a sua senha da Hotmart?\n")
maxCursos = 0
cursoAtual = 1

class Hotmart:
    _userAgent = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        ' AppleWebKit/537.36 (KHTML, like Gecko)'
        ' Chrome/91.0.4472.106 Safari/537.36'
    )

    def auth(userEmail, userPass):
        authMart = requests.session()
        authMart.headers['user-agent'] = _userAgent

        data = {
            'username': userEmail,
            'password': userPass,
            'grant_type': 'password'
        }

        authSparkle = authMart.post(
            'https://api.sparkleapp.com.br/oauth/token',
            data=data)

        authSparkle = authSparkle.json()

        try:
            authMart.headers.clear()
            authMart.headers['user-agent'] = _userAgent
            authMart.headers['authorization'] = f"Bearer {authSparkle['access_token']}"
        except KeyError:
            print(f"{Colors.Red}{Colors.Bold}Tentativa de login falhou! Verifique os dados ou contate o @katomaro (Telegram){Colors.Reset}")
            exit(13)
        return authMart

    def getProdutos(authMart):
        return authMart.get(
            'https://api-sec-vlc.hotmart.com/security/oauth/check_token',
            params={'token': authMart.headers['authorization'].split(" ")[1]}) \
            .json()['resources']

    def getCursos(authMart):
        produtos = getProdutos(authMart)
        cursosValidos = []

        for produto in produtos:
            try:
                if produto['resource']['status'] == "ACTIVE" or "STUDENT" in produto['roles']:
                    dominio = produto['resource']['subdomain']

                    authMart.headers['origin'] = f'https://{dominio}.club.hotmart.com'
                    authMart.headers['referer'] = authMart.headers['origin']
                    authMart.headers['club'] = dominio

                    membership = authMart.get('https://api-club.hotmart.com/hot-club-api/rest/v3/membership?attach_token=false') \
                        .json()['name']

                    produto["nome"] = re.sub(r'[<>:!"/\\|?*]', '', ) \
                        .strip() \
                        .replace(".", "") \
                        .replace("\t", "")

                    cursosValidos.append(produto)
            except KeyError:
                continue

        return cursosValidos

def clearScreen():
    if sys.platform.startswith('darwin'):
        # MacOs specific procedures
        os.system("clear")
    elif sys.platform.startswith('win32'):
        # Windows specific procedures
        os.system("cls")

def verCursos():
    authMart = Hotmart.auth(userEmail, userPass)
    cursosValidos = Hotmart.getCursos(authMart)

    print("Cursos disponíveis para download:")

    for i, curso in enumerate(cursosValidos, start=1):
        print("\t", i, curso['nome'])

    opcao = int(input( f"Qual curso deseja baixar? {Colors.Magenta}(0 para todos!){Colors.Reset}\n")) - 1

    if opcao == -1:
        global maxCursos
        maxCursos = len(cursosValidos)

        for curso in cursosValidos:
            baixarCurso(authMart, curso, True)
    else:
        baixarCurso(authMart, cursosValidos[opcao], False)

def baixarCurso(authMart, infoCurso, dAll):
    while True:
        tempFolder = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=7))
        if not os.path.isdir(tempFolder):
            os.makedirs(tempFolder)
            break
        else:
            continue

    nmcurso = re.sub(r'[<>:!"/\\|?*]', '', infoCurso['nome']
                     ).strip().replace('.', '').replace("\t", "")
    if not os.path.exists('Cursos/' + nmcurso):
        os.makedirs('Cursos/' + nmcurso)
    
    clearScreen()

    if dAll:
        global maxCursos
        global cursoAtual
        print(
            f"{Colors.Magenta}Modo de download de todos os cursos! {cursoAtual}/{maxCursos}")
        cursoAtual += 1
    dominio = infoCurso['resource']['subdomain']
    youtube_dl.utils.std_headers['Referer'] = f"https://{dominio}.club.hotmart.com/"
    authMart.headers['accept'] = 'application/json, text/plain, */*'
    authMart.headers['origin'] = f'https://{dominio}.club.hotmart.com/'
    authMart.headers['referer'] = f'https://{dominio}.club.hotmart.com/'
    authMart.headers['club'] = dominio
    authMart.headers['pragma'] = 'no-cache'
    authMart.headers['cache-control'] = 'no-cache'
    curso = authMart.get(
        'https://api-club.hotmart.com/hot-club-api/rest/v3/navigation').json()
    print(f"Baixando o curso: {Colors.Cyan}{Colors.Bold}{nmcurso}{Colors.Reset} (pressione {Colors.Magenta}ctrl+c{Colors.Reset} a qualquer momento para {Colors.Red}cancelar{Colors.Reset})")
    # Descomentar para ver o que caralhos a plataforma dá de json de curso
    # with open('data.json', 'w', encoding='utf-8') as f:
    #     json.dump(curso, f, ensure_ascii=False, indent=4)
    moduleCount = 0
    lessonCount = 0
    vidCount = 0
    segVideos = 0
    descCount = 0
    attCount = 0
    linkCount = 0
    videosLongos = 0
    descLongas = 0
    linksLongos = 0
    anexosLongos = 0
    videosInexistentes = 0
    try:
        for module in curso['modules']:
            nmModulo = f"{module['moduleOrder']}. " + re.sub(
                r'[<>:!"/\\|?*]', '', module['name']).strip().replace('.', '').replace("\t", "")
            if not os.path.exists(f"Cursos/{nmcurso}/{nmModulo}"):
                try:
                    os.makedirs(f"Cursos/{nmcurso}/{nmModulo}")
                except:
                    pass
            moduleCount += 1
            for aula in module['pages']:
                nmAula = f"{aula['pageOrder']}. " + re.sub(
                    r'[<>:!"/\\|?*]', '', aula['name']).strip().replace('.', '').replace("\t", "")
                print(f"{Colors.Magenta}Tentando baixar a aula: {Colors.Cyan}{nmModulo}{Colors.Magenta}/{Colors.Green}{nmAula}{Colors.Magenta}!{Colors.Reset}")
                if not os.path.exists(f"Cursos/{nmcurso}/{nmModulo}/{nmAula}"):
                    try:
                        os.makedirs(f"Cursos/{nmcurso}/{nmModulo}/{nmAula}")
                    except:
                        pass
                lessonCount += 1
                #  TODO Melhorar isso lol
                while True:
                    try:
                        infoGetter = authMart
                        infoAula = infoGetter.get(
                            f'https://api-club.hotmart.com/hot-club-api/rest/v3/page/{aula["hash"]}').json()
                        break
                    except (HTTPError, ConnectionError, Timeout, ChunkedEncodingError, ContentDecodingError):
                        authMart = Hotmart.auth(userEmail, userPass)
                        authMart.headers['accept'] = 'application/json, text/plain, */*'
                        authMart.headers['origin'] = f'https://{dominio}.club.hotmart.com/'
                        authMart.headers['referer'] = f'https://{dominio}.club.hotmart.com/'
                        authMart.headers['club'] = dominio
                        authMart.headers['pragma'] = 'no-cache'
                        authMart.headers['cache-control'] = 'no-cache'
                        continue
                # Descomentar para ver o que caralhos a plataforma retorna na página
                # with open('aula.json', 'w', encoding='utf-8') as f:
                #     json.dump(infoAula, f, ensure_ascii=False, indent=4)

                # Download Aulas Nativas (HLS)
                tryDL = 2
                while tryDL:
                    try:
                        try:
                            for x, media in enumerate(infoAula['mediasSrc'], start=1):
                                if media['mediaType'] == "VIDEO":
                                    print(
                                        f"\t{Colors.Magenta}Tentando baixar o vídeo {x}{Colors.Reset}")
                                    aulagetter = authMart
                                    playerData = aulagetter.get(
                                        media['mediaSrcUrl']).text
                                    # Descomentar para ver o que caralhos a plataforma retorna do player
                                    # with open("player.html", "w") as phtml:
                                    #     phtml.write(playerData)
                                    playerInfo = json.loads(BeautifulSoup(playerData, features="html.parser").find(
                                        text=re.compile("window.playerConfig"))[:-1].split(" ", 2)[2])
                                    segVideos += playerInfo['player']['mediaDuration']
                                    for asset in playerInfo['player']['assets']:
                                        # TODO Melhorar esse workaround para nome longo
                                        filePath = os.path.dirname(
                                            os.path.abspath(__file__))
                                        aulaPath = f"{filePath}/Cursos/{nmcurso}/{nmModulo}/{nmAula}/aula-{x}.mp4"
                                        if len(aulaPath) > 254:
                                            if not os.path.exists(f"Cursos/{nmcurso}/ev"):
                                                os.makedirs(
                                                    f"Cursos/{nmcurso}/ev")
                                            tempNM = ''.join(random.choices(
                                                string.ascii_uppercase + string.digits, k=8))
                                            with open(f"Cursos/{nmcurso}/ev/list.txt", "a", encoding="utf-8") as safelist:
                                                safelist.write(
                                                    f"{tempNM} = {nmcurso}/{nmModulo}/{nmAula}/aula-{x}.mp4\n")
                                            aulaPath = f"Cursos/{nmcurso}/ev/{tempNM}.mp4"
                                            videosLongos += 1
                                        if not os.path.isfile(aulaPath):
                                            videoData = aulagetter.get(
                                                f"{asset['url']}?{playerInfo['player']['cloudFrontSignature']}")
                                            masterPlaylist = m3u8.loads(
                                                videoData.text)
                                            res = []
                                            highestQual = None
                                            for playlist in masterPlaylist.playlists:
                                                res.append(
                                                    playlist.stream_info.resolution)
                                            res.sort(reverse=True)
                                            for playlist in masterPlaylist.playlists:
                                                if playlist.stream_info.resolution == res[0]:
                                                    highestQual = playlist.uri
                                            if highestQual is not None:
                                                videoData = aulagetter.get(
                                                    f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual}?{playerInfo['player']['cloudFrontSignature']}")
                                                with open(f'{tempFolder}/dump.m3u8', 'w') as dump:
                                                    dump.write(videoData.text)
                                                videoPlaylist = m3u8.loads(
                                                    videoData.text)
                                                key = videoPlaylist.segments[0].key.uri
                                                totalSegmentos = videoPlaylist.segments[-1].uri.split(".")[
                                                    0].split("-")[1]
                                                for segment in videoPlaylist.segments:
                                                    print(f"\r\tBaixando o segmento {Colors.Blue}{segment.uri.split('.')[0].split('-')[1]}{Colors.Reset}/{Colors.Magenta}{totalSegmentos}{Colors.Reset}!",
                                                          end="", flush=True)
                                                    uri = segment.uri
                                                    frag = aulagetter.get(
                                                        f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual.split('/')[0]}/{uri}?{playerInfo['player']['cloudFrontSignature']}")
                                                    with open(f"{tempFolder}/" + uri, 'wb') as sfrag:
                                                        sfrag.write(
                                                            frag.content)
                                                fragkey = aulagetter.get(
                                                    f"{asset['url'][:asset['url'].rfind('/')]}/{highestQual.split('/')[0]}/{key}?{playerInfo['player']['cloudFrontSignature']}")
                                                with open(f"{tempFolder}/{key}", 'wb') as skey:
                                                    skey.write(fragkey.content)
                                                print(
                                                    f"\r\tSegmentos baixados, gerando video final! {Colors.Red}(dependendo da config do pc este passo pode demorar até 20 minutos!){Colors.Reset}", end="\n", flush=True)

                                                # TODO Implementar verificação de hardware acceleration
                                                # ffmpegcmd = f'ffmpeg -hide_banner -loglevel error -v quiet -stats -allowed_extensions ALL -hwaccel cuda -i {tempFolder}/dump.m3u8 -c:v h264_nvenc -n "{aulaPath}"'

                                                ffmpegcmd = f'ffmpeg -hide_banner -loglevel error -v quiet -stats -allowed_extensions ALL -i {tempFolder}/dump.m3u8 -n "{aulaPath}"'

                                                if sys.platform.startswith('darwin'):
                                                    # MacOs specific procedures
                                                    subprocess.run(
                                                        ffmpegcmd, shell=True)
                                                elif sys.platform.startswith('win32'):
                                                    # Windows specific procedures
                                                    subprocess.run(ffmpegcmd)

                                                # TODO Implementar verificação de falha pelo FFMPEG
                                                # p = subprocess.run(ffmpegcmd)
                                                # if p.returncode != 0:
                                                #     pass

                                                vidCount += 1
                                                print(
                                                    f"Download da aula {Colors.Bold}{Colors.Magenta}{nmModulo}/{nmAula}{Colors.Reset} {Colors.Green}concluído{Colors.Reset}!")
                                                time.sleep(3)
                                                for ff in glob.glob(f"{tempFolder}/*"):
                                                    os.remove(ff)

                                            else:
                                                print(
                                                    f"{Colors.Red}{Colors.Bold}Algo deu errado ao baixar a aula, redefinindo conexão para tentar novamente!{Colors.Reset}")
                                                raise HTTPError
                                        else:
                                            print("VIDEO JA EXISTE")
                                            vidCount += 1

                                    # tryDL = 0

                        # Download de aula Externa
                        except KeyError:
                            try:
                                fonteExterna = None
                                pjson = BeautifulSoup(
                                    infoAula['content'], features="html.parser")
                                viframe = pjson.findAll("iframe")
                                for x, i in enumerate(viframe, start=1):
                                    # TODO Mesmo trecho de aula longa zzz

                                    filePath = os.path.dirname(
                                        os.path.abspath(__file__))
                                    aulaPath = f"{filePath}/Cursos/{nmcurso}/{nmModulo}/{nmAula}/aula-{x}.mp4"
                                    if len(aulaPath) > 254:
                                        if not os.path.exists(f"Cursos/{nmcurso}/ev"):
                                            os.makedirs(f"Cursos/{nmcurso}/ev")
                                        tempNM = ''.join(random.choices(
                                            string.ascii_uppercase + string.digits, k=8))
                                        with open(f"Cursos/{nmcurso}/ev/list.txt", "a", encoding="utf-8") as safelist:
                                            safelist.write(
                                                f"{tempNM} = {nmcurso}/{nmModulo}/{nmAula}/aula-{x}.mp4\n")
                                        aulaPath = f"Cursos/{nmcurso}/ev/{tempNM}.mp4"
                                        videosLongos += 1

                                    if not os.path.isfile(aulaPath):
                                        ydl_opts = {"format": "best",
                                                    'retries': 3,
                                                    'fragment_retries': 5,
                                                    'quiet': True,
                                                    "outtmpl": f"{aulaPath}"}

                                        if 'player.vimeo' in i.get("src"):
                                            fonteExterna = f"{Colors.Cyan}Vimeo{Colors.Reset}"
                                            if "?" in i.get("src"):
                                                linkV = i.get(
                                                    "src").split("?")[0]
                                            else:
                                                linkV = i.get("src")
                                            if linkV[-1] == "/":
                                                linkV = linkV.split("/")[-1]

                                        elif 'vimeo.com' in i.get("src"):
                                            fonteExterna = f"{Colors.Cyan}Vimeo{Colors.Reset}"
                                            vimeoID = i.get("src").split(
                                                'vimeo.com/')[1]
                                            if "?" in vimeoID:
                                                vimeoID = vimeoID.split("?")[0]
                                            linkV = "https://player.vimeo.com/video/" + vimeoID

                                        elif "wistia.com" in i.get("src"):
                                            # TODO Implementar Wistia
                                            fonteExterna = None
                                            # fonteExterna = f"{C.Yellow}Wistia{C.Reset}"
                                            # Preciso de um curso que tenha aula do Wistia para ver como tá sendo dado
                                            # :( Ajuda noix Telegram: @katomaro
                                            raise KeyError

                                        elif "youtube.com" in i.get("src") or "youtu.be" in i.get("src"):
                                            fonteExterna = f"{Colors.Red}YouTube{Colors.Reset}"
                                            linkV = i.get("src")

                                        if fonteExterna is not None:
                                            print(
                                                f"{Colors.Magenta}Baixando aula externa de fonte: {fonteExterna}!")
                                            try:
                                                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                                    ydl.download([linkV])
                                                vidCount += 1
                                            # TODO especificar os erros de Live Agendada(YouTube) e Video Inexistente
                                            except:
                                                print(
                                                    f"{Colors.Red}O vídeo é uma Live Agendada, ou, foi apagado!{Colors.Reset}")
                                                with open(f"Cursos/{nmcurso}/erros.txt", "a", encoding="utf-8") as elog:
                                                    elog.write(
                                                        f"{linkV} - {nmcurso}/{nmModulo}/{nmAula}")
                                                videosInexistentes += 1
                                    else:
                                        vidCount += 1

                                # tryDL = 0

                            except KeyError:
                                print(
                                    f"{Colors.Bold}{Colors.Red}Ué, erro ao salvar essa aula, pulada!{Colors.Reset} (verifique se ela tem vídeo desbloqueado na plataforma)")
                                tryDL = 0

                        # Count Descrições
                        try:
                            if infoAula['content']:
                                # TODO Mesmo trecho de aula longa zzz

                                filePath = os.path.dirname(
                                    os.path.abspath(__file__))
                                aulaPath = f"{filePath}/Cursos/{nmcurso}/{nmModulo}/{nmAula}/desc.html"
                                if len(aulaPath) > 254:
                                    if not os.path.exists(f"Cursos/{nmcurso}/ed"):
                                        os.makedirs(f"Cursos/{nmcurso}/ed")
                                    tempNM = ''.join(random.choices(
                                        string.ascii_uppercase + string.digits, k=8))
                                    with open(f"Cursos/{nmcurso}/ed/list.txt", "a", encoding="utf-8") as safelist:
                                        safelist.write(
                                            f"{tempNM} = {nmcurso}/{nmModulo}/{nmAula}/desc.html\n")
                                    aulaPath = f"Cursos/{nmcurso}/ed/{tempNM}.html"
                                    descLongas += 1

                                if not os.path.isfile(f"{aulaPath}"):
                                    with open(f"{aulaPath}", "w", encoding="utf-8") as desct:
                                        desct.write(infoAula['content'])
                                        print(
                                            f"{Colors.Magenta}Descrição da aula salva!{Colors.Reset}")
                                descCount += 1

                        except KeyError:
                            pass

                        # Count Anexos
                        try:
                            for att in infoAula['attachments']:
                                print(
                                    f"{Colors.Magenta}Tentando baixar o anexo: {Colors.Red}{att['fileName']}{Colors.Reset}")
                                # TODO Mesmo trecho de aula longa zzz

                                filePath = os.path.dirname(
                                    os.path.abspath(__file__))
                                aulaPath = f"{filePath}/Cursos/{nmcurso}/{nmModulo}/{nmAula}/Materiais/{att['fileName']}"
                                if len(aulaPath) > 254:
                                    if not os.path.exists(f"Cursos/{nmcurso}/et"):
                                        os.makedirs(f"Cursos/{nmcurso}/et")
                                    tempNM = ''.join(random.choices(
                                        string.ascii_uppercase + string.digits, k=8))
                                    with open(f"Cursos/{nmcurso}/et/list.txt", "a", encoding="utf-8") as safelist:
                                        safelist.write(
                                            f"{tempNM} = {nmcurso}/{nmModulo}/{nmAula}/Materiais/{att['fileName']}\n")
                                    aulaPath = f"Cursos/{nmcurso}/et/{tempNM}.{att['fileName'].split('.')[-1]}"
                                    anexosLongos += 1

                                try:
                                    if not os.path.exists(f"Cursos/{nmcurso}/{nmModulo}/{nmAula}/Materiais"):
                                        os.makedirs(
                                            f"Cursos/{nmcurso}/{nmModulo}/{nmAula}/Materiais")
                                except:
                                    pass

                                if not os.path.isfile(f"{aulaPath}"):
                                    while True:
                                        try:
                                            try:
                                                attGetter = authMart
                                                anexo = attGetter.get(
                                                    f"https://api-club.hotmart.com/hot-club-api/rest/v3/attachment/{att['fileMembershipId']}/download").json()
                                                anexo = requests.get(
                                                    anexo['directDownloadUrl'])
                                            except KeyError:
                                                vrum = requests.session()
                                                vrum.headers.update(
                                                    authMart.headers)
                                                lambdaUrl = anexo['lambdaUrl']
                                                vrum.headers['token'] = anexo['token']
                                                anexo = requests.get(
                                                    vrum.get(lambdaUrl).text)
                                                del vrum
                                            with open(f"{aulaPath}", 'wb') as ann:
                                                ann.write(anexo.content)
                                                print(
                                                    f"{Colors.Magenta}Anexo baixado com sucesso!{Colors.Reset}")
                                            break
                                        except:
                                            pass
                                attCount += 1
                        except KeyError:
                            pass

                        # Count Links Complementares
                        try:
                            if infoAula['complementaryReadings']:
                                # TODO Mesmo trecho de aula longa zzz

                                filePath = os.path.dirname(
                                    os.path.abspath(__file__))
                                aulaPath = f"{filePath}/Cursos/{nmcurso}/{nmModulo}/{nmAula}/links.txt"
                                if len(aulaPath) > 254:
                                    if not os.path.exists(f"Cursos/{nmcurso}/el"):
                                        os.makedirs(f"Cursos/{nmcurso}/el")
                                    tempNM = ''.join(random.choices(
                                        string.ascii_uppercase + string.digits, k=8))
                                    with open(f"Cursos/{nmcurso}/el/list.txt", "a", encoding="utf-8") as safelist:
                                        safelist.write(
                                            f"{tempNM} = {nmcurso}/{nmModulo}/{nmAula}/links.txt\n")
                                    aulaPath = f"Cursos/{nmcurso}/el/links.txt"
                                    linksLongos += 1

                                if not os.path.isfile(f"{aulaPath}"):
                                    print(
                                        f"{Colors.Magenta}Link Complementar encontrado!{Colors.Reset}")
                                    for link in infoAula['complementaryReadings']:
                                        with open(f"{aulaPath}", "a", encoding="utf-8") as linkz:
                                            linkz.write(f"{link}\n")

                                else:
                                    print(
                                        f"{Colors.Green}Os Links já estavam presentes!{Colors.Reset}")
                            linkCount += 1
                        except KeyError:
                            pass

                    except (HTTPError, ConnectionError, Timeout, ChunkedEncodingError, ContentDecodingError):
                        authMart = Hotmart.auth(userEmail, userPass)
                        authMart.headers['accept'] = 'application/json, text/plain, */*'
                        authMart.headers['origin'] = f'https://{dominio}.club.hotmart.com/'
                        authMart.headers['referer'] = f'https://{dominio}.club.hotmart.com/'
                        authMart.headers['club'] = dominio
                        authMart.headers['pragma'] = 'no-cache'
                        authMart.headers['cache-control'] = 'no-cache'
                        tryDL -= 1
                        continue
                    break
    except KeyError:
        print(f"\t{Colors.Red}Recurso sem módulos!{Colors.Reset}")

    with open(f"Cursos/{nmcurso}/info.txt", "w", encoding="utf-8") as nfo:
        nfo.write(f"""Info sobre o rip do curso: {nmcurso} ({f'https://{dominio}.club.hotmart.com/'})
    Data do rip: {datetime.datetime.today().strftime('%d/%m/%Y')}
    Quantidade de recursos/erros (na run que completou):
        Quantidade de Módulos: {moduleCount};
        Quantidade de Aulas: {lessonCount};
        Quantidade de Vídeos: {vidCount}/{videosLongos}, inexistentes: {videosInexistentes};
            Duração (Aproximada, HLS apenas): {segVideos} segundos;
        Quantidade de Descrições(/aulas texto): {descCount}/{descLongas};
        Quantidade de Leitura Complementar: {linkCount}/{linksLongos};
        Quantidade de Anexos: {attCount}/{anexosLongos};

    Caso você esteja vendo algum erro qualquer, entenda:
        Estes erros se referem apenas à erros relacionados à caminhos muito longos, por limitação do sistema de arquivos
        Neste caso, uma pasta chamda "eX" foi criada e o arquivo foi salvo dentro dela com um nome aleatório
        No lugar de X vai uma letra para o que deu erro, sendo "v" para vídeo, "d" para descrição "l" para link
        e "t" para anexo. Dentro da pasta existe um arquivo .txt com a função de te informar onde cada arquivo deveria estar
        e com qual nome. Sinta-se livre de reornigazar e encurtar nomes para deixar organizado, ou não :)

    Vídeos Inexistentes são Lives Agendadas no Youtube, ou, vídeos que foram apagado de onde estavam hospedados.
    Verifique o arquivo "erros.txt", caso exista.
    
    A duração aproximada se refere aos segundos que o player nativo da Hotmart diz para cada aula, não contabilizando aulas do Vimeo/Youtube.

    Run que completou se refere à execução do script que terminou o download.

    A enumeração pode parecer estar faltando coisas, mas geralmente não está, a hotmart que a entrega de forma cagada.

    Script utilizado para download feito por Katinho ;)
    Versão do script: 3.8.4""")

    for f in glob.glob(f"{tempFolder}/*"):
        os.remove(f)

    time.sleep(3)

    os.rmdir(tempFolder)

    if not dAll:
        verCursos()

clearScreen()
verCursos()
