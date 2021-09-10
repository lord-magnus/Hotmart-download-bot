# coding=utf-8

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
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

import random
import string
import datetime

import requests
from bs4 import BeautifulSoup
import re
import glob
import youtube_dl
import os
import time
import m3u8
import json
import subprocess
import sys

from requests import HTTPError, Timeout
from requests.exceptions import ChunkedEncodingError, ContentDecodingError

# GLOBALS
userEmail = input("Qual o seu Email da Hotmart?\n")
userPass = input("Qual a sua senha da Hotmart?\n")
maxCursos = 0
cursoAtual = 1

if sys.platform.startswith('darwin'):
    # MacOs specific procedures
    os.system("clear")
elif sys.platform.startswith('win32'):
    # Windows specific procedures
    os.system("cls")

class Cores:
    """ANSI Escape codes for the console output with colors and rich text.

    How to use: print(f"Total errors this run: {Cores.Red if a > 0 else Cores.Green}{a}")
    Read more also: 
        * https://en.wikipedia.org/wiki/ANSI_escape_code
        * https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html
        * https://gist.github.com/arlm/f624561b2cd3f53cb26112f3e48f97cd
        * https://www.ecma-international.org/publications-and-standards/standards/ecma-48/

    Attributes:
        Reset (str): Reset colors.
        Bold (str): Makes text bold.
        Underline (str): Underlines text.
        Red (str): Red foreground text.
        Green (str): Green foreground text.
        Yellow (str): Yellow foreground text.
        Blue (str): Blue foreground text.
        Magenta (str): Magenta foreground text.
        Cyan (str): Cyan foreground text.
        bgRed (str): Red background.
        bgGreen (str): Green background.
        bgYellow (str): Yellow background.
        bgBlue (str): Blue background.
        bgMagenta (str): Magenta background.
        bgCyan (str): Cyan background.
        bgWhite (str): White background.
    """
    
    Reset = '\u001b[0m'
    """Reset colors ANSI Escape code.
    """
    Bold = '\u001b[1m'
    """Makes text bold ANSI Escape code.
    """
    Underline = '\u001b[4m'
    """Underlines text ANSI Escape code.
    """

    Red = '\u001b[31m'
    """Red foreground text ANSI Escape code.
    """
    Green = '\u001b[32m'
    """Green foreground text ANSI Escape code.
    """
    Yellow = '\u001b[33m'
    """Yellow foreground text ANSI Escape code.
    """
    Blue = '\u001b[34m'
    """Blue foreground text ANSI Escape code.
    """
    Magenta = '\u001b[35m'
    """Magenta foreground text ANSI Escape code.
    """
    Cyan = '\u001b[36m'
    """Cyan foreground text ANSI Escape code.
    """

    bgRed = '\u001b[41m'
    """Red background ANSI Escape code.
    """
    bgGreen = '\u001b[42m'
    """Green background ANSI Escape code.
    """
    bgYellow = '\u001b[43m'
    """Yellow background ANSI Escape code.
    """
    bgBlue = '\u001b[44m'
    """Blue background ANSI Escape code.
    """
    bgMagenta = '\u001b[45m'
    """Magenta background ANSI Escape code.
    """
    bgCyan = '\u001b[46m'
    """Cyan background ANSI Escape code.
    """
    bgWhite = '\u001b[47m'
    """White background ANSI Escape code.
    """

def auth():
    global userEmail
    global userPass
    authMart = requests.session()
    authMart.headers[
        'user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36'
    data = {'username': userEmail,
            'password': userPass, 'grant_type': 'password'}
    authSparkle = authMart.post(
        'https://api.sparkleapp.com.br/oauth/token', data=data)
    authSparkle = authSparkle.json()
    try:
        authMart.headers.clear()
        authMart.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36'
        authMart.headers['authorization'] = f"Bearer {authSparkle['access_token']}"
    except KeyError:
        print(f"{Cores.Red}{Cores.Bold}Tentativa de login falhou! Verifique os dados ou contate o @katomaro (Telegram){Cores.Reset}")
        exit(13)
    return authMart


def verCursos():
    authMart = auth()
    produtos = authMart.get('https://api-sec-vlc.hotmart.com/security/oauth/check_token',
                            params={'token': authMart.headers['authorization'].split(" ")[1]}).json()['resources']
    cursosValidos = []
    for i in produtos:
        try:
            if i['resource']['status'] == "ACTIVE" or "STUDENT" in i['roles']:
                dominio = i['resource']['subdomain']
                authMart.headers['origin'] = f'https://{dominio}.club.hotmart.com'
                authMart.headers['referer'] = f'https://{dominio}.club.hotmart.com'
                authMart.headers['club'] = dominio
                i["nome"] = re.sub(r'[<>:!"/\\|?*]', '', authMart.get('https://api-club.hotmart.com/hot-club-api/rest/v3/membership?attach_token=false').json()[
                                   'name']).strip().replace(".", "").replace("\t", "")
                cursosValidos.append(i)
        except KeyError:
            continue
    print("Cursos disponíveis para download:")
    for i, curso in enumerate(cursosValidos, start=1):
        print("\t", i, curso['nome'])
    opcao = int(input(
        f"Qual curso deseja baixar? {Cores.Magenta}(0 para todos!){Cores.Reset}\n")) - 1
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

    if sys.platform.startswith('darwin'):
        # MacOs specific procedures
        os.system("clear")
    elif sys.platform.startswith('win32'):
        # Windows specific procedures
        os.system("cls")

    if dAll:
        global maxCursos
        global cursoAtual
        print(
            f"{Cores.Magenta}Modo de download de todos os cursos! {cursoAtual}/{maxCursos}")
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
    print(f"Baixando o curso: {Cores.Cyan}{Cores.Bold}{nmcurso}{Cores.Reset} (pressione {Cores.Magenta}ctrl+c{Cores.Reset} a qualquer momento para {Cores.Red}cancelar{Cores.Reset})")
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
                print(f"{Cores.Magenta}Tentando baixar a aula: {Cores.Cyan}{nmModulo}{Cores.Magenta}/{Cores.Green}{nmAula}{Cores.Magenta}!{Cores.Reset}")
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
                        authMart = auth()
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
                                        f"\t{Cores.Magenta}Tentando baixar o vídeo {x}{Cores.Reset}")
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
                                                    print(f"\r\tBaixando o segmento {Cores.Blue}{segment.uri.split('.')[0].split('-')[1]}{Cores.Reset}/{Cores.Magenta}{totalSegmentos}{Cores.Reset}!",
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
                                                    f"\r\tSegmentos baixados, gerando video final! {Cores.Red}(dependendo da config do pc este passo pode demorar até 20 minutos!){Cores.Reset}", end="\n", flush=True)

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
                                                    f"Download da aula {Cores.Bold}{Cores.Magenta}{nmModulo}/{nmAula}{Cores.Reset} {Cores.Green}concluído{Cores.Reset}!")
                                                time.sleep(3)
                                                for ff in glob.glob(f"{tempFolder}/*"):
                                                    os.remove(ff)

                                            else:
                                                print(
                                                    f"{Cores.Red}{Cores.Bold}Algo deu errado ao baixar a aula, redefinindo conexão para tentar novamente!{Cores.Reset}")
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
                                            fonteExterna = f"{Cores.Cyan}Vimeo{Cores.Reset}"
                                            if "?" in i.get("src"):
                                                linkV = i.get(
                                                    "src").split("?")[0]
                                            else:
                                                linkV = i.get("src")
                                            if linkV[-1] == "/":
                                                linkV = linkV.split("/")[-1]

                                        elif 'vimeo.com' in i.get("src"):
                                            fonteExterna = f"{Cores.Cyan}Vimeo{Cores.Reset}"
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
                                            fonteExterna = f"{Cores.Red}YouTube{Cores.Reset}"
                                            linkV = i.get("src")

                                        if fonteExterna is not None:
                                            print(
                                                f"{Cores.Magenta}Baixando aula externa de fonte: {fonteExterna}!")
                                            try:
                                                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                                    ydl.download([linkV])
                                                vidCount += 1
                                            # TODO especificar os erros de Live Agendada(YouTube) e Video Inexistente
                                            except:
                                                print(
                                                    f"{Cores.Red}O vídeo é uma Live Agendada, ou, foi apagado!{Cores.Reset}")
                                                with open(f"Cursos/{nmcurso}/erros.txt", "a", encoding="utf-8") as elog:
                                                    elog.write(
                                                        f"{linkV} - {nmcurso}/{nmModulo}/{nmAula}")
                                                videosInexistentes += 1
                                    else:
                                        vidCount += 1

                                # tryDL = 0

                            except KeyError:
                                print(
                                    f"{Cores.Bold}{Cores.Red}Ué, erro ao salvar essa aula, pulada!{Cores.Reset} (verifique se ela tem vídeo desbloqueado na plataforma)")
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
                                            f"{Cores.Magenta}Descrição da aula salva!{Cores.Reset}")
                                descCount += 1

                        except KeyError:
                            pass

                        # Count Anexos
                        try:
                            for att in infoAula['attachments']:
                                print(
                                    f"{Cores.Magenta}Tentando baixar o anexo: {Cores.Red}{att['fileName']}{Cores.Reset}")
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
                                                    f"{Cores.Magenta}Anexo baixado com sucesso!{Cores.Reset}")
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
                                        f"{Cores.Magenta}Link Complementar encontrado!{Cores.Reset}")
                                    for link in infoAula['complementaryReadings']:
                                        with open(f"{aulaPath}", "a", encoding="utf-8") as linkz:
                                            linkz.write(f"{link}\n")

                                else:
                                    print(
                                        f"{Cores.Green}Os Links já estavam presentes!{Cores.Reset}")
                            linkCount += 1
                        except KeyError:
                            pass

                    except (HTTPError, ConnectionError, Timeout, ChunkedEncodingError, ContentDecodingError):
                        authMart = auth()
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
        print(f"\t{Cores.Red}Recurso sem módulos!{Cores.Reset}")

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


verCursos()